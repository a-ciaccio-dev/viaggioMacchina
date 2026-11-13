"""
Unit test per PlacesAgent e l'aggiornamento di RouteAgent (Google Places/Routes API v2).
Tutte le chiamate HTTP sono simulate tramite unittest.mock.patch su requests.post.
"""
from unittest.mock import MagicMock, patch
import pytest
import requests

from agents.places_agent import PlacesAgent
from agents.route_agent import RouteAgent
from models.trip_models import RouteResult


def _make_mock_response(status_code: int = 200, json_data=None, text: str = "") -> MagicMock:
    """Crea un oggetto response simulato per requests.post."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = text
    mock_resp.json.return_value = json_data if json_data is not None else {}
    return mock_resp


# --- Test PlacesAgent ---


def test_places_agent_missing_api_key_raises_value_error():
    """Verifica che PlacesAgent sollevi ValueError se la chiave API manca e il fallback e' disattivato."""
    agent = PlacesAgent(google_maps_api_key="", use_overpass_fallback=False)
    with pytest.raises(ValueError, match="Chiave API Google Maps mancante"):
        agent.search_place("Ristorante Milano")

    agent_spaces = PlacesAgent(google_maps_api_key="   ", use_overpass_fallback=False)
    with pytest.raises(ValueError, match="Chiave API Google Maps mancante"):
        agent_spaces.search_along_route("benzinaio", "abcPolyline123")


def test_places_agent_missing_config_api_key_raises_value_error():
    """Verifica ValueError anche quando google_maps_api_key e' None, config e' vuoto e fallback disattivato."""
    with patch("agents.places_agent.GOOGLE_MAPS_API_KEY", ""):
        agent = PlacesAgent(google_maps_api_key=None, use_overpass_fallback=False)
        with pytest.raises(ValueError, match="Chiave API Google Maps mancante"):
            agent.search_place("Via Roma 10, Torino")


@patch("agents.places_agent.requests.post")
def test_places_agent_search_along_route(mock_post):
    """Verifica URL, header, payload con searchAlongRouteParameters e parsing di search_along_route."""
    expected_places = [
        {
            "id": "place_1",
            "displayName": {"text": "Area di Servizio Eni"},
            "formattedAddress": "A1 Km 120",
        }
    ]
    mock_post.return_value = _make_mock_response(
        status_code=200,
        json_data={"places": expected_places},
    )

    agent = PlacesAgent(google_maps_api_key="test-api-key")
    result = agent.search_along_route(
        text_query="stazione di servizio",
        encoded_polyline="encoded_poly_xyz",
        max_results=7,
    )

    assert result == expected_places
    mock_post.assert_called_once()

    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == PlacesAgent.SEARCH_TEXT_URL
    assert call_args[0] == "https://places.googleapis.com/v1/places:searchText"

    headers = call_kwargs["headers"]
    assert headers["X-Goog-Api-Key"] == "test-api-key"
    assert headers["X-Goog-FieldMask"] == PlacesAgent.DEFAULT_FIELD_MASK
    assert headers["Content-Type"] == "application/json"

    payload = call_kwargs["json"]
    assert payload == {
        "textQuery": "stazione di servizio",
        "maxResultCount": 7,
        "searchAlongRouteParameters": {
            "polyline": {
                "encodedPolyline": "encoded_poly_xyz",
            }
        },
    }


@patch("agents.places_agent.requests.post")
def test_places_agent_search_place_omits_route_parameters(mock_post):
    """Verifica che search_place non includa searchAlongRouteParameters nel payload."""
    expected_places = [
        {
            "id": "place_2",
            "displayName": {"text": "Duomo di Milano"},
            "formattedAddress": "Piazza del Duomo, Milano",
        }
    ]
    mock_post.return_value = _make_mock_response(
        status_code=200,
        json_data={"places": expected_places},
    )

    agent = PlacesAgent(google_maps_api_key="test-api-key")
    result = agent.search_place(text_query="Piazza del Duomo, Milano", max_results=3)

    assert result == expected_places
    mock_post.assert_called_once()

    _, call_kwargs = mock_post.call_args
    payload = call_kwargs["json"]
    assert "searchAlongRouteParameters" not in payload
    assert payload == {
        "textQuery": "Piazza del Duomo, Milano",
        "maxResultCount": 3,
    }


