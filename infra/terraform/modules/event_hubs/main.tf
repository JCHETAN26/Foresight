# Azure Event Hubs — Kafka-compatible platform-scale ingestion.
# The namespace exposes a Kafka endpoint (port 9093) so the ingestion service
# uses the same aiokafka client locally and in prod, only swapping bootstrap
# servers + SASL config.

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "capacity" { type = number }
variable "partition_count" { type = number }
variable "tags" { type = map(string) }

resource "azurerm_eventhub_namespace" "main" {
  name                = "${var.name_prefix}-ehns"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard" # Standard tier required for Kafka protocol
  capacity            = var.capacity
  tags                = var.tags
}

# One hub for Stripe events. Per-tenant isolation is handled by partition key
# (tenant_id) and downstream routing, not by a hub-per-tenant, which would not
# scale to 500+ tenants within namespace entity limits.
resource "azurerm_eventhub" "stripe_events" {
  name                = "stripe-events"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = var.resource_group_name
  partition_count     = var.partition_count
  message_retention   = 1
}

resource "azurerm_eventhub_namespace_authorization_rule" "producer" {
  name                = "ingestion-producer"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = var.resource_group_name
  listen              = true
  send                = true
  manage              = false
}

output "namespace_name" {
  value = azurerm_eventhub_namespace.main.name
}

output "kafka_connection_string" {
  value     = azurerm_eventhub_namespace_authorization_rule.producer.primary_connection_string
  sensitive = true
}
