variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "region" {
  description = "Cloud region where the cluster will be deployed"
  type        = string
  default     = "us-central1"
}

variable "node_count" {
  description = "Number of nodes in the default node pool"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "Machine type for cluster nodes (e.g., e2-medium, n2-standard-4)"
  type        = string
  default     = "e2-medium"
}

variable "k8s_version" {
  description = "Kubernetes version for the cluster control plane and nodes"
  type        = string
  default     = "1.29"
}

variable "disk_size_gb" {
  description = "Size of the boot disk for each node in GB"
  type        = number
  default     = 50
}

variable "max_node_count" {
  description = "Maximum number of nodes for cluster autoscaling"
  type        = number
  default     = 10
}
