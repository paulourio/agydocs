package gate

import (
	"os"
	"testing"
)

func BenchmarkAuditScientificPapers(b *testing.B) {
	content, err := os.ReadFile("../../references/scientific_papers.md")
	if err != nil {
		b.Fatalf("Failed to read file: %v", err)
	}
	text := string(content)

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_, _ = AuditDocument(text, "paper")
	}
}

func BenchmarkAuditGlobalGuidance(b *testing.B) {
	content, err := os.ReadFile("../../references/global_guidance.md")
	if err != nil {
		b.Fatalf("Failed to read file: %v", err)
	}
	text := string(content)

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_, _ = AuditDocument(text, "essay")
	}
}

func BenchmarkExtractSentences(b *testing.B) {
	content, err := os.ReadFile("../../references/global_guidance.md")
	if err != nil {
		b.Fatalf("Failed to read file: %v", err)
	}
	_, prose, _ := SplitIntoLinesAndProse(string(content))

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = ExtractSentences(prose)
	}
}

func BenchmarkTokenizeWords(b *testing.B) {
	content, err := os.ReadFile("../../references/global_guidance.md")
	if err != nil {
		b.Fatalf("Failed to read file: %v", err)
	}
	_, prose, _ := SplitIntoLinesAndProse(string(content))

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = TokenizeWords(prose)
	}
}

func BenchmarkCacheHit(b *testing.B) {
	content, err := os.ReadFile("../../references/scientific_papers.md")
	if err != nil {
		b.Fatalf("Failed to read file: %v", err)
	}
	cache := NewCache("", true) // in-memory only
	rep, _ := AuditDocument(string(content), "paper")
	cache.Put(content, "paper", rep)

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_, _ = cache.Get(content, "paper")
	}
}

func BenchmarkWorkerPoolMultiFiles(b *testing.B) {
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

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		_ = ProcessFiles(docPaths, "essay", 8, nil)
	}
}
