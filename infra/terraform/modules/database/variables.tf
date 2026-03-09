variable "instance_name" {
  description = "Name of the PostgreSQL database instance"
  type        = string
}

variable "db_name" {
  description = "Name of the default database to create"
  type        = string
  default     = "mobility_platform"
}

variable "db_user" {
  description = "Username for the database administrator"
  type        = string
  default     = "mobility"
}

variable "db_password" {
  description = "Password for the database administrator"
  type        = string
  sensitive   = true
  default     = "mobility_dev_2024"
}

variable "storage_gb" {
  description = "Storage capacity for the database instance in GB"
  type        = number
  default     = 20
}

variable "db_version" {
  description = "PostgreSQL version to deploy"
  type        = string
  default     = "POSTGRES_16"
}

variable "tier" {
  description = "Machine tier for the database instance (e.g., db-f1-micro, db-custom-2-8192)"
  type        = string
  default     = "db-f1-micro"
}
