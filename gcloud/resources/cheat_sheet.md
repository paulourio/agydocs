# Google Cloud CLI Engineering Cheat Sheet

This cheat sheet summarizes command structures, global flags, identity flows, compute provisioning, storage commands, and diagnostic queries for the Google Cloud CLI (`gcloud`). It provides quick-reference command patterns for infrastructure operations across development and production environments.

```bash
# Display active account, project, and default compute zone
gcloud config list --format="table(core.account, core.project, compute.zone)"
```

---

## 1. Identity, Profiles, and Configuration Management

The CLI coordinates authentication state through named configuration profiles and short-lived tokens. Profiles isolate environments. Engineers maintain distinct profiles to isolate local development contexts from live production deployments.

| Target Action | CLI Command Template | Core Flags and Modifiers |
| :--- | :--- | :--- |
| **Interactive Login** | `gcloud auth login` | `--no-browser` for headless hosts |
| **SDK Credentials** | `gcloud auth application-default login` | Generates local ADC JSON file |
| **Print Access Token**| `gcloud auth print-access-token` | Emits raw bearer token |
| **Create Profile** | `gcloud config configurations create <name>` | Establishes empty named profile |
| **Switch Profile** | `gcloud config configurations activate <name>` | Sets active environment profile |

```bash
# Set active parameters within a dedicated staging configuration
gcloud config set project staging-app-991
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

---

## 2. Compute Engine and Persistent Storage

Compute Engine provisions virtual machine hardware across isolated zonal boundaries. Disks survive instance termination. Disks and regional snapshots manage persistent block storage independently of instance execution state across cloud clusters.

```bash
# Create an e2-medium Compute Engine instance
gcloud compute instances create app-worker-01 \
  --project=staging-app-991 \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --quiet

# List running instances in a specific region, projecting internal and external IPs
gcloud compute instances list \
  --project=staging-app-991 \
  --filter="status=RUNNING AND zone:us-central1-*" \
  --format="table(name, zone.basename(), networkInterfaces[0].networkIP:label=INTERNAL_IP, networkInterfaces[0].accessConfigs[0].natIP:label=EXTERNAL_IP)"

# Create a 100GB persistent SSD disk
gcloud compute disks create disk-data-01 \
  --project=staging-app-991 \
  --zone=us-central1-a \
  --size=100GB \
  --type=pd-ssd \
  --quiet

# Capture a disk snapshot across regional storage
gcloud compute disks snapshot disk-data-01 \
  --project=staging-app-991 \
  --zone=us-central1-a \
  --snapshot-names=disk-data-01-snap \
  --quiet
```

---

## 3. Google Kubernetes Engine (GKE) and Cloud Run

GKE orchestrates container clusters while Cloud Run hosts autoscaling HTTP microservices. Autopilot manages worker nodes. These managed platforms run verified container images stored in Artifact Registry.

```bash
# Create a production GKE Autopilot cluster
gcloud container clusters create-auto cluster-prod \
  --project=staging-app-991 \
  --region=us-central1 \
  --quiet

# Populate local kubeconfig context with cluster credentials
gcloud container clusters get-credentials cluster-prod \
  --project=staging-app-991 \
  --region=us-central1

# Deploy a Cloud Run microservice from Artifact Registry
gcloud run deploy api-service \
  --project=staging-app-991 \
  --image=us-central1-docker.pkg.dev/staging-app-991/apps/api:v1 \
  --region=us-central1 \
  --memory=512Mi \
  --cpu=1 \
  --allow-unauthenticated \
  --quiet

# Execute an asynchronous Cloud Run batch job
gcloud run jobs execute data-cleanse \
  --project=staging-app-991 \
  --region=us-central1 \
  --async
```

---

## 4. Cloud Storage Operations (`gcloud storage`)

The unified storage group handles bucket lifecycle management and recursive object transfers. Buckets hold data. Operations enforce uniform access controls to restrict public data exposure across networks.

```bash
# Create a storage bucket with uniform bucket-level access
gcloud storage buckets create gs://data-lake-prod-991 \
  --project=staging-app-991 \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --quiet

# Upload directory recursively
gcloud storage cp -r ./dist/ gs://data-lake-prod-991/dist/ --quiet

# Synchronize local directory with bucket
gcloud storage rsync ./media/ gs://data-lake-prod-991/media/ --recursive --quiet
```

---

## 5. IAM Policy and Identity Delegation

Identity and access management controls resource privileges through explicit role bindings. Roles bind to accounts. Keyless impersonation grants short-lived access without distributing private keys across workstations.

```bash
# Create an application service account
gcloud iam service-accounts create backend-worker \
  --project=staging-app-991 \
  --display-name="Backend Worker Service Account" \
  --quiet

# Grant project viewer privileges to a principal
gcloud projects add-iam-policy-binding staging-app-991 \
  --member="serviceAccount:backend-worker@staging-app-991.iam.gserviceaccount.com" \
  --role="roles/viewer" \
  --quiet

# Run command via service account token exchange
gcloud compute instances list \
  --project=staging-app-991 \
  --impersonate-service-account=backend-worker@staging-app-991.iam.gserviceaccount.com
```

---

## 6. Observability and Diagnostics

Cloud Logging collects structured telemetry while operation commands track asynchronous tasks. Queries filter log streams. Operators isolate critical error events across cloud microservices with targeted filter expressions.

```bash
# Query recent error logs from Cloud Run
gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR' \
  --project=staging-app-991 \
  --limit=20 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'), textPayload)"

# Poll compute operation status until finished
gcloud compute operations describe operation-1711283920-5e341-a \
  --project=staging-app-991 \
  --zone=us-central1-a \
  --format="value(status)"
```
