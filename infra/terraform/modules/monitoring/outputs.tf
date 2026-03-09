output "prometheus_url" {
  description = "Internal URL for the Prometheus server"
  value       = "http://prometheus.${var.namespace}.svc.cluster.local:9090"
}

output "grafana_url" {
  description = "Internal URL for the Grafana dashboard"
  value       = "http://grafana.${var.namespace}.svc.cluster.local:3000"
}

output "jaeger_url" {
  description = "Internal URL for the Jaeger UI"
  value       = "http://jaeger.${var.namespace}.svc.cluster.local:16686"
}

output "jaeger_otlp_grpc_endpoint" {
  description = "OTLP gRPC endpoint for sending traces to Jaeger"
  value       = "jaeger.${var.namespace}.svc.cluster.local:4317"
}

output "jaeger_otlp_http_endpoint" {
  description = "OTLP HTTP endpoint for sending traces to Jaeger"
  value       = "jaeger.${var.namespace}.svc.cluster.local:4318"
}

output "namespace" {
  description = "Kubernetes namespace where the monitoring stack is deployed"
  value       = var.namespace
}
