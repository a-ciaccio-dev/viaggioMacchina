import math
import re
from typing import Any, Dict, List, Optional, Tuple
import requests

from agents.base_agent import BaseAgent
from config import GOOGLE_MAPS_API_KEY


def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    """Decodifica una polyline5 (formato Google/OSRM) in lista di tuple (lat, lon)."""
    if not encoded:
        return []

    points: List[Tuple[float, float]] = []
    index = 0
    lat = 0
    lon = 0
    length = len(encoded)

    while index < length:
        for is_lon in (False, True):
            shift = 0
            result = 0
            while index < length:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lon:
                lon += delta
            else:
                lat += delta
        points.append((lat / 1e5, lon / 1e5))

    return points


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcola la distanza geodetica approssimata in km tra due coordinate."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def sample_route_points(
    points: List[Tuple[float, float]],
    step_km: float = 25.0,
    max_points: int = 40,
) -> List[Tuple[float, float]]:
    """Campiona punti lungo la rotta ogni `step_km` km mantenendo inizio e fine."""
    if len(points) <= 2:
        return list(points)

    sampled: List[Tuple[float, float]] = [points[0]]
    acc_km = 0.0
    prev = points[0]

    for curr in points[1:-1]:
        acc_km += haversine_km(prev[0], prev[1], curr[0], curr[1])
        if acc_km >= step_km:
            sampled.append(curr)
            acc_km = 0.0
        prev = curr

    if sampled[-1] != points[-1]:
        sampled.append(points[-1])

    if len(sampled) > max_points:
        stride = math.ceil(len(sampled) / max_points)
        reduced = sampled[::stride]
        if reduced[-1] != sampled[-1]:
            reduced.append(sampled[-1])
        return reduced

    return sampled


class PlacesAgent(BaseAgent):
    """Agente per la ricerca di luoghi e punti di interesse tramite Google Places API (New)."""

    SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    DEFAULT_FIELD_MASK = (
        "places.id,"
        "places.displayName,"
        "places.formattedAddress,"
        "places.location,"
        "places.googleMapsUri,"
        "places.businessStatus,"
        "places.currentOpeningHours.openNow"
    )

    def __init__(self, google_maps_api_key: Optional[str] = None):
        super().__init__(
            name="PlacesAgent",
            role="Cerca luoghi, indirizzi e punti di interesse lungo un itinerario tramite Google Places API (New)."
        )
        raw_key = google_maps_api_key if google_maps_api_key is not None else GOOGLE_MAPS_API_KEY
        self.google_api_key: str = raw_key.strip() if raw_key else ""

    def search_along_route(
        self,
        text_query: str,
        encoded_polyline: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Cerca luoghi lungo un percorso codificato (encoded polyline).

        Args:
            text_query: Testo della ricerca (es. "stazione di servizio", "ristorante").
            encoded_polyline: Polyline codificata restituita da Google Routes API v2.
            max_results: Numero massimo di risultati da restituire (default 10).

        Returns:
            Lista di dizionari rappresentanti i luoghi trovati.
        """
        payload: Dict[str, Any] = {
            "textQuery": text_query,
            "maxResultCount": max_results,
            "searchAlongRouteParameters": {
                "polyline": {
                    "encodedPolyline": encoded_polyline
                }
            },
        }
        return self._search_text(payload)

    def search_place(
        self,
        text_query: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Cerca luoghi o verifica indirizzi esatti e numeri civici tramite ricerca testuale.

        Args:
            text_query: Testo della ricerca o indirizzo completo.
            max_results: Numero massimo di risultati da restituire (default 5).

        Returns:
            Lista di dizionari rappresentanti i luoghi trovati.
        """
        payload: Dict[str, Any] = {
            "textQuery": text_query,
            "maxResultCount": max_results,
        }
        return self._search_text(payload)

    def _search_text(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Esegue la chiamata POST verso Places API (New) places:searchText."""
        if not self.google_api_key:
            raise ValueError(
                "Chiave API Google Maps mancante: impostare 'GOOGLE_MAPS_API_KEY' in config/env "
                "oppure passarla al costruttore di PlacesAgent."
            )

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.google_api_key,
            "X-Goog-FieldMask": self.DEFAULT_FIELD_MASK,
        }

        try:
            response = requests.post(
                self.SEARCH_TEXT_URL,
                json=payload,
                headers=headers,
                timeout=12,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Errore di rete durante la chiamata a Google Places API: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"Google Places API Error {response.status_code}: {response.text}"
            )

        data = response.json()
        return data.get("places", [])

    def _build_overpass_around_query(
        self,
        points: List[Tuple[float, float]],
        text_query: str,
        radius_meters: int = 2500,
    ) -> str:
        """Costruisce una query Overpass QL `around` lungo i punti campionati della rotta."""
        coords_csv = ",".join(f"{lat:.5f},{lon:.5f}" for lat, lon in points)
        q_lower = text_query.lower()

        fuel_keywords = ("fuel", "benzina", "diesel", "carburante", "stazione", "distributore", "total")
        is_fuel = any(k in q_lower for k in fuel_keywords)

        brand_filter = ""
        if "total" in q_lower:
            brand_filter = '["brand"~"Total",i]'
        elif not is_fuel:
            safe_token = re.sub(r'["\\]', "", text_query.strip())
            if safe_token:
                brand_filter = f'["name"~"{safe_token}",i]'

        if is_fuel and "total" in q_lower:
            return (
                "[out:json][timeout:25];\n"
                "(\n"
                f'  nwr(around:{radius_meters},{coords_csv})["amenity"="fuel"]["brand"~"Total",i];\n'
                f'  nwr(around:{radius_meters},{coords_csv})["amenity"="fuel"]["name"~"Total",i];\n'
                f'  nwr(around:{radius_meters},{coords_csv})["amenity"="fuel"]["operator"~"Total",i];\n'
                ");\n"
                "out center;"
            )
        if is_fuel:
            return (
                "[out:json][timeout:25];\n"
                f'nwr(around:{radius_meters},{coords_csv})["amenity"="fuel"];\n'
                "out center;"
            )

        return (
            "[out:json][timeout:25];\n"
            f'nwr(around:{radius_meters},{coords_csv}){brand_filter};\n'
            "out center;"
        )

    def _query_overpass(self, query: str) -> List[Dict[str, Any]]:
        """Esegue una query POST verso Overpass API e restituisce gli elementi grezzi."""
        headers = {
            "User-Agent": "TripCostCalculatorAgent/1.0 (OpenStreetMap Overpass Fallback)"
        }
        try:
            response = requests.post(
                self.OVERPASS_URL,
                data={"data": query},
                headers=headers,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Errore di rete durante la chiamata a Overpass API: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(f"Overpass API Error {response.status_code}: {response.text}")

        return response.json().get("elements", [])
