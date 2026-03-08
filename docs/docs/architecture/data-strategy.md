---
sidebar_position: 3
---

# Data Strategy

## Real Data Sources

| Dataset | Size | Used For |
|---------|------|----------|
| NYC Taxi & Limousine (2009-2024) | ~1.7B trips | Core ride data: pickups, dropoffs, fares |
| NYC Taxi Zone Lookup | 263 zones | Zone mapping, geospatial analysis |
| NOAA Weather (NYC) | ~50M records | Weather features for demand/ETA models |
| OpenStreetMap NYC | ~500MB | Road network, routing, POIs |

## How Data Is Used Across Roles

| Role | Data Usage | Phase |
|------|-----------|-------|
| **Data Analyst** | SQL analytics on 1B trips, zone heatmaps, fare trends | 3 |
| **Data Engineer** | Ingest 1B rows via streaming, build star schemas, ETL | 2-3 |
| **Data Scientist** | Feature engineering from trips+weather, forecasting | 4, 6 |
| **ML Engineer** | Train PyTorch models on real trip data, serve predictions | 4, 6 |
| **Backend Engineer** | 155 microservices consuming/producing real events | 1-2 |
| **Frontend Engineer** | Dashboards visualizing real ride data, maps | 1-3 |
| **Platform/Infra** | K8s deployment, observability on real workloads | 5, 7 |

## Download Commands

```bash
# Download 2023 data only (~3.5GB, ~37M trips)
python data/scripts/download_nyc_taxi.py --years 2023

# Download specific months
python data/scripts/download_nyc_taxi.py --years 2023 --months 1,2,3

# Download everything (2009-2024, ~300GB)
python data/scripts/download_nyc_taxi.py --all

# Preview what would be downloaded
python data/scripts/download_nyc_taxi.py --years 2023 --dry-run
```
