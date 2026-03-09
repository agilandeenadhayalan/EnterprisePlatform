output "connection_string" {
  description = "PostgreSQL connection string for application configuration"
  value       = "postgresql://${var.db_user}@${var.instance_name}:5432/${var.db_name}"
  sensitive   = true
}

output "instance_id" {
  description = "Unique identifier for the database instance"
  value       = null_resource.postgres_instance.id
}

output "instance_name" {
  description = "Name of the provisioned database instance"
  value       = var.instance_name
}

output "db_name" {
  description = "Name of the default database"
  value       = var.db_name
}

output "db_user" {
  description = "Database administrator username"
  value       = var.db_user
}
