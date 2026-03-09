# Staging Environment
# Composes all infrastructure modules with staging-appropriate settings.
# Medium cluster, moderate resources, mirrors production topology
# at reduced scale for integration testing and pre-release validation.

terraform {
  required_version = ">= 1.5.0"

  # In production, configure a remote backend:
  # backend "gcs" {
  #   bucket = "mobility-platform-terraform-state"
  #   prefix = "environments/staging"
  # }
}

# --- Kubernetes Cluster ---
module "cluster" {
  source = "../../modules/kubernetes-cluster"

  cluster_name   = var.cluster_name
  region         = var.region
  node_count     = var.node_count
  machine_type   = var.machine_type
  k8s_version    = var.k8s_version
  disk_size_gb   = var.disk_size_gb
  max_node_count = var.max_node_count
}

# --- Database ---
module "database" {
  source = "../../modules/database"

  instance_name = "${var.cluster_name}-postgres"
  db_name       = var.db_name
  db_user       = var.db_user
  db_password   = var.db_password
  storage_gb    = var.db_storage_gb
  db_version    = var.db_version
  tier          = var.db_tier
}

# --- Monitoring Stack ---
module "monitoring" {
  source = "../../modules/monitoring"

  namespace                  = var.monitoring_namespace
  prometheus_retention_days   = var.prometheus_retention_days
  prometheus_storage_gb       = var.prometheus_storage_gb
  prometheus_scrape_interval  = var.prometheus_scrape_interval
  grafana_admin_password      = var.grafana_admin_password
  jaeger_storage_type         = var.jaeger_storage_type
  jaeger_retention_days       = var.jaeger_retention_days
}

# --- Outputs ---
output "cluster_endpoint" {
  description = "Kubernetes cluster API endpoint"
  value       = module.cluster.cluster_endpoint
}

output "cluster_name" {
  description = "Name of the Kubernetes cluster"
  value       = module.cluster.cluster_name
}

output "database_connection_string" {
  description = "PostgreSQL connection string"
  value       = module.database.connection_string
  sensitive   = true
}

output "prometheus_url" {
  description = "Prometheus server URL"
  value       = module.monitoring.prometheus_url
}

output "grafana_url" {
  description = "Grafana dashboard URL"
  value       = module.monitoring.grafana_url
}

output "jaeger_url" {
  description = "Jaeger tracing UI URL"
  value       = module.monitoring.jaeger_url
}
