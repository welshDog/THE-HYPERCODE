terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "hypercode-${var.environment}-rg"
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = "hypercode-${var.environment}-vnet"
  address_space       = [var.address_space]
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "app" {
  name                 = "app"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.subnet_cidr]
}

resource "azurerm_public_ip" "pip" {
  name                = "hypercode-${var.environment}-pip"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
  allocation_method   = "Static"
}

resource "azurerm_lb" "lb" {
  name                = "hypercode-${var.environment}-lb"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  frontend_ip_configuration {
    name                 = "Public"
    public_ip_address_id = azurerm_public_ip.pip.id
  }
}

output "endpoint" {
  value = azurerm_public_ip.pip.ip_address
}
