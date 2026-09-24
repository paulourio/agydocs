# Google Cloud CLI Reference SDK Clients and Examples

This directory provides working reference implementations demonstrating programmatic client wrappers, argument vector safety, and idempotent shell scripts for the Google Cloud CLI (`gcloud`). Reference code eliminates shell injection hazards and handles exit codes deterministically.

---

## 1. Directory Structure

The files within this directory demonstrate client workflows across Go, Python, and Bash:

```
examples/
├── README.md                     # Setup and verification instructions
├── go.mod                        # Go module definition
├── client.go                     # Go programmatic client wrapper
├── client_test.go                # Go client unit tests
├── client.py                     # Python programmatic client wrapper
├── test_client.py                # Python client unit tests
├── provision_service_account.sh  # Idempotent IAM provisioning workflow
├── batch_snapshot_disks.sh       # Async disk snapshotting with operation polling
└── query_infrastructure.sh       # Resource queries with transforms and projections
```

Client wrappers parse JSON streams directly into typed structs. The scripts enforce headless execution by disabling prompts.

---

## 2. Verification Commands

Engineers execute test suites across language runtimes:

```bash
# Verify Go client
go -C examples vet ./...
go -C examples test -v -count=1 ./...

# Verify Python client
python3 -m unittest examples/test_client.py

# Verify shell scripts syntax
bash -n examples/*.sh
```

Tests run quickly. Executing these commands confirms that client wrappers and scripts operate cleanly before deployment.
