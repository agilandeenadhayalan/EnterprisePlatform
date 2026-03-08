"""
Fleet management service repository — stubbed fleet data aggregation.

In production, this would read from vehicles.vehicles and drivers.drivers
tables via read-only database connections. For now, returns mock data.
"""

from typing import List, Dict


# Stubbed fleet data
MOCK_VEHICLES = [
    {"id": "veh-1", "make": "Tesla", "model": "Model 3", "year": 2024, "license_plate": "ABC-1234", "status": "active", "vehicle_type": "sedan"},
    {"id": "veh-2", "make": "Toyota", "model": "Camry", "year": 2023, "license_plate": "DEF-5678", "status": "active", "vehicle_type": "sedan"},
    {"id": "veh-3", "make": "Honda", "model": "CR-V", "year": 2024, "license_plate": "GHI-9012", "status": "maintenance", "vehicle_type": "suv"},
    {"id": "veh-4", "make": "Ford", "model": "Transit", "year": 2023, "license_plate": "JKL-3456", "status": "active", "vehicle_type": "van"},
]

MOCK_DRIVERS = [
    {"id": "drv-1", "full_name": "John Smith", "status": "active", "rating": 4.8, "total_trips": 1250},
    {"id": "drv-2", "full_name": "Jane Doe", "status": "active", "rating": 4.9, "total_trips": 980},
    {"id": "drv-3", "full_name": "Bob Wilson", "status": "offline", "rating": 4.6, "total_trips": 2100},
]


class FleetRepository:
    """Stubbed fleet data aggregation."""

    async def get_overview(self) -> Dict:
        """Get fleet overview statistics."""
        total_vehicles = len(MOCK_VEHICLES)
        active_vehicles = sum(1 for v in MOCK_VEHICLES if v["status"] == "active")
        total_drivers = len(MOCK_DRIVERS)
        active_drivers = sum(1 for d in MOCK_DRIVERS if d["status"] == "active")
        utilization = (active_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
        return {
            "total_vehicles": total_vehicles,
            "active_vehicles": active_vehicles,
            "total_drivers": total_drivers,
            "active_drivers": active_drivers,
            "utilization_rate": round(utilization, 1),
        }

    async def get_vehicles(self) -> List[Dict]:
        """Get all fleet vehicles."""
        return MOCK_VEHICLES

    async def get_drivers(self) -> List[Dict]:
        """Get all fleet drivers."""
        return MOCK_DRIVERS

    async def get_utilization(self) -> Dict:
        """Get fleet utilization metrics."""
        return {
            "period": "last_30_days",
            "vehicle_utilization_pct": 75.0,
            "driver_utilization_pct": 82.5,
            "avg_trips_per_vehicle": 45.2,
            "avg_trips_per_driver": 68.3,
        }
