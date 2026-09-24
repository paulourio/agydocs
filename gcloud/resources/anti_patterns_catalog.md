# Google Cloud CLI Anti-Patterns and Failure Modes Catalog

This catalog documents common operational anti-patterns, credential leaks, and script failures encountered when using the Google Cloud CLI (`gcloud`). Each entry details the mechanical failure mode, root cause, and verified remediation pattern.

```bash
# Anti-Pattern: Unfiltered listing piped into shell grep without project
gcloud compute instances list | grep RUNNING

# Production Pattern: Explicit project binding and server-side filtering
gcloud compute instances list \
  --project=core-infra-prod \
  --filter="status=RUNNING" \
  --format="value(name)"
```

---

## 1. Summary of Anti-Patterns

| Anti-Pattern ID | Operational Category | Mechanical Failure Mode | Production Remediation |
| :--- | :--- | :--- | :--- |
| **AP-001** | Pipeline Runners | Interactive prompt freezes headless CI/CD runners | Append `--quiet` or export `CLOUDSDK_CORE_DISABLE_PROMPTS=1` |
| **AP-002** | Query Performance | Client-side `grep` burns API egress quotas | Execute server-side filtering via `--filter="EXPRESSION"` |
| **AP-003** | Access Governance | Blind `set-iam-policy` wipes out inherited roles | Use additive `add-iam-policy-binding` commands |
| **AP-004** | Credential Control | Static JSON service account keys leak to disk | Adopt keyless `--impersonate-service-account` workflows |
| **AP-005** | Toolchain Hygiene | Calling deprecated legacy tools (`gsutil`) | Standardize on unified `gcloud storage` commands |
| **AP-006** | Code Safety | Shell string concatenation invites injection | Pass structured argument vectors (`exec.CommandContext`) |
| **AP-007** | Concurrency State | Unchecked async operations induce race conditions | Poll operation status loops until state matches `DONE` |
| **AP-008** | Multi-Tenant Safety | Ambient profile defaults cause cross-project mutation | Set `--project=PROJECT_ID` on every API outcall |

---

## 2. Detailed Failure Modes and Remediations

### AP-001: Interactive Prompt Freezes in Headless Runners
- **Mechanical Failure:** Commands encountering ambiguous inputs prompt the user via stdin. Prompts stall pipelines. In headless CI/CD runners where no terminal user exists, the process waits indefinitely until external job timeouts abort the step.
- **Root Cause:** Default CLI configuration expects an interactive terminal TTY.
- **Remediation:** Enforce headless execution by appending `--quiet` (`-q`) to individual commands, or export `CLOUDSDK_CORE_DISABLE_PROMPTS=1` at script start.

### AP-002: Client-Side Grep Burning API Quotas
- **Mechanical Failure:** Scripts query entire resource records and pipe raw text into shell filters like `grep` or `awk`. This practice scales poorly. On projects hosting thousands of compute instances or disks, downloading unfiltered payloads introduces multi-second network latency and exhausts API read quotas.
- **Root Cause:** Relying on client-side text parsing instead of utilizing server-side query filters.
- **Remediation:** Pass server-side expressions to `--filter`. The cloud API evaluates predicates against storage indexes, returning only matching records over the network wire.

### AP-003: Destructive IAM Overwrites via Set-Policy
- **Mechanical Failure:** An engineer prepares a minimal IAM policy JSON file and runs `gcloud projects set-iam-policy`. The command overwrites the entire project access policy, inadvertently stripping essential Google Cloud service agents and administrative access bindings. Accidental lockouts follow immediately.
- **Root Cause:** The `set-iam-policy` command replaces the complete policy document atomically rather than appending missing bindings.
- **Remediation:** Use additive policy commands (`gcloud projects add-iam-policy-binding`) to grant individual roles. When full policy documents must be managed, execute strict read-modify-write workflows with ETags.

### AP-004: Static JSON Key Leakage
- **Mechanical Failure:** Scripts create service account private keys via `gcloud iam service-accounts keys create`. The resulting private keys persist indefinitely on local developer machines, presenting severe credential theft hazards. Static keys invite breaches.
- **Root Cause:** Relying on long-lived cryptographic keys for local identity delegation.
- **Remediation:** Enforce short-lived token assumption via `--impersonate-service-account`. Workload Identity bindings replace static keys in CI/CD platforms.

### AP-005: Invoking Deprecated Storage Tooling
- **Mechanical Failure:** Scripts execute legacy Python-based `gsutil` commands. These legacy commands lack integration with unified `gcloud` configuration profiles, token caches, and modern format flags.
- **Root Cause:** Stale documentation referring to deprecated standalone utilities.
- **Remediation:** Replace all `gsutil` calls with modern `gcloud storage` commands (`gcloud storage cp`, `gcloud storage rsync`).

### AP-006: Subprocess Shell Injection
- **Mechanical Failure:** Application code constructs CLI commands via string interpolation: `subprocess.run(f"gcloud compute instances delete {vm_name}", shell=True)`. Unsanitized characters in `vm_name` execute arbitrary shell commands on the host. Shell injection breaks host perimeters.
- **Root Cause:** Invoking shell interpreters (`/bin/sh`) instead of passing raw argument arrays.
- **Remediation:** Pass discrete argument slices: `subprocess.run(["gcloud", "compute", "instances", "delete", vm_name], shell=False, check=True)`.

### AP-007: Unchecked Asynchronous Operations
- **Mechanical Failure:** Scripts launch mutating infrastructure commands with `--async` and immediately execute subsequent setup tasks. Because the background operation has not completed, dependent tasks fail with resource-not-found errors. Race conditions break builds.
- **Root Cause:** Assuming that asynchronous dispatch implies resource readiness.
- **Remediation:** Capture the returned operation identifier and poll `gcloud compute operations describe` until the status property reaches `DONE`.

### AP-008: Ambient Project Dependency on API Outcalls
- **Mechanical Failure:** Commands omit the target project parameter when querying or modifying cloud resources. In automated pipelines or multi-tenant agent loops, commands fall back to whatever active project happens to be stored in the ambient profile. Concurrent workers alter resources in the wrong tenant or fail on missing resources.
- **Root Cause:** Relying on implicit local profile settings rather than declaring explicit target scopes.
- **Remediation:** Always supply `--project=PROJECT_ID` on every command initiating remote API outcalls.

