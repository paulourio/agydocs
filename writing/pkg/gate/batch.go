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

// NonProseExtensions maps file extensions of code, data, and markup files to their human-readable format names.
var NonProseExtensions = map[string]string{
	".json":  "JSON",
	".yaml":  "YAML",
	".yml":   "YAML",
	".xml":   "XML",
	".html":  "HTML",
	".htm":   "HTML",
	".toml":  "TOML",
	".sql":   "SQL",
	".go":    "Go",
	".py":    "Python",
	".js":    "JavaScript",
	".ts":    "TypeScript",
	".rs":    "Rust",
	".c":     "C",
	".cpp":   "C++",
	".h":     "C/C++ Header",
	".java":  "Java",
	".sh":    "Shell",
	".css":   "CSS",
	".scss":  "SCSS",
	".proto": "Protobuf",
}

// AuditFile audits a single file using LevelStandard, checking and updating the cache if available.
func AuditFile(path string, profile string, cache *Cache) (*AuditReport, error) {
	return AuditFileWithLevel(path, profile, LevelStandard, cache)
}

// AuditFileWithLevel audits a single file with a specified strictness level.
func AuditFileWithLevel(path string, profile string, level Level, cache *Cache) (*AuditReport, error) {
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
		if rep, ok := cache.GetWithLevel(content, profile, level); ok {
			return rep, nil
		}
	}

	rep, err := AuditDocumentWithLevel(string(content), profile, level)
	if err != nil {
		return nil, err
	}

	// Check for non-markdown file extension
	ext := strings.ToLower(filepath.Ext(path))
	if formatName, ok := NonProseExtensions[ext]; ok {
		sev := GetRuleSeverity("Non-Markdown File Extension", 0, level)
		hasExtViolation := false
		for _, v := range rep.Violations {
			if v.Rule == "Non-Markdown File Extension" {
				hasExtViolation = true
				break
			}
		}
		if !hasExtViolation {
			v := Violation{
				Rule:           "Non-Markdown File Extension",
				Severity:       sev,
				Message:        fmt.Sprintf("File '%s' has non-Markdown extension '%s' (%s). Quality gate evaluates natural language prose in Markdown documents.", filepath.Base(path), ext, formatName),
				Recommendation: "Convert to Markdown (.md) or wrap code/data inside Markdown code fences (```).",
			}
			rep.Violations = append([]Violation{v}, rep.Violations...)
			switch sev {
			case SeverityError:
				rep.ErrorCount++
				rep.Passed = false
			case SeverityWarn:
				rep.WarningCount++
			case SeverityInfo:
				rep.InfoCount++
			}
		}
	}

	if cache != nil {
		cache.PutWithLevel(content, profile, level, rep)
	}

	return rep, nil
}

// ProcessFiles processes multiple files concurrently using a worker pool with LevelStandard.
func ProcessFiles(paths []string, profile string, workers int, cache *Cache) []FileResult {
	return ProcessFilesWithLevel(paths, profile, LevelStandard, workers, cache)
}

// ProcessFilesWithLevel processes multiple files concurrently with a specified strictness level.
func ProcessFilesWithLevel(paths []string, profile string, level Level, workers int, cache *Cache) []FileResult {
	if len(paths) == 0 {
		return nil
	}

	results := make([]FileResult, len(paths))

	// Fast path: single file, zero concurrency overhead
	if len(paths) == 1 {
		rep, err := AuditFileWithLevel(paths[0], profile, level, cache)
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
				rep, err := AuditFileWithLevel(j.path, profile, level, cache)
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
