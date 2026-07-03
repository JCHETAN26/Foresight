variable "project" {
  description = "Project name, used as a prefix for all resources."
  type        = string
  default     = "foresight"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default = {
    project    = "foresight"
    managed_by = "terraform"
  }
}

# Event Hubs
variable "eventhub_capacity" {
  description = "Throughput units for the Event Hubs namespace."
  type        = number
  default     = 1
}

variable "eventhub_partition_count" {
  description = "Partitions per event hub (tenant events)."
  type        = number
  default     = 4
}

# AKS
variable "aks_node_count" {
  description = "Number of nodes in the default AKS node pool."
  type        = number
  default     = 2
}

variable "aks_vm_size" {
  description = "VM size for AKS nodes."
  type        = string
  default     = "Standard_D2s_v5"
}
