# Azure Databricks workspace — Spark Structured Streaming engine.
# M0 provisions the workspace only; the streaming job + Unity Catalog wiring
# land in M1.

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_databricks_workspace" "main" {
  name                = "${var.name_prefix}-dbx"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "premium" # premium required for cluster ACLs + Unity Catalog
  tags                = var.tags
}

output "workspace_url" {
  value = "https://${azurerm_databricks_workspace.main.workspace_url}"
}

output "workspace_id" {
  value = azurerm_databricks_workspace.main.id
}
