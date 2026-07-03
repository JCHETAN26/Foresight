# ADLS Gen2 storage account for the Iceberg lakehouse (bronze/silver/gold).
# Hierarchical namespace (is_hns_enabled) is what makes this ADLS Gen2 rather
# than plain blob storage — required for Iceberg/Spark path semantics.

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_storage_account" "lake" {
  # Storage account names: 3-24 chars, lowercase alphanumeric only.
  name                     = replace("${var.name_prefix}lake", "-", "")
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.lake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.lake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.lake.name
  container_access_type = "private"
}

output "storage_account_name" {
  value = azurerm_storage_account.lake.name
}

output "storage_account_id" {
  value = azurerm_storage_account.lake.id
}
