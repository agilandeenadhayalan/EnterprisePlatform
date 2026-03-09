output "cluster_endpoint" {
  description = "Endpoint URL for the Kubernetes cluster API server"
  value       = "https://${var.cluster_name}.${var.region}.k8s.local"
}

output "cluster_id" {
  description = "Unique identifier for the Kubernetes cluster"
  value       = null_resource.cluster.id
}

output "cluster_name" {
  description = "Name of the provisioned Kubernetes cluster"
  value       = var.cluster_name
}

output "node_pool_id" {
  description = "Unique identifier for the default node pool"
  value       = null_resource.node_pool.id
}

output "kubeconfig_path" {
  description = "Path to the generated cluster configuration file"
  value       = local_file.cluster_config.filename
}
