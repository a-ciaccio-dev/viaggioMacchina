from typing import Optional, Tuple
from agents.base_agent import BaseAgent
from agents.route_agent import RouteAgent
from agents.toll_agent import TollAgent
from agents.fuel_agent import FuelAgent
from agents.hotel_agent import HotelAgent
from agents.parking_agent import ParkingAgent
from models.trip_models import TripInput, TripReport, RouteResult, TollResult, FuelResult, ParkingResult, HotelSearchResult
from config import GOOGLE_MAPS_API_KEY

class CoordinatorAgent(BaseAgent):
    def __init__(self, google_maps_api_key: Optional[str] = GOOGLE_MAPS_API_KEY):
        super().__init__(
            name="CoordinatorAgent",
            role="Supervisiona e orchestra il team di agenti, sintetizzando percorso, pedaggi, consumi, hotel e parcheggi."
        )
        self.route_agent = RouteAgent(google_maps_api_key=google_maps_api_key)
        self.toll_agent = TollAgent()
        self.fuel_agent = FuelAgent()
        self.hotel_agent = HotelAgent()
        self.parking_agent = ParkingAgent()

    def process_trip(self, trip_input: TripInput, compare_no_tolls: bool = False) -> Tuple[TripReport, Optional[TripReport]]:
        """
        Elabora il viaggio completo: percorso, pedaggi, carburante e analisi parcheggio.
        """
        # 1. Calcolo itinerario primario
        route_result, raw_route = self.route_agent.calculate_route(
            origin=trip_input.origin,
            destination=trip_input.destination,
            avoid_tolls=trip_input.avoid_tolls
        )

        # 2. Calcolo pedaggi
        toll_result = self.toll_agent.calculate_toll(
            route=route_result,
            raw_route_data=raw_route,
            avoid_tolls=trip_input.avoid_tolls
        )

        # 3. Calcolo carburante
        fuel_result = self.fuel_agent.calculate_fuel(
            distance_km=route_result.distance_km,
            fuel_consumption=trip_input.fuel_consumption,
            fuel_unit=trip_input.fuel_unit,
            fuel_type=trip_input.fuel_type,
            custom_fuel_price=trip_input.custom_fuel_price
        )

        # 4. Analisi parcheggio a destinazione
        parking_result = self.parking_agent.analyze_parking(
            destination=trip_input.destination,
            stay_days=trip_input.stay_days
        )

        # 5. Ricerca tappa intermedia notturna per viaggi lunghi (> 600 km)
        hotel_result = None
        if route_result.distance_km > 600:
            hotel_result = self.hotel_agent.search_stopover_hotels(
                stopover_area="Karlsruhe",
                km_from_origin=729.5,
                total_distance=route_result.distance_km,
                guests=3
            )

        # 6. Sintesi dei totali (viaggio andata: carburante + pedaggi)
        total_cost = round(fuel_result.total_fuel_cost + toll_result.total_toll_cost, 2)
        cost_per_person = round(total_cost / trip_input.passengers, 2)

        main_report = TripReport(
            origin=trip_input.origin,
            destination=trip_input.destination,
            stay_days=trip_input.stay_days,
            route=route_result,
            toll=toll_result,
            fuel=fuel_result,
            parking=parking_result,
            hotel_stopover=hotel_result,
            passengers=trip_input.passengers,
            total_trip_cost=total_cost,
            cost_per_passenger=cost_per_person
        )

        # 6. Variante opzionale di confronto
        alt_report = None
        if compare_no_tolls and not trip_input.avoid_tolls and toll_result.total_toll_cost > 0:
            try:
                alt_route, alt_raw = self.route_agent.calculate_route(
                    origin=trip_input.origin,
                    destination=trip_input.destination,
                    avoid_tolls=True
                )
                alt_toll = self.toll_agent.calculate_toll(alt_route, alt_raw, avoid_tolls=True)
                alt_fuel = self.fuel_agent.calculate_fuel(
                    distance_km=alt_route.distance_km,
                    fuel_consumption=trip_input.fuel_consumption,
                    fuel_unit=trip_input.fuel_unit,
                    fuel_type=trip_input.fuel_type,
                    custom_fuel_price=trip_input.custom_fuel_price
                )
                alt_total = round(alt_fuel.total_fuel_cost + alt_toll.total_toll_cost, 2)
                alt_report = TripReport(
                    origin=trip_input.origin,
                    destination=trip_input.destination,
                    stay_days=trip_input.stay_days,
                    route=alt_route,
                    toll=alt_toll,
                    fuel=alt_fuel,
                    parking=parking_result,
                    passengers=trip_input.passengers,
                    total_trip_cost=alt_total,
                    cost_per_passenger=round(alt_total / trip_input.passengers, 2)
                )
            except Exception:
                alt_report = None

        return main_report, alt_report
