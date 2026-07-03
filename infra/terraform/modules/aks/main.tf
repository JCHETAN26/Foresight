# AKS cluster — hosts FastAPI, gRPC services, the agent, and KEDA-scaled
# stream workers. KEDA + workload autoscaling wiring lands in M4.

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "node_count" { type = number }
variable "vm_size" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.name_prefix}-aks"
  resource_group_name = var.resource_group_name
  location            = var.location
  dns_prefix          = "${var.name_prefix}-aks"
  tags                = var.tags

  default_node_pool {
    name       = "default"
    node_count = var.node_count
    vm_size    = var.vm_size
  }

  identity {
    type = "SystemAssigned"
  }
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "kube_config_raw" {
  value     = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive = true
}
