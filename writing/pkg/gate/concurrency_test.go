package gate

import (
	"fmt"
	"os"
	"strings"
	"sync"
	"testing"
)

func TestCacheThreadSafety(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "qg_cache_test_*")
	if err != nil {
		t.Fatalf("MkdirTemp failed: %v", err)
	}
	defer os.RemoveAll(tempDir)

	cache := NewCache(tempDir, true)

	var wg sync.WaitGroup
	numRoutines := 20
	iterations := 50

	for i := 0; i < numRoutines; i++ {
		wg.Add(1)
		go func(routineID int) {
			defer wg.Done()
			for j := 0; j < iterations; j++ {
				text := fmt.Sprintf("Document %d iteration %d. This invariant preserves safety.", routineID, j)
				content := []byte(text)

				// Put
				rep := &AuditReport{
					Profile: "rfc",
					Passed:  true,
					Metrics: QualityMetrics{TotalWords: 8},
				}
				cache.Put(content, "rfc", rep)

				// Get
				cached, ok := cache.Get(content, "rfc")
				if !ok || cached == nil {
					t.Errorf("Routine %d failed to retrieve cached item %d", routineID, j)
				}
			}
		}(i)
	}

	wg.Wait()
}

func TestProcessFilesWorkerPoolConcurrency(t *testing.T) {
	docPaths := []string{
		"../../references/scientific_papers.md",
		"../../references/technical_systems.md",
		"../../references/guides_tutorials.md",
		"../../references/conversational_pairing.md",
		"../../SKILL.md",
		"../../references/global_guidance.md",
		"../../resources/anti_patterns_catalog.md",
		"../../resources/metric_cheat_sheet.md",
		"../../examples/before_after_transformations.md",
	}

	// Test with 1 worker (synchronous)
	res1 := ProcessFiles(docPaths, "essay", 1, nil)
	if len(res1) != len(docPaths) {
		t.Fatalf("res1 len = %d, want %d", len(res1), len(docPaths))
	}

	// Test with 4 workers
	res4 := ProcessFiles(docPaths, "essay", 4, nil)
	if len(res4) != len(docPaths) {
		t.Fatalf("res4 len = %d, want %d", len(res4), len(docPaths))
	}

	// Verify order is preserved
	for i := range docPaths {
		if res1[i].Path != docPaths[i] {
			t.Errorf("res1[%d].Path = %s, want %s", i, res1[i].Path, docPaths[i])
		}
		if res4[i].Path != docPaths[i] {
			t.Errorf("res4[%d].Path = %s, want %s", i, res4[i].Path, docPaths[i])
		}
		if res1[i].Report.Metrics.TotalWords != res4[i].Report.Metrics.TotalWords {
			t.Errorf("Word mismatch at %d: %d vs %d", i, res1[i].Report.Metrics.TotalWords, res4[i].Report.Metrics.TotalWords)
		}
	}
}

func TestCollectFilesDirectory(t *testing.T) {
	files, err := CollectFiles([]string{"../../references"})
	if err != nil {
		t.Fatalf("CollectFiles failed: %v", err)
	}
	if len(files) < 5 {
		t.Errorf("Expected at least 5 markdown files in references, got %d", len(files))
	}
	for _, f := range files {
		if !strings.HasSuffix(f, ".md") && !strings.HasSuffix(f, ".markdown") {
			t.Errorf("Non-markdown file returned: %s", f)
		}
	}
}

func TestDiskCachePersistence(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "qg_disk_cache_*")
	if err != nil {
		t.Fatalf("MkdirTemp failed: %v", err)
	}
	defer os.RemoveAll(tempDir)

	content := []byte("The leader serializes client mutations to an append-only log. This invariant preserves safety.")
	cache1 := NewCache(tempDir, true)
	rep1, err := AuditDocument(string(content), "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	cache1.Put(content, "rfc", rep1)

	// Create a fresh cache instance pointing to same directory
	cache2 := NewCache(tempDir, true)
	rep2, ok := cache2.Get(content, "rfc")
	if !ok || rep2 == nil {
		t.Fatalf("Failed to retrieve from disk cache")
	}
	if rep2.Passed != rep1.Passed {
		t.Errorf("rep2.Passed = %v, want %v", rep2.Passed, rep1.Passed)
	}
	if rep2.Metrics.TotalWords != rep1.Metrics.TotalWords {
		t.Errorf("TotalWords = %d, want %d", rep2.Metrics.TotalWords, rep1.Metrics.TotalWords)
	}
}
