# Google Cloud CLI Identity and Credential Specification

This document specifies identity mechanisms, credential caches, and profile configurations within the Google Cloud CLI (`gcloud`). It details OAuth2 user flows, keyless service account token exchange, Application Default Credentials (ADC), and local SQLite credential stores.

```bash
# Verify active authenticated principal and target project
gcloud auth list --filter="status=ACTIVE" --format="value(account)"
gcloud config get-value project
```

---

## 1. Identity Classes and Credential Models

The CLI interacts with four primary identity primitives across development laptops and automated build nodes:

- **OAuth2 User Consent:** Interactive users authenticate through `gcloud auth login`. The command opens a browser loopback listener on `localhost:8085` to capture authorization codes from Google Identity endpoints.
- **Service Account Token Exchange:** Workloads assume target service accounts via the global flag (`--impersonate-service-account`). The client calls the IAM Credentials API to mint short-lived OAuth2 bearer tokens valid for 3600 seconds.
- **Static Service Account Keys:** Legacy worker jobs mount static JSON key files using `gcloud auth activate-service-account` with the file path flag. Production policy restricts downloadable keys due to exfiltration risks.
- **Compute Metadata Identity:** Virtual machines and containers query the link-local metadata server at `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token` to acquire ephemeral tokens without local secrets.

```
┌──────────────────┐   Mint Bearer Token   ┌───────────────────────────┐
│ User Principal   ├──────────────────────►│ Target Service Account    │
│ (Developer Host) │◄──────────────────────┤ (1-Hour Ephemeral Token)  │
└──────────────────┘    IAM Credentials    └─────────────┬─────────────┘
                                                         │
                                                         ▼ API Authorization
                                                 Cloud Storage / Compute
```

---

## 2. Configuration Profiles and Property Trees

The CLI stores runtime settings in named configuration profiles. Each profile manages dedicated project identifiers, compute regions, default zones, and proxy definitions.

### 2.1 Profile Lifecycle Commands
Engineers isolate development, staging, and production environments using distinct named configurations:

```bash
# Create an isolated staging configuration profile
gcloud config configurations create staging-profile

# Bind core properties to the active staging profile
gcloud config set project staging-billing-data
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a

# List all stored profiles and identify the active context
gcloud config configurations list

# Switch context back to production
gcloud config configurations activate production-profile
```

### 2.2 Property Hierarchy and Lookup Order
Property resolution follows a deterministic three-tier hierarchy:
1. Command-line flags (`--project=my-proj`) override all lower settings.
2. Shell environment variables (such as `CLOUDSDK_CORE_PROJECT`) override profile records.
3. Named profile properties stored in `~/.config/gcloud/configurations/config_<name>` supply base defaults.

### 2.3 Explicit Project Scope During API Calls
Logging in a caller establishes credentials, but credentials alone do not define a safe target container. Ambient profile states frequently point to stale projects.

Every command dispatching API requests must pass `--project=PROJECT_ID` explicitly. Decoupling credential lookup from ambient project state prevents unintended mutations when scripts switch roles or run across shared nodes.

---

## 3. Short-Lived Token Exchange Workflows

Assuming service accounts dynamically eliminates static keys from developer laptops. The invoking user authenticates with individual credentials, then requests short-lived tokens from target service accounts.

### 3.1 Invocation with Inline Identity Assumption
The client exchanges credentials through the IAM Credentials API before dispatching target commands:

```bash
# Query Compute Engine instances using the infra-operator service account
gcloud compute instances list \
  --project=core-infra-prod \
  --impersonate-service-account=infra-operator@core-infra-prod.iam.gserviceaccount.com
```

### 3.2 Required IAM Bindings for Token Creation
The calling user principal requires the `roles/iam.serviceAccountTokenCreator` role on the target service account:

```bash
# Grant token creator rights on a target service account
gcloud iam service-accounts add-iam-policy-binding \
  infra-operator@core-infra-prod.iam.gserviceaccount.com \
  --member="user:alice@example.com" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project=core-infra-prod \
  --quiet
```

---

## 4. Application Default Credentials (ADC)

Application Default Credentials provide client SDKs with standard token resolution paths. CLI credentials remain distinct from SDK application credentials:

| Credential Scope | Setup Command | Local Storage Path | Target Runtime |
| :--- | :--- | :--- | :--- |
| **CLI Client Store** | `gcloud auth login` | `~/.config/gcloud/credentials.db` | Binary `gcloud` invocations |
| **SDK Application Default** | `gcloud auth application-default login` | `~/.config/gcloud/application_default_credentials.json` | Go, Python, and Java client SDKs |
| **Workload Identity** | Automatic metadata discovery | Memory-only link-local socket | GKE Pods and Cloud Run containers |

Developers testing client SDKs locally must generate ADC files explicitly:

```bash
# Provision local application default credentials for Python or Go SDKs
gcloud auth application-default login

# Print active ADC token payload to verify expiration
gcloud auth application-default print-access-token
```

---

## 5. Token Extraction and HTTP Diagnostics

Engineers extract raw bearer tokens to interact with REST APIs through low-level HTTP clients:

```bash
# Extract raw OAuth2 bearer token for curl debugging
ACCESS_TOKEN=$(gcloud auth print-access-token)

# Query compute zone inventory using HTTP authorization header
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://compute.googleapis.com/compute/v1/projects/core-infra-prod/zones"
```

This diagnostic probe verifies token validity before automated infrastructure jobs initiate.
