# Kubernetes Cluster Module
# In production, this would use google_container_cluster (GKE)
# or aws_eks_cluster (EKS). For learning, we simulate the pattern
# using null_resource to demonstrate module composition and
# variable/output wiring without requiring cloud credentials.

terraform {
  required_version = ">= 1.5.0"
}

# Simulated cluster resource
# In production, replace with:
#   resource "google_container_cluster" "primary" { ... }
#   resource "google_container_node_pool" "default" { ... }
resource "null_resource" "cluster" {
  triggers = {
    cluster_name = var.cluster_name
    region       = var.region
    node_count   = var.node_count
    machine_type = var.machine_type
    k8s_version  = var.k8s_version
  }

  provisioner "local-exec" {
    command = "echo 'Cluster ${var.cluster_name} would be provisioned in ${var.region} with ${var.node_count} x ${var.machine_type} nodes running Kubernetes ${var.k8s_version}'"
  }
}

# Simulated node pool resource
# In production, this would be a separate node pool configuration
resource "null_resource" "node_pool" {
  depends_on = [null_resource.cluster]

  triggers = {
    cluster_name   = var.cluster_name
    node_count     = var.node_count
    machine_type   = var.machine_type
    disk_size_gb   = var.disk_size_gb
    max_node_count = var.max_node_count
  }

  provisioner "local-exec" {
    command = "echo 'Node pool for ${var.cluster_name}: ${var.node_count} nodes (max ${var.max_node_count}), ${var.machine_type}, ${var.disk_size_gb}GB disk'"
  }
}

# Generate a cluster configuration file for reference
resource "local_file" "cluster_config" {
  filename = "${path.module}/cluster-config.json"
  content = jsonencode({
    cluster_name = var.cluster_name
    region       = var.region
    k8s_version  = var.k8s_version
    node_pool = {
      node_count     = var.node_count
      machine_type   = var.machine_type
      disk_size_gb   = var.disk_size_gb
      max_node_count = var.max_node_count
    }
    endpoint = "https://${var.cluster_name}.${var.region}.k8s.local"
  })
}
