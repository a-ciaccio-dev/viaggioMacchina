from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from models.trip_models import TollResult, RouteResult
from config import AVERAGE_ITALY_TOLL_PER_KM

class TollAgent(BaseAgent):
    def __init__(self, average_toll_per_km: float = AVERAGE_ITALY_TOLL_PER_KM):
        super().__init__(
            name="TollAgent",
            role="Analizza e quantifica i costi dei pedaggi autostradali lungo il tragitto."
        )
        self.average_toll_per_km = average_toll_per_km

    def calculate_toll(
        self, 
        route: RouteResult, 
        raw_route_data: Dict[str, Any], 
        avoid_tolls: bool = False
    ) -> TollResult:
        """
        Calcola i pedaggi autostradali in base ai dati della rotta.
        """
        if avoid_tolls:
            return TollResult(
                total_toll_cost=0.0,
                toll_source="Pedaggi esclusi dall'utente",
                currency="EUR",
                notes="Percorso impostato per evitare autostrade a pedaggio."
            )

        # Se il percorso è stato calcolato con Google Maps Routes API
        if route.is_google_api:
            toll_info = (
                raw_route_data.get("travelAdvisory", {}).get("tollInfo") 
                or (raw_route_data.get("legs", [{}])[0].get("travelAdvisory", {}).get("tollInfo") if raw_route_data.get("legs") else None)
            )

            if toll_info:
                estimated_prices = toll_info.get("estimatedPrice", [])
                if estimated_prices:
                    first_price = estimated_prices[0]
                    currency = first_price.get("currencyCode", "EUR")
                    units = int(first_price.get("units", 0))
                    nanos = int(first_price.get("nanos", 0))
                    total_toll = round(units + (nanos / 1_000_000_000.0), 2)
                    return TollResult(
                        total_toll_cost=total_toll,
                        toll_source="Google Maps Routes API (Tolls)",
                        currency=currency,
                        notes="Calcolo ufficiale fornito da Google Maps Routes API."
                    )
                else:
                    return TollResult(
                        total_toll_cost=0.0,
                        toll_source="Google Maps Routes API",
                        currency="EUR",
                        notes="Nessun pedaggio rilevato su questo itinerario."
                    )

        # Se siamo in modalità OSRM o Google non ha fornito la stima puntuale
        motorway_km = route.motorway_distance_km
        if motorway_km is None:
            # Stima di massima se non determinata: circa il 70% del percorso è autostrada per viaggi interurbani lunghi (> 100km)
            motorway_km = route.distance_km * 0.7 if route.distance_km > 100 else 0.0

        estimated_toll = round(motorway_km * self.average_toll_per_km, 2)
        
        notes = (
            f"Stima calcolata su ~{motorway_km:.1f} km di tratta autostradale "
            f"con tariffa media AISCAT di {self.average_toll_per_km:.3f} €/km."
        ) if motorway_km > 0 else "Nessuna tratta a pedaggio rilevata."

        return TollResult(
            total_toll_cost=estimated_toll,
            toll_source="Tariffario chilometrico Autostrade / AISCAT",
            currency="EUR",
            notes=notes
        )
