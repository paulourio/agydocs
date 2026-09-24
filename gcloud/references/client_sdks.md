# Google Cloud CLI Programmatic SDK Integration

This document specifies patterns for invoking the Google Cloud CLI (`gcloud`) programmatically from Go and Python. It details process execution boundaries, argument vector safety, JSON stream parsing, context cancellation, and deterministic error checks.

```go
// Canonical Go execution pattern using argument vectors and context timeout
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

cmd := exec.CommandContext(ctx, "gcloud", "compute", "instances", "list", "--project=core-infra-prod", "--format=json", "--quiet")
output, err := cmd.Output()
```

---

## 1. Process Execution and Argument Vector Safety

Programmatic wrappers must invoke the CLI binary directly through argument vectors rather than shell string concatenation. Passing argument slices prevents shell exploits and argument quoting failures:

- **Bypassing Shell Interpreters:** Invoke `exec.CommandContext` in Go or `subprocess.run(..., shell=False)` in Python. Never concatenate user input into raw shell strings.
- **Target Project Binding:** Explicitly pass `--project=PROJECT_ID` in the argument slice. Never rely on ambient profile defaults in host environments.
- **Enforcing Headless Execution:** Append `--quiet` and `--format=json` to all programmatic calls. Set the environment variable `CLOUDSDK_CORE_DISABLE_PROMPTS=1` on the subprocess environment.
- **Standard Error Splitting:** Separate standard output from standard error streams. Parse structured data from stdout only when the process exits with status code zero.

```
┌───────────────────────┐   execve(argv)   ┌──────────────────────────┐
│ Application Runtime   ├─────────────────►│ gcloud CLI Binary        │
│ (Go / Python Process) │◄─────────────────┤ Writes JSON to stdout    │
└───────────────────────┘   Exit Code 0    │ Writes Errors to stderr  │
                            JSON Payload   └──────────────────────────┘
```

---

## 2. Structured JSON Stream Parsing

All programmatic listing and inspection calls must request JSON output via `--format=json`. Client applications parse the resulting byte stream into typed data structures.

### 2.1 Go Data Structure Mapping
Define Go structs with explicit JSON tags corresponding to Google Cloud API resource schemas:

```go
type ComputeInstance struct {
	ID                string            `json:"id"`
	Name              string            `json:"name"`
	Zone              string            `json:"zone"`
	Status            string            `json:"status"`
	MachineType       string            `json:"machineType"`
	CreationTimestamp string            `json:"creationTimestamp"`
	Labels            map[string]string `json:"labels,omitempty"`
}
```

### 2.2 Python Typed Dataclass Mapping
Define Python dataclasses with type annotations to deserialize command payloads:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ComputeInstance:
    id: str
    name: str
    zone: str
    status: str
    machine_type: str
```

---

## 3. Timeout Control and Process Cancellation

Infrastructure API calls can stall during network partitions or quota throttling. Software clients must bind all calls to strict timeouts:

- **Context Deadlines in Go:** Use `context.WithTimeout` to signal kernel process termination via `SIGKILL` if the command exceeds its budget.
- **Subprocess Timeouts in Python:** Pass `timeout=float` to `subprocess.run` and catch `subprocess.TimeoutExpired` exceptions.

```python
# Safe Python subprocess execution with explicit timeout
import subprocess

try:
    res = subprocess.run(
        ["gcloud", "storage", "buckets", "list", "--project=core-infra-prod", "--format=json", "--quiet"],
        capture_output=True,
        text=True,
        timeout=15.0,
        check=True,
    )
except subprocess.TimeoutExpired:
    raise TimeoutError("gcloud storage command timed out after 15 seconds")
```

This timeout discipline guarantees that hanging CLI calls do not exhaust backend worker pools.
