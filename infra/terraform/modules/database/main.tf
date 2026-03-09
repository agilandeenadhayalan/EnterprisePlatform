# Database Module
# In production, this would use google_sql_database_instance (Cloud SQL)
# or aws_db_instance (RDS). For learning, we simulate the pattern
# using null_resource to demonstrate module composition.

terraform {
  required_version = ">= 1.5.0"
}

# Simulated PostgreSQL instance
# In production, replace with:
#   resource "google_sql_database_instance" "main" { ... }
#   resource "google_sql_database" "default" { ... }
#   resource "google_sql_user" "default" { ... }
resource "null_resource" "postgres_instance" {
  triggers = {
    instance_name = var.instance_name
    db_name       = var.db_name
    db_user       = var.db_user
    storage_gb    = var.storage_gb
    db_version    = var.db_version
    tier          = var.tier
  }

  provisioner "local-exec" {
    command = "echo 'PostgreSQL instance ${var.instance_name} would be provisioned: ${var.db_version}, ${var.tier}, ${var.storage_gb}GB storage'"
  }
}

# Simulated database creation
resource "null_resource" "database" {
  depends_on = [null_resource.postgres_instance]

  triggers = {
    instance_name = var.instance_name
    db_name       = var.db_name
  }

  provisioner "local-exec" {
    command = "echo 'Database ${var.db_name} created on instance ${var.instance_name}'"
  }
}

# Simulated database user
resource "null_resource" "db_user" {
  depends_on = [null_resource.postgres_instance]

  triggers = {
    instance_name = var.instance_name
    db_user       = var.db_user
  }

  provisioner "local-exec" {
    command = "echo 'User ${var.db_user} created on instance ${var.instance_name}'"
  }
}

# Generate a database configuration file for reference
resource "local_file" "db_config" {
  filename = "${path.module}/db-config.json"
  content = jsonencode({
    instance_name     = var.instance_name
    db_name           = var.db_name
    db_user           = var.db_user
    db_version        = var.db_version
    tier              = var.tier
    storage_gb        = var.storage_gb
    connection_string = "postgresql://${var.db_user}:****@${var.instance_name}:5432/${var.db_name}"
  })
}
