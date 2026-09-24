# IAM Policy and Resource Hierarchy Specification

This document specifies permission management, service account setup, and resource tree rules in the Google Cloud CLI (`gcloud`). It details policy binding mutations, custom role authoring, and audit access validation.

```bash
# Grant Compute Viewer rights to a developer principal on the target project
gcloud projects add-iam-policy-binding core-infra-prod \
  --member="user:engineer@example.com" \
  --role="roles/compute.viewer" \
  --condition='expression=request.time < timestamp("2026-12-31T00:00:00Z"),title=temporary_access' \
  --quiet
```

---

## 1. Resource Hierarchy and Policy Inheritance

Google Cloud enforces an acyclic resource tree where permissions inherit downward from ancestors to leaf nodes:

```
┌─────────────────────────────────┐
│ Organization (organizations/*)  │  Enforces Root Policies
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Folder (folders/*)              │  Isolates Business Units
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Project (projects/*)            │  Defines Billing & Quota Boundaries
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Resource (Compute / Storage)    │  Leaf Assets
└─────────────────────────────────┘
```

Policy inheritance obeys strict properties:
- **Additive Unions:** Permissions granted at root or folder layers cannot be revoked at the child project level.
- **Deny Policy Checks:** Deny rules override allow rules during runtime authorization checks.

---

## 2. Mutating IAM Policy Bindings

Engineers update access policies through atomic additions or complete document replacements.

### 2.1 Additive Policy Bindings
The `add-iam-policy-binding` command appends principals to specific roles without modifying unrelated role assignments:

```bash
# Grant storage object viewer roles to an application service account
gcloud projects add-iam-policy-binding core-infra-prod \
  --member="serviceAccount:app-backend@core-infra-prod.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer" \
  --quiet

# Remove an expired access role from a principal
gcloud projects remove-iam-policy-binding core-infra-prod \
  --member="user:contractor@example.com" \
  --role="roles/viewer" \
  --quiet
```

### 2.2 Atomic Policy Document Replacement
Modifying complex multi-binding rules requires fetching the active policy, modifying records, and submitting the JSON document:

```bash
# Export the active project IAM policy to a local JSON file
gcloud projects get-iam-policy core-infra-prod --format=json > policy.json

# Apply updated policy document atomically across the project
gcloud projects set-iam-policy core-infra-prod policy.json --quiet
```

---

## 3. Service Account and Key Governance

Service accounts provide distinct identities for workloads. Security rules enforce least privilege and keyless flows.

### 3.1 Managing Service Accounts
Engineers provision dedicated service accounts for individual microservices:

```bash
# Create a dedicated backend service account
gcloud iam service-accounts create api-gateway-sa \
  --display-name="API Gateway Service Account" \
  --description="Authorizes API Gateway compute workloads" \
  --project=core-infra-prod \
  --quiet

# List existing service accounts within the target project
gcloud iam service-accounts list \
  --project=core-infra-prod \
  --format="table(displayName, email, disabled)"
```

### 3.2 Authoring Custom IAM Roles
When predefined Google roles grant excessive privileges, authors define custom roles with curated permission sets:

```bash
# Create a custom role with narrow compute inspection privileges
gcloud iam roles create customInstanceMonitor \
  --project=core-infra-prod \
  --title="Custom Instance Monitor" \
  --description="Permits read-only inspection of instances and disk status" \
  --permissions="compute.instances.get,compute.instances.list,compute.disks.get" \
  --stage=GA \
  --quiet
```

This custom role confines identity privileges to mandatory operational calls.
