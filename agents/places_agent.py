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
    OVERPASS_MIRRORS = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    )
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

    def __init__(
        self,
        google_maps_api_key: Optional[str] = None,
        use_overpass_fallback: bool = True,
    ):
        super().__init__(
            name="PlacesAgent",
            role="Cerca luoghi, indirizzi e punti di interesse lungo un itinerario tramite Google Places API (New) o fallback OpenStreetMap/Overpass."
        )
        raw_key = google_maps_api_key if google_maps_api_key is not None else GOOGLE_MAPS_API_KEY
        self.google_api_key: str = raw_key.strip() if raw_key else ""
        self.use_overpass_fallback = use_overpass_fallback

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
        if not self.google_api_key and self.use_overpass_fallback:
            return self._search_along_route_overpass(
                text_query=text_query,
                encoded_polyline=encoded_polyline,
                max_results=max_results,
            )

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
        if not self.google_api_key and self.use_overpass_fallback:
            return self._search_place_nominatim(
                text_query=text_query,
                max_results=max_results,
            )

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
        """Costruisce una query Overpass QL su bounding-box del corridoio per risposte rapide."""
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        pad_deg = max(0.03, radius_meters / 111000.0)
        south = min(lats) - pad_deg
        north = max(lats) + pad_deg
        west = min(lons) - pad_deg
        east = max(lons) + pad_deg
        bbox = f"{south:.4f},{west:.4f},{north:.4f},{east:.4f}"

        q_lower = text_query.lower()
        fuel_keywords = ("fuel", "benzina", "diesel", "carburante", "stazione", "distributore", "total")
        is_fuel = any(k in q_lower for k in fuel_keywords)

        if is_fuel and "total" in q_lower:
            return (
                "[out:json][timeout:25];\n"
                f'nwr["amenity"="fuel"]["brand"~"Total",i]({bbox});\n'
                "out center;"
            )
        if is_fuel:
            return (
                "[out:json][timeout:25];\n"
                f'nwr["amenity"="fuel"]({bbox});\n'
                "out center;"
            )

        safe_token = re.sub(r'["\\]', "", text_query.strip())
        name_filter = f'["name"~"{safe_token}",i]' if safe_token else ""
        return (
            "[out:json][timeout:25];\n"
            f"nwr{name_filter}({bbox});\n"
            "out center;"
        )

    def _query_overpass(self, query: str) -> List[Dict[str, Any]]:
        """Esegue una query POST verso Overpass API (con fallback su mirror pubblici) e restituisce gli elementi grezzi."""
        headers = {
            "User-Agent": "TripCostCalculatorAgent/1.0 (OpenStreetMap Overpass Fallback)"
        }
        last_error: Optional[str] = None
        for idx, url in enumerate(self.OVERPASS_MIRRORS):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers=headers,
                    timeout=30,
                )
            except requests.RequestException as exc:
                last_error = f"Errore di rete durante la chiamata a Overpass API ({url}): {exc}"
                continue

            if response.status_code == 200:
                return response.json().get("elements", [])

            last_error = f"Overpass API Error {response.status_code}: {response.text}"
            if response.status_code not in (429, 502, 503, 504) or idx == len(self.OVERPASS_MIRRORS) - 1:
                raise RuntimeError(last_error)

        raise RuntimeError(last_error or "Overpass API non disponibile")

    def _normalize_overpass_element(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalizza un elemento Overpass nello stesso formato di Google Places API (New)."""
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            center = element.get("center") or {}
            lat = center.get("lat")
            lon = center.get("lon")
        if lat is None or lon is None:
            return None

        tags = element.get("tags") or {}
        name = tags.get("name") or tags.get("brand") or tags.get("operator") or "Senza nome"
        brand = tags.get("brand")
        if brand and brand.lower() not in name.lower():
            display_name = f"{brand} - {name}"
        else:
            display_name = name

        addr_parts = [
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
            tags.get("addr:postcode"),
            tags.get("addr:city"),
            tags.get("addr:country"),
        ]
        address = ", ".join(p for p in addr_parts if p)
        if not address:
            ref = tags.get("ref") or tags.get("highway")
            address = f"Area lungo {ref}" if ref else f"{lat:.5f}, {lon:.5f}"

        el_type = element.get("type", "node")
        el_id = element.get("id", "")
        return {
            "id": f"osm:{el_type}/{el_id}",
            "displayName": {"text": display_name},
            "formattedAddress": address,
            "location": {"latitude": float(lat), "longitude": float(lon)},
            "googleMapsUri": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
            "source": "overpass",
            "osmTags": tags,
        }

    def _search_along_route_overpass(
        self,
        text_query: str,
        encoded_polyline: str,
        max_results: int = 10,
        radius_meters: int = 2500,
    ) -> List[Dict[str, Any]]:
        """Fallback Overpass API lungo la polilinea codificata della rotta."""
        points = decode_polyline(encoded_polyline)
        if not points:
            return []

        sampled = sample_route_points(points, step_km=25.0, max_points=40)
        query = self._build_overpass_around_query(
            points=sampled,
            text_query=text_query,
            radius_meters=radius_meters,
        )
        elements = self._query_overpass(query)

        seen_ids = set()
        normalized_with_order: List[Tuple[int, Dict[str, Any]]] = []
        dense_points = sample_route_points(points, step_km=5.0, max_points=250)
        max_dist_km = max(3.0, radius_meters / 1000.0)
        for el in elements:
            item = self._normalize_overpass_element(el)
            if not item or item["id"] in seen_ids:
                continue
            p_lat = item["location"]["latitude"]
            p_lon = item["location"]["longitude"]
            best_idx = min(
                range(len(dense_points)),
                key=lambda i: haversine_km(p_lat, p_lon, dense_points[i][0], dense_points[i][1]),
            )
            min_dist = haversine_km(
                p_lat, p_lon, dense_points[best_idx][0], dense_points[best_idx][1]
            )
            if len(dense_points) > 3 and min_dist > max_dist_km:
                continue
            seen_ids.add(item["id"])
            normalized_with_order.append((best_idx, item))

        normalized_with_order.sort(key=lambda pair: pair[0])
        return [item for _, item in normalized_with_order[:max_results]]

    def _search_place_nominatim(
        self,
        text_query: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fallback Nominatim per ricerca testuale senza Google Maps API Key."""
        headers = {
            "User-Agent": "TripCostCalculatorAgent/1.0 (OpenStreetMap Nominatim Fallback)"
        }
        params = {
            "q": text_query,
            "format": "json",
            "limit": max_results,
        }
        try:
            response = requests.get(
                self.NOMINATIM_URL,
                params=params,
                headers=headers,
                timeout=12,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Errore di rete durante la chiamata a Nominatim: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(f"Nominatim Error {response.status_code}: {response.text}")

        results: List[Dict[str, Any]] = []
        for item in response.json():
            lat = float(item["lat"])
            lon = float(item["lon"])
            display_name = item.get("display_name", text_query)
            results.append(
                {
                    "id": f"osm:{item.get('osm_type', 'node')}/{item.get('osm_id', '')}",
                    "displayName": {"text": display_name.split(",")[0].strip()},
                    "formattedAddress": display_name,
                    "location": {"latitude": lat, "longitude": lon},
                    "googleMapsUri": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
                    "source": "nominatim",
                }
            )
        return results[:max_results]
