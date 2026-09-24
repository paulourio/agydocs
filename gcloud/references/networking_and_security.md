# VPC Networking and Secret Management Specification

This document specifies virtual network setups, firewall rules, and secret storage in the Google Cloud CLI (`gcloud`). It details VPC boundaries, Cloud NAT egress routing, Secret Manager versions, and Cloud KMS encryption keys.

```bash
# Create a custom VPC network with automatic subnet creation disabled
gcloud compute networks create core-vpc \
  --project=core-infra-prod \
  --subnet-mode=custom \
  --bgp-routing-mode=regional \
  --quiet
```

---

## 1. Virtual Private Cloud (VPC) Networking

Production setups provision custom-mode VPC networks with dedicated regional subnets:

```bash
# Provision a regional subnet with private Google access enabled
gcloud compute networks subnets create core-subnet-central \
  --project=core-infra-prod \
  --network=core-vpc \
  --region=us-central1 \
  --range=10.10.0.0/20 \
  --enable-private-ip-google-access \
  --quiet

# Configure Cloud Router and Cloud NAT for private egress
gcloud compute routers create core-router \
  --project=core-infra-prod \
  --network=core-vpc \
  --region=us-central1 \
  --quiet

gcloud compute routers nats create core-nat \
  --project=core-infra-prod \
  --router=core-router \
  --region=us-central1 \
  --auto-allocate-nat-external-ips \
  --nat-all-subnet-ip-ranges \
  --quiet
```

Private Google access allows worker nodes lacking external IP addresses to reach storage buckets over internal routes.

---

## 2. Firewall Rules and Zero-Trust Invariants

Firewall rules filter network traffic based on ingress or egress flow, priority, target tags, and CIDR ranges:

```bash
# Permit internal ingress traffic across cluster nodes
gcloud compute firewall-rules create allow-internal-mesh \
  --project=core-infra-prod \
  --network=core-vpc \
  --direction=INGRESS \
  --priority=1000 \
  --action=ALLOW \
  --rules=tcp:8080,tcp:8443,icmp \
  --source-ranges=10.10.0.0/20 \
  --target-tags=cluster-node \
  --quiet
```

Security rules enforce tight perimeters by binding traffic permissions to explicit network tags rather than broad subnets.

---

## 3. Secret Manager and Secret Versions

Secret Manager stores sensitive tokens, API credentials, and certificates securely:

```bash
# Create a replicated secret container
gcloud secrets create stripe-api-key \
  --project=core-infra-prod \
  --replication-policy=automatic \
  --labels=environment=prod,tier=backend \
  --quiet

# Append a new secret version from plain text input
echo -n "sk_live_sample_token_99182" | gcloud secrets versions add stripe-api-key \
  --project=core-infra-prod \
  --data-file=- \
  --quiet

# Read secret payload directly for local deployment injection
gcloud secrets versions access latest \
  --secret=stripe-api-key \
  --project=core-infra-prod
```

### 3.1 Granting Secret Access
Workload identities read secret payloads after receiving the accessor role:

```bash
# Grant secret accessor rights to a Cloud Run service account
gcloud secrets add-iam-policy-binding stripe-api-key \
  --project=core-infra-prod \
  --member="serviceAccount:run-backend@core-infra-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet
```

---

## 4. Cloud KMS Cryptographic Key Rings

Cloud KMS manages cryptographic keys used for Customer-Managed Encryption Keys (CMEK):

```bash
# Create a regional key ring for database volume encryption
gcloud kms keyrings create database-keyring \
  --project=core-infra-prod \
  --location=us-central1 \
  --quiet

# Create a symmetric encryption key with automated rotation
gcloud kms keys create db-primary-key \
  --project=core-infra-prod \
  --keyring=database-keyring \
  --location=us-central1 \
  --purpose=encryption \
  --rotation-period=90d \
  --next-rotation-time=2026-06-01T00:00:00Z \
  --quiet
```

Binding this crypto key to Compute Engine disks protects data at rest using customer keys.