@patch("agents.places_agent.requests.post")
def test_places_agent_empty_places_returns_empty_list(mock_post):
    """Verifica che una risposta 200 senza chiave 'places' restituisca lista vuota."""
    mock_post.return_value = _make_mock_response(status_code=200, json_data={})

    agent = PlacesAgent(google_maps_api_key="test-api-key")
    assert agent.search_place("Indirizzo inesistente") == []


@patch("agents.places_agent.requests.post")
def test_places_agent_http_error_raises_runtime_error(mock_post):
    """Verifica che uno status HTTP != 200 sollevi RuntimeError."""
    mock_post.return_value = _make_mock_response(
        status_code=403,
        text="API key not valid",
    )

    agent = PlacesAgent(google_maps_api_key="bad-key")
    with pytest.raises(RuntimeError, match="Google Places API Error 403"):
        agent.search_place("Roma")


@patch("agents.places_agent.requests.post")
def test_places_agent_network_error_raises_runtime_error(mock_post):
    """Verifica che un'eccezione requests.RequestException sollevi RuntimeError."""
    mock_post.side_effect = requests.Timeout("Connection timed out")

    agent = PlacesAgent(google_maps_api_key="test-api-key")
    with pytest.raises(RuntimeError, match="Errore di rete durante la chiamata a Google Places API"):
        agent.search_along_route("autogrill", "poly_123")


# --- Test RouteAgent (Google Routes API v2) ---


def _google_route_response(encoded_polyline: str = "sample_encoded_polyline") -> MagicMock:
    """Costruisce una risposta valida simulata per Google Routes API v2."""
    return _make_mock_response(
        status_code=200,
        json_data={
            "routes": [
                {
                    "distanceMeters": 215000,
                    "duration": "7200s",
                    "polyline": {"encodedPolyline": encoded_polyline},
                    "travelAdvisory": {},
                    "legs": [],
                }
            ]
        },
    )


@patch("agents.route_agent.requests.post")
def test_route_agent_includes_polyline_field_mask_and_intermediates_with_waypoints(mock_post):
    """Verifica X-Goog-FieldMask con encodedPolyline e intermediates popolato quando ci sono waypoints."""
    mock_post.return_value = _google_route_response("poly_with_waypoints")

    agent = RouteAgent(google_maps_api_key="google-test-key")
    route_result, primary_route = agent.calculate_route(
        origin="Milano",
        destination="Bologna",
        avoid_tolls=False,
        waypoints=["Piacenza", "Parma"],
    )

    assert isinstance(route_result, RouteResult)
    assert route_result.is_google_api is True
    assert route_result.distance_km == 215.0
    assert route_result.duration_minutes == 120.0
    assert primary_route["polyline"]["encodedPolyline"] == "poly_with_waypoints"

    mock_post.assert_called_once()
    _, call_kwargs = mock_post.call_args

    headers = call_kwargs["headers"]
    assert headers["X-Goog-Api-Key"] == "google-test-key"
    assert "routes.polyline.encodedPolyline" in headers["X-Goog-FieldMask"]

    payload = call_kwargs["json"]
    assert payload["intermediates"] == [
        {"address": "Piacenza"},
        {"address": "Parma"},
    ]


@pytest.mark.parametrize("empty_waypoints", [None, []])
@patch("agents.route_agent.requests.post")
def test_route_agent_omits_intermediates_when_waypoints_none_or_empty(mock_post, empty_waypoints):
    """Verifica che intermediates sia omesso dal payload quando waypoints e' None o vuoto."""
    mock_post.return_value = _google_route_response("poly_no_waypoints")

    agent = RouteAgent(google_maps_api_key="google-test-key")
    route_result, primary_route = agent._compute_with_google(
        origin="Torino",
        destination="Genova",
        avoid_tolls=True,
        waypoints=empty_waypoints,
    )

    assert route_result.is_google_api is True
    assert primary_route["polyline"]["encodedPolyline"] == "poly_no_waypoints"

    mock_post.assert_called_once()
    _, call_kwargs = mock_post.call_args

    headers = call_kwargs["headers"]
    assert "routes.polyline.encodedPolyline" in headers["X-Goog-FieldMask"]

    payload = call_kwargs["json"]
    assert "intermediates" not in payload
    assert payload["routeModifiers"] == {"avoidTolls": True}
