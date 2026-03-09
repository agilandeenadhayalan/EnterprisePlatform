# --- Cluster Variables ---
variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
  default     = "mobility-dev"
}

variable "region" {
  description = "Cloud region for all resources"
  type        = string
  default     = "us-central1"
}

variable "node_count" {
  description = "Number of nodes in the cluster"
  type        = number
  default     = 2
}

variable "machine_type" {
  description = "Machine type for cluster nodes"
  type        = string
  default     = "e2-medium"
}

variable "k8s_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "disk_size_gb" {
  description = "Boot disk size per node in GB"
  type        = number
  default     = 30
}

variable "max_node_count" {
  description = "Maximum nodes for autoscaling"
  type        = number
  default     = 4
}

# --- Database Variables ---
variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "mobility_platform"
}

variable "db_user" {
  description = "Database administrator username"
  type        = string
  default     = "mobility"
}

variable "db_password" {
  description = "Database administrator password"
  type        = string
  sensitive   = true
  default     = "mobility_dev_2024"
}

variable "db_storage_gb" {
  description = "Database storage in GB"
  type        = number
  default     = 10
}

variable "db_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_16"
}

variable "db_tier" {
  description = "Database machine tier"
  type        = string
  default     = "db-f1-micro"
}

# --- Monitoring Variables ---
variable "monitoring_namespace" {
  description = "Kubernetes namespace for monitoring"
  type        = string
  default     = "monitoring"
}

variable "prometheus_retention_days" {
  description = "Prometheus data retention in days"
  type        = number
  default     = 7
}

variable "prometheus_storage_gb" {
  description = "Prometheus storage in GB"
  type        = number
  default     = 20
}

variable "prometheus_scrape_interval" {
  description = "Prometheus scrape interval"
  type        = string
  default     = "30s"
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
  default     = "admin"
}

variable "jaeger_storage_type" {
  description = "Jaeger storage backend"
  type        = string
  default     = "memory"
}

variable "jaeger_retention_days" {
  description = "Jaeger trace retention in days"
  type        = number
  default     = 3
}
