output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "adls_storage_account" {
  value = module.adls.storage_account_name
}

output "eventhub_namespace" {
  value = module.event_hubs.namespace_name
}

output "eventhub_connection_string" {
  value     = module.event_hubs.kafka_connection_string
  sensitive = true
}

output "databricks_workspace_url" {
  value = module.databricks.workspace_url
}

output "aks_cluster_name" {
  value = module.aks.cluster_name
}

output "openai_endpoint" {
  value = module.openai.endpoint
}
