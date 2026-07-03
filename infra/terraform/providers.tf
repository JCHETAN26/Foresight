terraform {
  required_version = ">= 1.7"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
  }

  # Remote state: uncomment once the state storage account exists (bootstrap
  # it manually or via a separate root module, then migrate).
  # backend "azurerm" {
  #   resource_group_name  = "foresight-tfstate"
  #   storage_account_name = "foresighttfstate"
  #   container_name       = "tfstate"
  #   key                  = "foresight.tfstate"
  # }
}

provider "azurerm" {
  features {}
}

provider "azuread" {}
