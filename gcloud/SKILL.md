---
name: gcloud
description: >-
  Expert reference and operational tooling for the Google Cloud CLI (gcloud).
  Use this skill when authoring, reviewing, executing, or debugging gcloud commands,
  infrastructure deployment scripts, service account authentication, resource filtering,
  and programmatic SDK integrations across Google Cloud Platform.
---

# Google Cloud CLI (gcloud) Engineering Skill

The Google Cloud CLI (`gcloud`) provides a unified command-line interface to manage resources hosted across Google Cloud Platform. The client serializes parameters into structured REST or gRPC requests directed to regional and global API control planes (`*.googleapis.com`).

```bash
# Baseline production invocation: explicit project, server-side filtering, and table projection
gcloud compute instances list \
  --project=core-infra-prod \
  --filter="status=RUNNING AND zone:us-central1-*" \
  --format="table(name, zone.basename(), machineType.basename(), networkInterfaces[0].networkIP)" \
  --quiet
```

---

## Core Engineering Invariants

Production shell scripts, pipelines, and autonomous agents must enforce seven non-negotiable engineering invariants:

- **Mandatory Project Parameter:** Set `--project=PROJECT_ID` on every command initiating API outcalls. Never rely on ambient configuration defaults for API queries or resource mutations. Omitting the project flag causes accidental cross-environment execution.
- **Server-Side Filter Discipline:** Always filter resource records using `--filter="EXPRESSION"`. Server-side queries prune records directly within Google Cloud storage indexes. This pattern avoids client-side memory bloat and quota limits.
- **Deterministic Headless Execution:** Suppress interactive terminal prompts. Append `--quiet` (`-q`) or set the shell variable `export CLOUDSDK_CORE_DISABLE_PROMPTS=1`.
- **Keyless Identity Assumption:** Authenticate workloads via service account token exchange (`--impersonate-service-account`) or Workload Identity. Never download or commit static JSON private key files to disk.
- **Structured Machine Output Projections:** Extract operational parameters using `--format="value(...)"` or `--format="json"`. Prohibit fragile regex parsing of unstructured terminal text.
- **Toolchain Hygiene and Complete Omission:** Standardize storage transfers on `gcloud storage`. Omit deprecated utilities such as standalone `gsutil` or obsolete `gcloud docker` commands.
- **Idempotent Resource Mutation:** Verify resource status through probe queries before creating new assets. This safeguard allows scripts to rerun safely across failed pipeline stages.

---

## Unified Technical Architecture and Routing Matrix

The skill provides a two-tier knowledge architecture. Consult `references/` for synthesized architectural standards and operational invariants; consult `docs/` for exhaustive command parameter matrices.

| Operational Domain | Primary Synthesized RFC | Exhaustive Upstream Dictionary | Core Subsystems and Mechanics |
| :--- | :--- | :--- | :--- |
| **CLI Architecture & Conventions** | [CLI Conventions](references/cli_architecture_and_conventions.md) | [Topic Catalog](docs/topic/) | Command grammar, global flags, exit codes, environment variables |
| **Identity & Authentication** | [Identity Specification](references/authentication_and_identity.md) | [Auth Docs](docs/auth/), [Config Docs](docs/config/) | OAuth2 consent, service account impersonation, ADC, profiles |
| **Filtering & Formatting** | [Filtering & Projections](references/filtering_formatting_and_projections.md) | [Filters Topic](docs/topic/topic-filters.md), [Formats](docs/topic/topic-formats.md) | Expressions, boolean logic, projections, transforms, flattening |
| **Compute & Containers** | [Compute & Containers](references/compute_and_containers.md) | [Compute Docs](docs/compute/), [Container Docs](docs/container/) | Instances, disks, snapshots, GKE Autopilot, Cloud Run services |
| **Storage & Databases** | [Storage & Databases](references/storage_and_databases.md) | [Storage Docs](docs/storage/), [SQL Docs](docs/sql/) | Cloud Storage buckets, objects, rsync, Cloud SQL, Spanner DDL |
| **IAM & Resource Hierarchy** | [IAM & Hierarchy](references/iam_and_resource_hierarchy.md) | [IAM Docs](docs/iam/), [Projects Docs](docs/projects/) | Additive policy bindings, custom roles, service account setup |
| **Networking & Security** | [Networking & Security](references/networking_and_security.md) | [Compute Networks](docs/compute/), [Secrets Docs](docs/secrets/) | VPC subnets, firewall rules, Cloud NAT, Secret Manager, KMS |
| **Observability & Scripting** | [Observability & Automation](references/observability_and_automation.md) | [Logging Docs](docs/logging/) | Structured log queries, audit sinks, async operation polling |
| **Client SDK Integration** | [Client SDKs Guide](references/client_sdks.md) | [CLI Trees Topic](docs/topic/topic-cli-trees.md) | Go and Python subprocess wrappers, JSON streaming, timeouts |

---

## Production Quick Reference

| Operational Vector | Anti-Pattern | Recommended Production Pattern | Reference Guide |
| :--- | :--- | :--- | :--- |
| **Target Project Scope** | Omitting `--project` on API outcalls | Always appending `--project=PROJECT_ID` | [Conventions](references/cli_architecture_and_conventions.md) |
| **Resource Querying** | `gcloud compute instances list \| grep RUNNING` | `gcloud compute instances list --filter="status=RUNNING"` | [Filtering](references/filtering_formatting_and_projections.md) |
| **Automated Runs** | Hanging interactive prompts in headless CI | `export CLOUDSDK_CORE_DISABLE_PROMPTS=1` | [Conventions](references/cli_architecture_and_conventions.md) |
| **Credential Management** | Downloading long-lived service account JSON keys | `--impersonate-service-account=sa@proj.iam.gserviceaccount.com` | [Identity](references/authentication_and_identity.md) |
| **Object Transfers** | Calling deprecated `gsutil cp` or `gsutil rsync` | Standardizing on modern `gcloud storage cp` and `rsync` | [Storage](references/storage_and_databases.md) |
| **IAM Governance** | Overwriting policies with `gcloud projects set-iam-policy`| Appending roles via `gcloud projects add-iam-policy-binding` | [IAM](references/iam_and_resource_hierarchy.md) |
| **Subprocess Execution** | String interpolation: `subprocess.run(f"...", shell=True)` | Argument arrays: `subprocess.run(["gcloud", ...], shell=False)` | [Client SDKs](references/client_sdks.md) |

---

## Executable Tooling and Test Suites

- **Documentation Ingestion:** Execute `bash scripts/fetch_docs.sh` to mirror upstream command specifications into `docs/`.
- **Verification Runner:** Run `bash scripts/verify.sh` to execute Go client tests, Python client tests, and shell syntax audits.
- **Reference Clients:** Inspect verified Go and Python programmatic wrappers located in `examples/`.
- **Anti-Patterns Catalog:** Consult [anti_patterns_catalog.md](resources/anti_patterns_catalog.md) for concrete failure modes and remediations.
- **Engineering Cheat Sheet:** Consult [cheat_sheet.md](resources/cheat_sheet.md) for high-frequency operational syntax.
