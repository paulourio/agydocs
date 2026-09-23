package main

import (
	"bytes"
	"encoding/json"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func buildBinary(t *testing.T) string {
	binPath := filepath.Join(t.TempDir(), "quality_gate")
	cmd := exec.Command("go", "build", "-o", binPath, ".")
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("go build failed: %v, output: %s", err, string(out))
	}
	return binPath
}

func TestCLIExitCodeZeroOnPass(t *testing.T) {
	binPath := buildBinary(t)
	cleanText := "Raft serializes mutations to an append-only log. " +
		"The leader flushes entries to disk before responding. " +
		"This invariant prevents split-brain scenarios."

	cmd := exec.Command(binPath, "--profile", "rfc")
	cmd.Stdin = strings.NewReader(cleanText)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	if err != nil {
		t.Fatalf("Expected exit code 0, got err: %v, stderr: %s", err, stderr.String())
	}
}

func TestCLIExitCodeOneOnFail(t *testing.T) {
	binPath := buildBinary(t)
	slopText := "Let us delve into this rich tapestry of cloud microservices."

	cmd := exec.Command(binPath, "--profile", "rfc")
	cmd.Stdin = strings.NewReader(slopText)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	if err == nil {
		t.Fatalf("Expected exit code 1, but command exited with 0")
	}
	if !strings.Contains(stdout.String(), "VIOLATIONS DETECTED") {
		t.Errorf("Expected 'VIOLATIONS DETECTED' in stdout, got: %s", stdout.String())
	}
}

func TestCLIJSONOutput(t *testing.T) {
	binPath := buildBinary(t)
	cleanText := "The leader writes to disk. This write ensures persistence."

	cmd := exec.Command(binPath, "--profile", "rfc", "--json")
	cmd.Stdin = strings.NewReader(cleanText)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	if err != nil {
		t.Fatalf("Expected exit code 0, got err: %v, stderr: %s", err, stderr.String())
	}

	var data map[string]interface{}
	if err := json.Unmarshal(stdout.Bytes(), &data); err != nil {
		t.Fatalf("Failed to parse JSON output: %v\nOutput: %s", err, stdout.String())
	}

	if _, ok := data["metrics"]; !ok {
		t.Errorf("Missing 'metrics' key in JSON")
	}
	if _, ok := data["violations"]; !ok {
		t.Errorf("Missing 'violations' key in JSON")
	}
	if data["profile"] != "rfc" {
		t.Errorf("Expected profile 'rfc', got %v", data["profile"])
	}
	if data["passed"] != true {
		t.Errorf("Expected passed true, got %v", data["passed"])
	}
}
