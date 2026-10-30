"""
FuelStrategyAgent: Agente specializzato nell'analisi realistica dei prezzi del carburante
transfrontalieri (Italia, Austria, Germania, Francia) e nell'ottimizzazione dei rifornimenti.
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from models.trip_models import FuelType, FuelUnit

class FuelStrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="FuelStrategyAgent",
            role="Analizza i prezzi reali dei carburanti nei diversi Paesi e calcola il piano di rifornimento ottimale."
        )

        # Prezzi realistici rilevati e aggiornati al mercato attuale (minimo ~2,02 €/l in Italia)
        self.market_prices: Dict[str, Dict[str, float]] = {
            "italia": {
                "autostrada": 2.32,  # Rete autostradale italiana oltre 2,25 - 2,35 €/l
                "ordinaria": 2.02,   # Il prezzo minimo self-service su rete ordinaria
                "diesel_autostrada": 2.18,
                "diesel_ordinaria": 1.92
            },
            "austria": {
                "autostrada": 2.24,
                "ordinaria": 1.85,   # Fuori autostrada in Austria si risparmia rispetto all'Italia
                "diesel_autostrada": 2.12,
                "diesel_ordinaria": 1.78
            },
            "germania": {
                "autostrada": 2.38,  # Raststätte tedesche hanno prezzi record
                "ordinaria": 2.12,   # Autohof a 1-2 km dall'autostrada
                "diesel_autostrada": 2.22,
                "diesel_ordinaria": 1.88
            },
            "francia": {
                "autostrada": 2.34,  # Aree di servizio autostradali Sanef/APRR
                "ordinaria": 2.08,   # Ipermercati Leclerc/Carrefour
                "diesel_autostrada": 2.18,
                "diesel_ordinaria": 1.85
            }
        }

    def analyze_trip_fuel(
        self,
        total_distance_km: float,
        fuel_consumption: float,
        fuel_unit: FuelUnit = "km_l",
        fuel_type: FuelType = "benzina"
    ) -> Dict[str, Any]:
        """
        Calcola la stima realistica del carburante confrontando lo scenario 'Solo Autostrada'
        con lo scenario 'Smart Refueling' ottimizzato.
        """
        # Litri per tratta singola
        if fuel_unit == "km_l":
            single_liters = total_distance_km / fuel_consumption
        else:
            single_liters = (total_distance_km / 100.0) * fuel_consumption

        round_trip_liters = single_liters * 2

        # 1. Scenario Solo Autostrada (Pessimistico / Casual)
        # Ponderazione km percorsi: Italia ~70km, Austria ~230km, Germania ~590km, Francia ~400km
        weights = {"italia": 0.05, "austria": 0.18, "germania": 0.46, "francia": 0.31}
        key_fuel = "autostrada" if fuel_type == "benzina" else "diesel_autostrada"

        highway_avg_price = sum(self.market_prices[c][key_fuel] * w for c, w in weights.items())
        highway_cost_single = round(single_liters * highway_avg_price, 2)
        highway_cost_round = round(round_trip_liters * highway_avg_price, 2)

        # 2. Scenario Smart Refueling (Strategico Ottimizzato)
        # Strategia:
        # Pieno 1 (Partenza Tolmezzo, ~50L): prezzo minimo ordinaria Italia (~2.02 €/l)
        # Pieno 2 (Salisburgo/Villach Austria, ~50L): prezzo ordinaria Austria (~1.85 €/l)
        # Pieno 3 (Autohof Germania / Ipermercato Francia, ~65L): prezzo medio ordinaria D/F (~2.10 €/l)
        smart_weighted_price = (2.02 * 0.25) + (1.85 * 0.40) + (2.10 * 0.35)
        smart_cost_single = round(single_liters * smart_weighted_price, 2)
        smart_cost_round = round(round_trip_liters * smart_weighted_price, 2)

        savings_round = round(highway_cost_round - smart_cost_round, 2)

        # Piano tappe rifornimento consigliato
        refueling_stops = [
            {
                "tappa": "Partenza: Tolmezzo (UD)",
                "azione": "Pieno completo su rete ordinaria self-service (minimo di mercato ~2,00 - 2,02 €/l)",
                "prezzo_stimato": "2,02 €/l",
                "litri_stimati": "45 - 50 L",
                "autonomia": "Copre fino a Salisburgo / confine tedesco (~300 km)"
            },
            {
                "tappa": "Sosta 1: Salisburgo o Villach (Austria)",
                "azione": "Uscita a 1-2 km dall'A10 (evitare le stazioni autostradali)",
                "prezzo_stimato": "1,85 €/l (prezzo più basso rispetto a Italia, Germania e Francia)",
                "litri_stimati": "40 - 45 L",
                "autonomia": "Copre tutta la Germania fino al confine francese (~500 km)"
            },
            {
                "tappa": "Sosta 2: Autohof Germania (A6) o Reims (Francia)",
                "azione": "Rifornimento rapido in Autohof tedesco o ipermercato francese (Leclerc/Carrefour)",
                "prezzo_stimato": "2,08 - 2,12 €/l",
                "litri_stimati": "35 - 40 L",
                "autonomia": "Arrivo a Montreuil e primi giorni di permanenza"
            }
        ]

        return {
            "single_distance_km": round(total_distance_km, 1),
            "round_trip_distance_km": round(total_distance_km * 2, 1),
            "single_liters": round(single_liters, 1),
            "round_trip_liters": round(round_trip_liters, 1),
            "highway_avg_price": round(highway_avg_price, 3),
            "highway_cost_single": highway_cost_single,
            "highway_cost_round": highway_cost_round,
            "smart_avg_price": round(smart_weighted_price, 3),
            "smart_cost_single": smart_cost_single,
            "smart_cost_round": smart_cost_round,
            "savings_round_trip": savings_round,
            "refueling_stops": refueling_stops,
            "fuel_prices_by_country": self.market_prices
        }
