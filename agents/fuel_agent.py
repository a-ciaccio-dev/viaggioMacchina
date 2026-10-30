from typing import Optional
from agents.base_agent import BaseAgent
from models.trip_models import FuelResult, FuelType, FuelUnit
from config import DEFAULT_PRICES

class FuelAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="FuelAgent",
            role="Calcola il fabbisogno di carburante, i litri necessari e la spesa complessiva di rifornimento."
        )

    def calculate_fuel(
        self,
        distance_km: float,
        fuel_consumption: float,
        fuel_unit: FuelUnit = "km_l",
        fuel_type: FuelType = "benzina",
        custom_fuel_price: Optional[float] = None
    ) -> FuelResult:
        """
        Calcola i litri (o kWh per elettrico) e il costo totale del carburante.
        """
        if fuel_consumption <= 0:
            raise ValueError("Il valore del consumo deve essere maggiore di zero.")

        # Calcolo dei litri/unità consumate
        if fuel_unit == "km_l":
            liters = distance_km / fuel_consumption
        elif fuel_unit == "l_100km":
            liters = (distance_km / 100.0) * fuel_consumption
        else:
            raise ValueError(f"Unità carburante non supportata: {fuel_unit}")

        # Determinazione del prezzo al litro
        if custom_fuel_price is not None and custom_fuel_price > 0:
            price_per_unit = custom_fuel_price
        else:
            price_per_unit = DEFAULT_PRICES.get(fuel_type.lower(), 1.85)

        total_cost = round(liters * price_per_unit, 2)
        cost_per_km = round(total_cost / distance_km, 3) if distance_km > 0 else 0.0

        return FuelResult(
            fuel_type=fuel_type,
            fuel_unit=fuel_unit,
            consumption_rate=fuel_consumption,
            effective_liters=round(liters, 2),
            fuel_price_per_unit=round(price_per_unit, 3),
            total_fuel_cost=total_cost,
            cost_per_km=cost_per_km
        )
