variable "namespace" {
  description = "Kubernetes namespace for the monitoring stack"
  type        = string
  default     = "monitoring"
}

variable "prometheus_retention_days" {
  description = "Number of days to retain Prometheus metrics data"
  type        = number
  default     = 15
}

variable "prometheus_storage_gb" {
  description = "Storage capacity for Prometheus data in GB"
  type        = number
  default     = 50
}

variable "prometheus_scrape_interval" {
  description = "Default scrape interval for Prometheus targets (e.g., 15s, 30s)"
  type        = string
  default     = "15s"
}

variable "grafana_admin_password" {
  description = "Password for the Grafana admin user"
  type        = string
  sensitive   = true
  default     = "admin"
}

variable "jaeger_storage_type" {
  description = "Storage backend for Jaeger traces (memory, elasticsearch, cassandra)"
  type        = string
  default     = "memory"
}

variable "jaeger_retention_days" {
  description = "Number of days to retain Jaeger trace data"
  type        = number
  default     = 7
}
