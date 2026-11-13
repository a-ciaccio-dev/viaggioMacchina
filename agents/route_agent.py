import time
import requests
from typing import Dict, Any, Tuple, Optional, List
from agents.base_agent import BaseAgent
from models.trip_models import RouteResult

class RouteAgent(BaseAgent):
    def __init__(self, google_maps_api_key: Optional[str] = None):
        super().__init__(
            name="RouteAgent",
            role="Calcola il miglior itinerario stradale, analizza distanze, tempi e tratte autostradali."
        )
        self.google_api_key = google_maps_api_key

    def calculate_route(
        self,
        origin: str,
        destination: str,
        avoid_tolls: bool = False,
        waypoints: Optional[List[str]] = None,
    ) -> Tuple[RouteResult, Dict[str, Any]]:
        """
        Calcola l'itinerario.
        Restituisce un RouteResult e il payload grezzo per l'estrazione di informazioni specifiche sui pedaggi.
        """
        if self.google_api_key:
            try:
                return self._compute_with_google(origin, destination, avoid_tolls, waypoints=waypoints)
            except Exception as e:
                # In caso di errore o problemi con la chiave API, fallback automatico a OSRM
                print(f"[RouteAgent] Avviso: Google Routes API non disponibile ({e}). Passo al motore OpenStreetMap/OSRM...")
                return self._compute_with_osrm(origin, destination, avoid_tolls, waypoints=waypoints)
        else:
            return self._compute_with_osrm(origin, destination, avoid_tolls, waypoints=waypoints)

    def _compute_with_google(
        self,
        origin: str,
        destination: str,
        avoid_tolls: bool,
        waypoints: Optional[List[str]] = None,
    ) -> Tuple[RouteResult, Dict[str, Any]]:
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.google_api_key,
            "X-Goog-FieldMask": (
                "routes.duration,"
                "routes.distanceMeters,"
                "routes.polyline.encodedPolyline,"
                "routes.travelAdvisory.tollInfo,"
                "routes.legs.travelAdvisory.tollInfo,"
                "routes.legs.steps"
            )
        }
        payload: Dict[str, Any] = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "extraComputations": ["TOLLS"],
            "routeModifiers": {
                "avoidTolls": avoid_tolls
            }
        }
        if waypoints:
            payload["intermediates"] = [{"address": w} for w in waypoints]
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code != 200:
            raise RuntimeError(f"Google API Error {response.status_code}: {response.text}")

        data = response.json()
        routes = data.get("routes", [])
        if not routes:
            raise RuntimeError("Nessun percorso trovato da Google Routes API.")

        primary_route = routes[0]
        distance_meters = primary_route.get("distanceMeters", 0)
        distance_km = round(distance_meters / 1000.0, 2)
        
        # duration è una stringa tipo "3600s"
        duration_str = primary_route.get("duration", "0s").replace("s", "")
        duration_seconds = float(duration_str) if duration_str else 0.0
        duration_minutes = round(duration_seconds / 60.0, 1)

        hours = int(duration_minutes // 60)
        minutes = int(duration_minutes % 60)
        formatted_duration = f"{hours}h {minutes}min" if hours > 0 else f"{minutes} min"

        route_result = RouteResult(
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            duration_formatted=formatted_duration,
            origin_resolved=origin,
            destination_resolved=destination,
            is_google_api=True,
            motorway_distance_km=None,
            steps_summary=[]
        )
        return route_result, primary_route

    def _geocode_nominatim(self, query: str) -> Tuple[float, float, str]:
        """Geocodifica un indirizzo usando OpenStreetMap Nominatim"""
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "TripCostCalculatorAgent/1.0 (Educational and Python Agent Project)"
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200 or not resp.json():
            raise ValueError(f"Impossibile geolocalizzare la località: '{query}'")
        
        item = resp.json()[0]
        lat = float(item["lat"])
        lon = float(item["lon"])
        display_name = item.get("display_name", query)
        return lat, lon, display_name

    def _compute_with_osrm(
        self,
        origin: str,
        destination: str,
        avoid_tolls: bool,
        waypoints: Optional[List[str]] = None,
    ) -> Tuple[RouteResult, Dict[str, Any]]:
        # 1. Geocoding (origine, eventuali waypoint, destinazione)
        lat1, lon1, name1 = self._geocode_nominatim(origin)
        coords: List[Tuple[float, float]] = [(lat1, lon1)]

        if waypoints:
            for wp in waypoints:
                if wp and wp.strip():
                    time.sleep(1)  # Rispetto delle policy di rate limit di Nominatim
                    w_lat, w_lon, _ = self._geocode_nominatim(wp.strip())
                    coords.append((w_lat, w_lon))

        time.sleep(1)  # Rispetto delle policy di rate limit di Nominatim
        lat2, lon2, name2 = self._geocode_nominatim(destination)
        coords.append((lat2, lon2))

        # 2. OSRM routing con geometria polyline completa per ricerche POI lungo il percorso
        coords_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
        osrm_url = (
            f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
            "?overview=full&geometries=polyline&steps=true"
        )
        resp = requests.get(osrm_url, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Errore OSRM routing: {resp.status_code}")

        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            raise RuntimeError(f"Nessuna rotta trovata da OSRM: {data.get('message', 'Errore')}")

        route = data["routes"][0]
        distance_meters = route.get("distance", 0)
        distance_km = round(distance_meters / 1000.0, 2)
        duration_seconds = route.get("duration", 0)
        duration_minutes = round(duration_seconds / 60.0, 1)

        hours = int(duration_minutes // 60)
        minutes = int(duration_minutes % 60)
        formatted_duration = f"{hours}h {minutes}min" if hours > 0 else f"{minutes} min"

        # Analisi dei tratti autostradali dagli step
        motorway_km = 0.0
        legs = route.get("legs", [])
        for leg in legs:
            for step in leg.get("steps", []):
                ref = step.get("ref", "")
                name = step.get("name", "")
                step_dist = step.get("distance", 0) / 1000.0
                # Se è un'autostrada (in Italia es. A1, A4, A14 o menziona Autostrada)
                if (ref and ref.startswith("A") and len(ref) <= 4 and any(c.isdigit() for c in ref)) or "autostrada" in name.lower():
                    motorway_km += step_dist

        motorway_km = round(motorway_km, 2)

        route_result = RouteResult(
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            duration_formatted=formatted_duration,
            origin_resolved=name1,
            destination_resolved=name2,
            is_google_api=False,
            motorway_distance_km=motorway_km,
            steps_summary=[]
        )

        encoded_polyline = route.get("geometry", "")
        raw_payload = {
            "source": "OSRM",
            "motorway_km": motorway_km,
            "distance_km": distance_km,
            "polyline": {
                "encodedPolyline": encoded_polyline
            },
        }
        return route_result, raw_payload
