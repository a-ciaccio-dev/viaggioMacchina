"""
Unit test per PlacesAgent e l'aggiornamento di RouteAgent (Google Places/Routes API v2).
Tutte le chiamate HTTP sono simulate tramite unittest.mock.patch su requests.post.
"""
from unittest.mock import MagicMock, patch
import pytest
import requests

from agents.places_agent import PlacesAgent, decode_polyline, sample_route_points
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


# --- Test Overpass / OSRM Fallback ---


def test_decode_polyline_and_sample_route_points():
    """Verifica il decoder polyline5 standard e il campionamento punti lungo la rotta."""
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert len(pts) == 3
    assert pts[0] == pytest.approx((38.5, -120.2), abs=1e-4)
    assert pts[1] == pytest.approx((40.7, -120.95), abs=1e-4)
    assert pts[2] == pytest.approx((43.252, -126.453), abs=1e-4)

    sampled = sample_route_points(pts, step_km=500.0)
    assert sampled[0] == pts[0]
    assert sampled[-1] == pts[-1]


@patch("agents.places_agent.requests.post")
def test_places_agent_overpass_fallback_search_along_route(mock_post):
    """Verifica che PlacesAgent senza API key interroghi Overpass API e normalizzi i risultati."""
    mock_post.return_value = _make_mock_response(
        status_code=200,
        json_data={
            "elements": [
                {
                    "type": "node",
                    "id": 101,
                    "lat": 40.7,
                    "lon": -120.95,
                    "tags": {
                        "amenity": "fuel",
                        "brand": "TotalEnergies",
                        "name": "Relais Autoroute",
                        "ref": "A4",
                    },
                },
                {
                    "type": "way",
                    "id": 202,
                    "center": {"lat": 38.5, "lon": -120.2},
                    "tags": {
                        "amenity": "fuel",
                        "name": "TotalEnergies Aire Nord",
                        "addr:street": "Autoroute A4",
                        "addr:city": "Reims",
                    },
                },
            ]
        },
    )

    agent = PlacesAgent(google_maps_api_key="")
    results = agent.search_along_route(
        text_query="TotalEnergies",
        encoded_polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@",
        max_results=5,
    )

    assert len(results) == 2
    assert results[0]["source"] == "overpass"
    assert results[0]["id"] == "osm:way/202"
    assert results[0]["displayName"]["text"] == "TotalEnergies Aire Nord"
    assert "Autoroute A4, Reims" in results[0]["formattedAddress"]
    assert results[1]["id"] == "osm:node/101"
    assert results[1]["displayName"]["text"] == "TotalEnergies - Relais Autoroute"

    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == PlacesAgent.OVERPASS_URL
    query_sent = call_kwargs["data"]["data"]
    assert '["amenity"="fuel"]["brand"~"Total",i]' in query_sent


@patch("agents.places_agent.requests.post")
def test_places_agent_overpass_http_error_raises_runtime_error(mock_post):
    """Verifica che errori HTTP di Overpass sollevino RuntimeError."""
    mock_post.return_value = _make_mock_response(status_code=504, text="Gateway Timeout")
    agent = PlacesAgent(google_maps_api_key="")
    with pytest.raises(RuntimeError, match="Overpass API Error 504"):
        agent.search_along_route("TotalEnergies", "_p~iF~ps|U_ulLnnqC")


@patch("agents.places_agent.requests.get")
def test_places_agent_nominatim_fallback_search_place(mock_get):
    """Verifica che search_place senza API key usi Nominatim e normalizzi i risultati."""
    mock_get.return_value = _make_mock_response(
        status_code=200,
        json_data=[
            {
                "osm_type": "node",
                "osm_id": 999,
                "lat": "48.86",
                "lon": "2.44",
                "display_name": "Montreuil, Seine-Saint-Denis, France",
            }
        ],
    )

    agent = PlacesAgent(google_maps_api_key="")
    results = agent.search_place("Montreuil, France", max_results=3)

    assert len(results) == 1
    assert results[0]["source"] == "nominatim"
    assert results[0]["displayName"]["text"] == "Montreuil"
    assert results[0]["location"] == {"latitude": 48.86, "longitude": 2.44}


@patch("agents.route_agent.time.sleep")
@patch("agents.route_agent.requests.get")
def test_route_agent_osrm_with_waypoints_and_polyline(mock_get, mock_sleep):
    """Verifica che RouteAgent OSRM supporti waypoints ed esponga polyline.encodedPolyline."""
    mock_get.side_effect = [
        _make_mock_response(200, [{"lat": "48.86", "lon": "2.44", "display_name": "Montreuil"}]),
        _make_mock_response(200, [{"lat": "49.25", "lon": "4.03", "display_name": "Reims"}]),
        _make_mock_response(200, [{"lat": "49.12", "lon": "6.17", "display_name": "Metz"}]),
        _make_mock_response(
            200,
            {
                "code": "Ok",
                "routes": [
                    {
                        "distance": 330000,
                        "duration": 11400,
                        "geometry": "osrmEncodedPolyline123",
                        "legs": [
                            {
                                "steps": [
                                    {"ref": "A4", "name": "Autoroute de l'Est", "distance": 280000}
                                ]
                            }
                        ],
                    }
                ],
            },
        ),
    ]

    agent = RouteAgent(google_maps_api_key="")
    route_result, raw_payload = agent.calculate_route(
        origin="Montreuil",
        destination="Metz",
        waypoints=["Reims"],
    )

    assert route_result.is_google_api is False
    assert route_result.distance_km == 330.0
    assert raw_payload["source"] == "OSRM"
    assert raw_payload["polyline"]["encodedPolyline"] == "osrmEncodedPolyline123"

    osrm_call_url = mock_get.call_args_list[-1][0][0]
    assert "2.44,48.86;4.03,49.25;6.17,49.12" in osrm_call_url
    assert "overview=full" in osrm_call_url
    assert "geometries=polyline" in osrm_call_url
