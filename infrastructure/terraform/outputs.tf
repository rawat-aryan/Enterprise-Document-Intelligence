output "backend_url" {
  description = "Cloud Run backend service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Cloud Run frontend service URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "gcs_bucket_name" {
  description = "GCS document storage bucket name"
  value       = google_storage_bucket.documents.name
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.document_intelligence.dataset_id
}

output "pubsub_topic" {
  description = "Pub/Sub document processing topic name"
  value       = google_pubsub_topic.document_processing.name
}

output "artifact_registry_url" {
  description = "Artifact Registry Docker repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/enterprise-doc-intel"
}

output "gemini_secret_id" {
  description = "Secret Manager ID for Gemini API key"
  value       = google_secret_manager_secret.gemini_api_key.secret_id
}
