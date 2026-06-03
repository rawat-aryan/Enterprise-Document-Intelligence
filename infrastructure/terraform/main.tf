terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "enterprise-doc-intel-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "sqladmin.googleapis.com",
    "vpcaccess.googleapis.com",
    "aiplatform.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# GCS Bucket for document storage
resource "google_storage_bucket" "documents" {
  name          = "${var.project_id}-enterprise-documents"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  lifecycle_rule {
    condition {
      age = 1825  # 5 years
    }
    action {
      type = "Delete"
    }
  }
  cors {
    origin          = ["https://${var.frontend_domain}"]
    method          = ["GET", "PUT", "POST"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
}

# Pub/Sub Topic for document processing
resource "google_pubsub_topic" "document_processing" {
  name = "document-processing"
  labels = {
    environment = var.environment
    project     = var.project_id
  }
  message_retention_duration = "86600s"  # 24 hours
}

resource "google_pubsub_subscription" "document_processing_sub" {
  name  = "document-processing-sub"
  topic = google_pubsub_topic.document_processing.name

  ack_deadline_seconds    = 300
  retain_acked_messages   = false
  message_retention_duration = "86600s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.document_processing_dlq.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "document_processing_dlq" {
  name = "document-processing-dlq"
}

# BigQuery Dataset
resource "google_bigquery_dataset" "document_intelligence" {
  dataset_id                  = "document_intelligence"
  friendly_name               = "Enterprise Document Intelligence"
  description                 = "Data warehouse for document AI platform"
  location                    = var.bq_location
  default_table_expiration_ms = null

  labels = {
    environment = var.environment
  }

  access {
    role          = "OWNER"
    user_by_email = var.service_account_email
  }
  access {
    role          = "READER"
    special_group = "projectReaders"
  }
}

resource "google_bigquery_table" "fact_invoices" {
  dataset_id          = google_bigquery_dataset.document_intelligence.dataset_id
  table_id            = "fact_invoices"
  deletion_protection = true

  schema = file("${path.module}/../bigquery/schemas/fact_invoices.json")

  time_partitioning {
    type  = "DAY"
    field = "invoice_date"
  }

  clustering = ["vendor_name", "validation_status", "tenant_id"]
}

resource "google_bigquery_table" "fact_contracts" {
  dataset_id          = google_bigquery_dataset.document_intelligence.dataset_id
  table_id            = "fact_contracts"
  deletion_protection = true
  schema              = file("${path.module}/../bigquery/schemas/fact_contracts.json")

  time_partitioning {
    type  = "DAY"
    field = "created_at"
  }
}

resource "google_bigquery_table" "dim_vendor" {
  dataset_id = google_bigquery_dataset.document_intelligence.dataset_id
  table_id   = "dim_vendor"
  schema     = file("${path.module}/../bigquery/schemas/dim_vendor.json")
}

# Secret Manager secrets
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "enterprise-doc-intel-gemini-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "enterprise-doc-intel-secret-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "db_url" {
  secret_id = "enterprise-doc-intel-database-url"
  replication {
    auto {}
  }
}

# Artifact Registry
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "enterprise-doc-intel"
  format        = "DOCKER"
  description   = "Docker images for document intelligence platform"
}

# Cloud Run - Backend API
resource "google_cloud_run_v2_service" "backend" {
  name     = "enterprise-doc-intel-backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/enterprise-doc-intel/backend:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "GOOGLE_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.documents.name
      }
      env {
        name  = "PUBSUB_TOPIC"
        value = google_pubsub_topic.document_processing.name
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = google_bigquery_dataset.document_intelligence.dataset_id
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        failure_threshold     = 5
      }
      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
      }
    }
    service_account = var.service_account_email
  }
  depends_on = [google_project_service.apis]
}

# Cloud Run - Frontend
resource "google_cloud_run_v2_service" "frontend" {
  name     = "enterprise-doc-intel-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/enterprise-doc-intel/frontend:latest"
      env {
        name  = "API_BASE_URL"
        value = "${google_cloud_run_v2_service.backend.uri}/api/v1"
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }
  depends_on = [google_cloud_run_v2_service.backend]
}

# Allow public access to Cloud Run services
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
