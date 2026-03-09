# Monitoring Stack Module
# Provisions the observability stack: Prometheus for metrics collection,
# Grafana for visualization, and Jaeger for distributed tracing.
# In production, these could be managed services (e.g., Google Cloud
# Monitoring, AWS CloudWatch, Datadog) or self-hosted via Helm charts.

terraform {
  required_version = ">= 1.5.0"
}

# Simulated Prometheus deployment
# In production, replace with helm_release for kube-prometheus-stack
# or a managed monitoring service.
resource "null_resource" "prometheus" {
  triggers = {
    namespace           = var.namespace
    retention_days      = var.prometheus_retention_days
    storage_gb          = var.prometheus_storage_gb
    scrape_interval     = var.prometheus_scrape_interval
  }

  provisioner "local-exec" {
    command = "echo 'Prometheus deployed in namespace ${var.namespace}: retention=${var.prometheus_retention_days}d, storage=${var.prometheus_storage_gb}GB, scrape_interval=${var.prometheus_scrape_interval}'"
  }
}

# Simulated Grafana deployment
# In production, replace with helm_release for grafana
# or a managed service like Grafana Cloud.
resource "null_resource" "grafana" {
  triggers = {
    namespace          = var.namespace
    admin_password     = var.grafana_admin_password
    prometheus_url     = "http://prometheus.${var.namespace}.svc.cluster.local:9090"
  }

  provisioner "local-exec" {
    command = "echo 'Grafana deployed in namespace ${var.namespace} with Prometheus datasource configured'"
  }
}

# Simulated Jaeger deployment
# In production, replace with helm_release for jaeger-operator
# or a managed tracing service.
resource "null_resource" "jaeger" {
  triggers = {
    namespace       = var.namespace
    storage_type    = var.jaeger_storage_type
    retention_days  = var.jaeger_retention_days
  }

  provisioner "local-exec" {
    command = "echo 'Jaeger deployed in namespace ${var.namespace}: storage=${var.jaeger_storage_type}, retention=${var.jaeger_retention_days}d'"
  }
}

# Generate a monitoring stack configuration file for reference
resource "local_file" "monitoring_config" {
  filename = "${path.module}/monitoring-config.json"
  content = jsonencode({
    namespace = var.namespace
    prometheus = {
      url              = "http://prometheus.${var.namespace}.svc.cluster.local:9090"
      retention_days   = var.prometheus_retention_days
      storage_gb       = var.prometheus_storage_gb
      scrape_interval  = var.prometheus_scrape_interval
    }
    grafana = {
      url = "http://grafana.${var.namespace}.svc.cluster.local:3000"
    }
    jaeger = {
      url            = "http://jaeger.${var.namespace}.svc.cluster.local:16686"
      otlp_grpc      = "jaeger.${var.namespace}.svc.cluster.local:4317"
      otlp_http      = "jaeger.${var.namespace}.svc.cluster.local:4318"
      storage_type   = var.jaeger_storage_type
      retention_days = var.jaeger_retention_days
    }
  })
}
