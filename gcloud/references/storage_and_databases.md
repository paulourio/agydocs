# Cloud Storage, Cloud SQL, and Cloud Spanner Specification

This document details object storage lifecycle management and relational database operations in the Google Cloud CLI (`gcloud`). It specifies bucket security controls, directory synchronization, Cloud SQL instance provisioning, and automated backup routines.

```bash
# Create a secure regional storage bucket with uniform bucket-level access
gcloud storage buckets create gs://telemetry-data-prod \
  --project=core-infra-prod \
  --location=us-central1 \
  --default-storage-class=STANDARD \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --quiet
```

---

## 1. Cloud Storage Operations (`gcloud storage`)

The `gcloud storage` command group provides unified object and bucket operations across Google Cloud Storage.

### 1.1 Bucket Security and Lifecycle Controls
Buckets enforce access controls and lifecycle rules across stored object versions:

```bash
# Apply a JSON lifecycle configuration to delete objects after 90 days
gcloud storage buckets update gs://telemetry-data-prod \
  --lifecycle-file=lifecycle-policy.json \
  --quiet

# Inspect bucket metadata and active storage class
gcloud storage buckets describe gs://telemetry-data-prod \
  --format="yaml(location, storageClass, uniformBucketLevelAccess)"
```

### 1.2 Object Transfer and Directory Synchronization
The client handles single files, recursive trees, and incremental synchronization:

```bash
# Upload local application logs recursively to cloud storage
gcloud storage cp -r ./local-logs/ gs://telemetry-data-prod/logs/ --quiet

# Synchronize local directory with bucket, removing deleted destination files
gcloud storage rsync ./assets/ gs://telemetry-data-prod/assets/ \
  --recursive \
  --delete-unmatched-destination-objects \
  --quiet
```

---

## 2. Cloud SQL Database Management

Cloud SQL provisions fully managed MySQL, PostgreSQL, and SQL Server database engines.

### 2.1 Instance Provisioning and High Availability
Production database instances configure regional high availability and automated backup windows:

```bash
# Provision a PostgreSQL 15 regional instance with automatic storage increase
gcloud sql instances create db-analytics-prod \
  --project=core-infra-prod \
  --database-version=POSTGRES_15 \
  --tier=db-custom-4-16384 \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --storage-auto-increase \
  --storage-size=100GB \
  --storage-type=SSD \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --quiet
```

### 2.2 Databases, Users, and Backups
Engineers manage relational schemas, application users, and point-in-time recovery points:

```bash
# Create a dedicated application database within the target instance
gcloud sql databases create analytics_warehouse \
  --project=core-infra-prod \
  --instance=db-analytics-prod \
  --quiet

# Provision an application user with password authentication
gcloud sql users create app_service \
  --project=core-infra-prod \
  --instance=db-analytics-prod \
  --password="SecureGeneratedPassword123!" \
  --quiet

# Capture an immediate on-demand database backup
gcloud sql backups create \
  --project=core-infra-prod \
  --instance=db-analytics-prod \
  --description="pre-migration-backup" \
  --quiet
```

---

## 3. Cloud Spanner Distributed Databases

Cloud Spanner delivers globally scalable relational database instances with external consistency.

### 3.1 Instance Creation and Processing Compute
Spanner scales compute capacity via Processing Units (where 1000 processing units equal 1 node):

```bash
# Provision a regional Spanner instance with 500 processing units
gcloud spanner instances create spanner-orders-prod \
  --project=core-infra-prod \
  --config=regional-us-central1 \
  --description="Production Orders Cluster" \
  --processing-units=500 \
  --quiet
```

### 3.2 Database DDL Updates
Schema updates execute asynchronously against target Spanner database instances:

```bash
# Create an orders table inside the Spanner database
gcloud spanner databases ddl update orders_db \
  --project=core-infra-prod \
  --instance=spanner-orders-prod \
  --ddl='CREATE TABLE Orders (OrderId STRING(36) NOT NULL, CustomerId STRING(36), OrderTotal NUMERIC) PRIMARY KEY (OrderId)' \
  --quiet
```

This declarative DDL statement executes schema changes without downtime or read locks.
