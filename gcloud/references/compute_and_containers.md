# Compute Engine, GKE, and Cloud Run Specification

This document specifies lifecycle management for virtual machines, Kubernetes clusters, and serverless containers in the Google Cloud CLI (`gcloud`). It details provisioning commands, operational flags, asynchronous operation polling, and zonal scheduling boundaries.

```bash
# Provision an e2-standard-4 Compute Engine instance with persistent SSD storage
gcloud compute instances create worker-prod-01 \
  --project=core-infra-prod \
  --zone=us-central1-a \
  --machine-type=e2-standard-4 \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-ssd \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --tags=worker,internal-only \
  --quiet
```

---

## 1. Compute Engine Infrastructure Lifecycle

Compute Engine provisions physical compute slices and virtualized hardware across isolated zones.

### 1.1 Virtual Machine Instance Operations
Creating, querying, and terminating virtual machines requires explicit project and zone identification:

```bash
# List running instances with custom column projection
gcloud compute instances list \
  --project=core-infra-prod \
  --filter="status=RUNNING" \
  --format="table(name, zone.basename(), machineType.basename(), networkInterfaces[0].networkIP)"

# Stop a running instance cleanly
gcloud compute instances stop worker-prod-01 \
  --project=core-infra-prod \
  --zone=us-central1-a \
  --quiet

# Attach a persistent disk to an existing instance
gcloud compute instances attach-disk worker-prod-01 \
  --project=core-infra-prod \
  --disk=data-disk-prod \
  --zone=us-central1-a \
  --mode=rw \
  --quiet
```

### 1.2 Persistent Disks and Snapshot Management
Disks retain state independently of instance execution lifecycles:

```bash
# Create an independent 200GB balanced persistent disk
gcloud compute disks create data-disk-prod \
  --project=core-infra-prod \
  --size=200GB \
  --type=pd-balanced \
  --zone=us-central1-a \
  --quiet

# Capture an incremental snapshot across regional storage
gcloud compute disks snapshot data-disk-prod \
  --project=core-infra-prod \
  --snapshot-names=data-disk-prod-snap-20260324 \
  --zone=us-central1-a \
  --storage-location=us-central1 \
  --quiet
```

---

## 2. Google Kubernetes Engine (GKE) Management

GKE manages containerized workloads across managed worker node pools.

### 2.1 Cluster Creation and Credential Ingestion
Production deployments choose between GKE Autopilot and GKE Standard cluster modes:

```bash
# Create a production GKE Autopilot cluster across multiple compute zones
gcloud container clusters create-auto cluster-prod-01 \
  --project=core-infra-prod \
  --region=us-central1 \
  --network=core-vpc \
  --subnetwork=gke-subnet \
  --release-channel=regular \
  --quiet

# Populate local kubeconfig with cluster credentials
gcloud container clusters get-credentials cluster-prod-01 \
  --region=us-central1 \
  --project=core-infra-prod
```

### 2.2 Node Pool Management
Standard clusters isolate heterogeneous hardware workloads into distinct node pools:

```bash
# Add a dedicated GPU node pool with cluster autoscaling enabled
gcloud container node-pools create gpu-workers \
  --project=core-infra-prod \
  --cluster=cluster-prod-01 \
  --region=us-central1 \
  --machine-type=g2-standard-8 \
  --accelerator=type=nvidia-l4,count=1 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=5 \
  --quiet
```

---

## 3. Serverless Workloads: Cloud Run and Functions

Cloud Run executes containerized HTTP services and background batch jobs without infrastructure management.

### 3.1 Deploying Cloud Run Services
Services deploy container images stored in Artifact Registry with defined CPU and concurrency limits:

```bash
# Deploy a public web microservice with concurrency limits
gcloud run deploy payments-api \
  --project=core-infra-prod \
  --image=us-central1-docker.pkg.dev/core-infra-prod/apps/payments:v1.4 \
  --region=us-central1 \
  --platform=managed \
  --memory=1Gi \
  --cpu=2 \
  --concurrency=80 \
  --min-instances=1 \
  --max-instances=20 \
  --allow-unauthenticated \
  --quiet
```

### 3.2 Executing Cloud Run Jobs
Jobs process bounded batch tasks to completion without HTTP listeners:

```bash
# Create and execute a batch migration job
gcloud run jobs create db-migrate \
  --project=core-infra-prod \
  --image=us-central1-docker.pkg.dev/core-infra-prod/apps/migrator:v1.0 \
  --region=us-central1 \
  --tasks=1 \
  --max-retries=3 \
  --quiet

# Trigger asynchronous job execution
gcloud run jobs execute db-migrate \
  --project=core-infra-prod \
  --region=us-central1 \
  --async
```

---

## 4. Asynchronous Operation Polling

Mutating infrastructure commands return unique operation URIs when executed with the `--async` flag. Automated scripts monitor operation progress by querying operation status:

```bash
# Query the status of an active compute operation
gcloud compute operations describe operation-1711283920-5e341-a \
  --project=core-infra-prod \
  --zone=us-central1-a \
  --format="value(status)"
```

Scripts evaluate the emitted status string until the value matches `DONE`, preventing pipeline race conditions before subsequent steps run.
