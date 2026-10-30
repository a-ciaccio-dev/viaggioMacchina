from typing import Optional, List, Literal
from pydantic import BaseModel, Field

FuelType = Literal["benzina", "diesel", "gpl", "metano", "elettrico"]
FuelUnit = Literal["km_l", "l_100km"]

class TripInput(BaseModel):
    origin: str = Field(..., description="Città o indirizzo di partenza")
    destination: str = Field(..., description="Città o indirizzo di arrivo")
    fuel_consumption: float = Field(..., gt=0, description="Consumo medio del veicolo")
    fuel_unit: FuelUnit = Field(default="km_l", description="Unità del consumo ('km_l' o 'l_100km')")
    fuel_type: FuelType = Field(default="benzina", description="Tipo di alimentazione")
    custom_fuel_price: Optional[float] = Field(default=None, gt=0, description="Prezzo al litro/kWh (€) personalizzato")
    passengers: int = Field(default=1, ge=1, description="Numero di persone a bordo per dividere le spese")
    stay_days: int = Field(default=1, ge=1, description="Numero di giorni di soggiorno a destinazione")
    avoid_tolls: bool = Field(default=False, description="Se True, cerca di evitare i pedaggi")

class RouteResult(BaseModel):
    distance_km: float
    duration_minutes: float
    duration_formatted: str
    origin_resolved: str
    destination_resolved: str
    is_google_api: bool = False
    motorway_distance_km: Optional[float] = None
    steps_summary: List[str] = Field(default_factory=list)

class TollResult(BaseModel):
    total_toll_cost: float
    toll_source: str
    currency: str = "EUR"
    notes: Optional[str] = None

class FuelResult(BaseModel):
    fuel_type: FuelType
    fuel_unit: FuelUnit
    consumption_rate: float
    effective_liters: float
    fuel_price_per_unit: float
    total_fuel_cost: float
    cost_per_km: float

class HotelPriceVerification(BaseModel):
    hotel_name: str
    official_price: float
    official_url: str
    booking_price: float
    booking_url: str
    discrepancy: float
    status: str  # es: "CONFERMATO", "DISCREPANZA RILEVATA", "PREZZO PIÙ BASSO"
    alert_level: str  # "INFO", "WARNING", "SUCCESS"
    best_channel: str
    notes: str

class HotelOption(BaseModel):
    name: str
    stars: str = "3★"
    location: str
    highway_exit: str
    room_type: str = "Camera Tripla (3 Persone)"
    price_total: float
    price_per_person: float
    parking_info: str
    checkin_info: str
    booking_platforms: List[str] = Field(default_factory=list)
    official_url: Optional[str] = None
    booking_url: Optional[str] = None
    verification_status: Optional[str] = "VERIFICATO"
    verified_price_booking: Optional[float] = None
    verified_price_official: Optional[float] = None
    price_discrepancy: Optional[float] = None
    price_alert_note: Optional[str] = None
    best_channel: Optional[str] = None
    recommended: bool = False
    highlights: str

class HotelSearchResult(BaseModel):
    stopover_city: str
    km_from_origin: float
    km_to_destination: float
    split_day1: str
    split_day2: str
    hotels: List[HotelOption] = Field(default_factory=list)
    verifications: List[HotelPriceVerification] = Field(default_factory=list)
    verification_summary: Optional[str] = None
    discrepancies_detected: int = 0
    recommended_hotel: str
    tips: List[str] = Field(default_factory=list)

class ParkingOption(BaseModel):
    name: str
    category: str # es. "In Strada (Zona Verde)", "Sotterraneo Custodito (Zenpark)", ecc.
    estimated_cost: float
    daily_rate: Optional[float] = None
    details: str
    recommended: bool = False

class ParkingResult(BaseModel):
    destination: str
    stay_days: int
    regulations_summary: str
    options: List[ParkingOption] = Field(default_factory=list)
    recommended_solution: str
    recommended_cost: float
    useful_apps: List[str] = Field(default_factory=list)

class TripReport(BaseModel):
    origin: str
    destination: str
    stay_days: int = 1
    route: RouteResult
    toll: TollResult
    fuel: FuelResult
    parking: Optional[ParkingResult] = None
    hotel_stopover: Optional[HotelSearchResult] = None
    passengers: int
    total_trip_cost: float
    cost_per_passenger: float
    savings_vs_notolls: Optional[float] = None
