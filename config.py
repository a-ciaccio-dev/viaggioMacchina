import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

DEFAULT_PRICES = {
    "benzina": float(os.getenv("DEFAULT_GASOLINE_PRICE", "2.02")),
    "diesel": float(os.getenv("DEFAULT_DIESEL_PRICE", "1.92")),
    "gpl": float(os.getenv("DEFAULT_LPG_PRICE", "0.78")),
    "metano": float(os.getenv("DEFAULT_CNG_PRICE", "1.45")),
    "elettrico": float(os.getenv("DEFAULT_ELECTRIC_PRICE_KWH", "0.45")),
}

# Tariffa chilometrica media stimata autostrade italiane (classe A - autovetture standard a 2 assi)
# Circa 0.075 € - 0.085 € / km per tratte autostradali con iva inclusa
AVERAGE_ITALY_TOLL_PER_KM = 0.082
