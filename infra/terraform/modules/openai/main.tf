# Azure OpenAI — GPT-4o deployment for the LangGraph agent's [reason] node.
# NOTE: Azure OpenAI access requires an approved subscription. If the apply
# fails on quota, request access before M3 rather than blocking M0.

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_cognitive_account" "openai" {
  name                = "${var.name_prefix}-openai"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "OpenAI"
  sku_name            = "S0"
  tags                = var.tags
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }

  scale {
    type     = "Standard"
    capacity = 10
  }
}

output "endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "primary_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}
