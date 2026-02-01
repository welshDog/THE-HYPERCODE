terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

resource "google_compute_network" "vpc" {
  name                    = "hypercode-${var.environment}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "hypercode-${var.environment}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_compute_firewall" "app" {
  name    = "hypercode-${var.environment}-fw"
  network = google_compute_network.vpc.name
  allow {
    protocol = "tcp"
    ports    = ["80"]
  }
  source_ranges = ["0.0.0.0/0"]
}

output "network" { value = google_compute_network.vpc.name }
output "subnet" { value = google_compute_subnetwork.subnet.name }
