# Foresight — root module.
# Wires the per-service modules into a single Azure resource group. Each module
# is self-contained so it can be applied/destroyed independently during dev.

locals {
  name_prefix = "${var.project}-${var.environment}"
}

resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = var.tags
}

module "adls" {
  source              = "./modules/adls"
  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = var.tags
}

module "event_hubs" {
  source              = "./modules/event_hubs"
  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  capacity            = var.eventhub_capacity
  partition_count     = var.eventhub_partition_count
  tags                = var.tags
}

module "databricks" {
  source              = "./modules/databricks"
  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = var.tags
}

module "aks" {
  source              = "./modules/aks"
  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  node_count          = var.aks_node_count
  vm_size             = var.aks_vm_size
  tags                = var.tags
}

module "openai" {
  source              = "./modules/openai"
  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = var.tags
}
