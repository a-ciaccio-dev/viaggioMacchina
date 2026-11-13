from typing import Any, Dict, List, Optional
import requests

from agents.base_agent import BaseAgent
from config import GOOGLE_MAPS_API_KEY


class PlacesAgent(BaseAgent):
    """Agente per la ricerca di luoghi e punti di interesse tramite Google Places API (New)."""

    SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
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
