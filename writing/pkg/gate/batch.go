package gate

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// FileResult holds the audit result for a single file in batch processing.
type FileResult struct {
	Path   string       `json:"path"`
	Report *AuditReport `json:"report,omitempty"`
	Error  string       `json:"error,omitempty"`
}

// CollectFiles resolves input file and directory arguments into a list of file paths.
// If an argument is a directory, it walks it recursively for Markdown files.
func CollectFiles(inputs []string) ([]string, error) {
	var files []string
	for _, in := range inputs {
		if in == "-" {
			files = append(files, "-")
			continue
		}
		fi, err := os.Stat(in)
		if err != nil {
			return nil, fmt.Errorf("file not found: %s", in)
		}
		if fi.IsDir() {
			err = filepath.WalkDir(in, func(path string, d fs.DirEntry, walkErr error) error {
				if walkErr != nil {
					return walkErr
				}
				name := d.Name()
				if d.IsDir() {
					if strings.HasPrefix(name, ".") || name == "node_modules" || name == "vendor" {
						return filepath.SkipDir
					}
					return nil
				}
				ext := strings.ToLower(filepath.Ext(name))
				if ext == ".md" || ext == ".markdown" {
					files = append(files, path)
				}
				return nil
			})
			if err != nil {
				return nil, err
			}
		} else {
			files = append(files, in)
		}
	}
	return files, nil
}

// AuditFile audits a single file, checking and updating the cache if available.
func AuditFile(path string, profile string, cache *Cache) (*AuditReport, error) {
	var content []byte
	var err error
	if path == "-" {
		return nil, fmt.Errorf("stdin cannot be audited with AuditFile; read content directly")
	}
	content, err = os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	if cache != nil {
		if rep, ok := cache.Get(content, profile); ok {
			return rep, nil
		}
	}

	rep, err := AuditDocument(string(content), profile)
	if err != nil {
		return nil, err
	}

	if cache != nil {
		cache.Put(content, profile, rep)
	}

	return rep, nil
}

// ProcessFiles processes multiple files concurrently using a worker pool.
// When len(paths) == 1, execution is completely synchronous with zero goroutine overhead.
func ProcessFiles(paths []string, profile string, workers int, cache *Cache) []FileResult {
	if len(paths) == 0 {
		return nil
	}

	results := make([]FileResult, len(paths))

	// Fast path: single file, zero concurrency overhead
	if len(paths) == 1 {
		rep, err := AuditFile(paths[0], profile, cache)
		results[0] = FileResult{Path: paths[0], Report: rep}
		if err != nil {
			results[0].Error = err.Error()
		}
		return results
	}

	if workers <= 0 {
		workers = 1
	}
	if workers > len(paths) {
		workers = len(paths)
	}

	type job struct {
		idx  int
		path string
	}

	jobs := make(chan job, len(paths))
	var wg sync.WaitGroup

	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := range jobs {
				rep, err := AuditFile(j.path, profile, cache)
				res := FileResult{Path: j.path, Report: rep}
				if err != nil {
					res.Error = err.Error()
				}
				results[j.idx] = res
			}
		}()
	}

	for idx, path := range paths {
		jobs <- job{idx: idx, path: path}
	}
	close(jobs)

	wg.Wait()
	return results
}
