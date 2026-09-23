package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"

	"writing/pkg/gate"
)

func main() {
	var profileName string
	var jsonOutput bool
	var verbose bool
	var useCache bool
	var fixHints bool
	var workers int

	flag.StringVar(&profileName, "profile", "essay", "Target writing profile band (rfc, paper, essay, tutorial, chat, briefing)")
	flag.StringVar(&profileName, "p", "essay", "Target writing profile band (shorthand)")
	flag.BoolVar(&jsonOutput, "json", false, "Emit structured JSON for automated agent loops and CI pipelines")
	flag.BoolVar(&verbose, "verbose", false, "Display extended diagnostic details")
	flag.BoolVar(&verbose, "v", false, "Display extended diagnostic details (shorthand)")
	flag.BoolVar(&useCache, "cache", true, "Enable SHA-256 result caching in .quality_gate_cache/")
	flag.BoolVar(&fixHints, "fix-hints", true, "Show actionable fix recommendations for each violation")
	flag.IntVar(&workers, "workers", runtime.NumCPU(), "Number of parallel workers for multi-file processing")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: %s [--profile {rfc,paper,essay,tutorial,chat,briefing}] [--json] [--cache] [--workers N] [FILE/DIR...]\n", os.Args[0])
		flag.PrintDefaults()
	}

	// Rearrange arguments so flags can appear before or after positional file paths
	valFlags := map[string]bool{
		"-profile": true, "--profile": true,
		"-p": true, "--p": true,
		"-workers": true, "--workers": true,
	}
	var flagArgs, posArgs []string
	rawArgs := os.Args[1:]
	for i := 0; i < len(rawArgs); i++ {
		arg := rawArgs[i]
		if valFlags[arg] && i+1 < len(rawArgs) {
			flagArgs = append(flagArgs, arg, rawArgs[i+1])
			i++
		} else if strings.HasPrefix(arg, "-") && arg != "-" {
			flagArgs = append(flagArgs, arg)
		} else {
			posArgs = append(posArgs, arg)
		}
	}
	os.Args = append([]string{os.Args[0]}, append(flagArgs, posArgs...)...)

	flag.Parse()

	if _, ok := gate.Profiles[profileName]; !ok {
		keys := make([]string, 0, len(gate.Profiles))
		for k := range gate.Profiles {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		fmt.Fprintf(os.Stderr, "Error: Unknown profile '%s'. Available: %v\n", profileName, keys)
		os.Exit(2)
	}

	var cache *gate.Cache
	if useCache {
		cacheDir := filepath.Join(".", ".quality_gate_cache")
		cache = gate.NewCache(cacheDir, true)
	}

	args := flag.Args()

	// Stdin mode
	if len(args) == 0 || (len(args) == 1 && args[0] == "-") {
		content, err := io.ReadAll(os.Stdin)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error reading stdin: %v\n", err)
			os.Exit(2)
		}

		var report *gate.AuditReport
		if cache != nil {
			if cached, ok := cache.Get(content, profileName); ok {
				report = cached
			}
		}

		if report == nil {
			rep, err := gate.AuditDocument(string(content), profileName)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error: %v\n", err)
				os.Exit(2)
			}
			report = rep
			if cache != nil {
				cache.Put(content, profileName, report)
			}
		}

		if jsonOutput {
			data, _ := json.MarshalIndent(report, "", "  ")
			fmt.Println(string(data))
		} else {
			fmt.Println(gate.FormatTerminalReport(report, fixHints, verbose))
		}

		if report.Passed {
			os.Exit(0)
		}
		os.Exit(1)
	}

	// File / Directory collection
	files, err := gate.CollectFiles(args)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(2)
	}

	if len(files) == 0 {
		fmt.Fprintf(os.Stderr, "Error: No matching Markdown files found\n")
		os.Exit(2)
	}

	// Single file execution
	if len(files) == 1 {
		report, err := gate.AuditFile(files[0], profileName, cache)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(2)
		}

		if jsonOutput {
			data, _ := json.MarshalIndent(report, "", "  ")
			fmt.Println(string(data))
		} else {
			fmt.Println(gate.FormatTerminalReport(report, fixHints, verbose))
		}

		if report.Passed {
			os.Exit(0)
		}
		os.Exit(1)
	}

	// Batch multi-file execution
	results := gate.ProcessFiles(files, profileName, workers, cache)
	allPassed := true

	if jsonOutput {
		data, _ := json.MarshalIndent(results, "", "  ")
		fmt.Println(string(data))
		for _, r := range results {
			if r.Error != "" || (r.Report != nil && !r.Report.Passed) {
				allPassed = false
			}
		}
	} else {
		passedCount := 0
		for _, r := range results {
			fmt.Println("=" + strings.Repeat("-", 74) + "=")
			fmt.Printf("File: %s\n", r.Path)
			if r.Error != "" {
				fmt.Printf("Error: %s\n", r.Error)
				allPassed = false
				continue
			}
			fmt.Println(gate.FormatTerminalReport(r.Report, fixHints, verbose))
			if r.Report.Passed {
				passedCount++
			} else {
				allPassed = false
			}
		}
		fmt.Printf("\nBatch Summary: %d/%d files passed quality gate.\n", passedCount, len(results))
	}

	if allPassed {
		os.Exit(0)
	}
	os.Exit(1)
}
