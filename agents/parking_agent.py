from typing import Optional, List
from agents.base_agent import BaseAgent
from models.trip_models import ParkingResult, ParkingOption

class ParkingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ParkingAgent",
            role="Ricerca normative, restrizioni e tariffe per il parcheggio nella città di destinazione per brevi e lunghi soggiorni."
        )

    def analyze_parking(self, destination: str, stay_days: int = 1) -> ParkingResult:
        """
        Analizza e stima i costi e le opzioni di parcheggio nella destinazione specificata.
        """
        dest_lower = destination.lower()

        # Caso Montreuil (93100) / Parigi periferia
        if "montreuil" in dest_lower or "93100" in dest_lower:
            return self._analyze_montreuil(stay_days)
        elif "parigi" in dest_lower or "paris" in dest_lower:
            return self._analyze_paris(stay_days)
        else:
            return self._analyze_generic(destination, stay_days)

    def _analyze_montreuil(self, stay_days: int) -> ParkingResult:
        regulations = (
            "A Montreuil la sosta su strada è regolamentata da Indigo e dal Comune in due zone:\n"
            "• Zona Verde: attiva lun-ven 9:00-19:00 (gratis sabato, domenica, festivi e agosto). Max 10h/giorno (~18 €/gg per non residenti).\n"
            "• Zona Rossa: solo sosta breve commerciale (max 2-3h, poi scatta FPS di 34 €).\n"
            "Attenzione: per legge francese (Code de la Route R417-12) è vietato lasciare l'auto nello stesso stallo oltre 7 giorni consecutivi (rischio rimozione forzata)."
        )

        options: List[ParkingOption] = []

        # 1. Opzione Strada Zona Verde
        # Calcolo giorni lavorativi approssimativi su stay_days
        working_days = int(stay_days * (5 / 7))
        street_cost = round(working_days * 18.20, 2)
        options.append(ParkingOption(
            name="Sosta su Strada (Zona Verde)",
            category="In strada (Voirie Indigo)",
            estimated_cost=street_cost,
            daily_rate=18.20,
            details=f"Pagamento giornaliero su app PayByPhone/EasyPark. Calcolato su ~{working_days} giorni feriali (weekend gratis). Sconsigliato oltre i 7 gg per divieto di sosta continuativa.",
            recommended=False
        ))

        # 2. Opzione Parcheggio Pubblico Sotterraneo (es. Indigo Mairie / Franklin)
        if stay_days <= 3:
            silos_cost = stay_days * 22.0
            silos_desc = "Tariffa giornaliera forfettaria Indigo Mairie."
        else:
            weeks = max(1, round(stay_days / 7))
            silos_cost = weeks * 85.0
            silos_desc = f"Forfait plurisettimanale (~{weeks} settimane) in parcheggio coperto custodito."
        options.append(ParkingOption(
            name="Parcheggio Pubblico Coperto (Indigo Mairie / Franklin)",
            category="Silos Sotterraneo Pubblico",
            estimated_cost=round(silos_cost, 2),
            daily_rate=round(silos_cost / stay_days, 2),
            details=silos_desc,
            recommended=False
        ))

        # 3. Opzione Parcheggio Condiviso Lunga Sosta (Zenpark / Yespark)
        # Ideale per soggiorni di 15 giorni (formula abbonamento 1 mese senza vincoli)
        if stay_days >= 7:
            zenpark_cost = 98.00  # Abbonamento mensile medio senza vincolo a Montreuil
            zenpark_desc = "Abbonamento mensile 24/7 senza vincoli in garage privato residenziale videosorvegliato con apertura via app (disattivabile a fine soggiorno)."
            is_rec = True
        else:
            zenpark_cost = stay_days * 14.0
            zenpark_desc = f"Prenotazione giornaliera flessibile in box privato tramite app Zenpark."
            is_rec = True

        options.append(ParkingOption(
            name="Parcheggio Privato Condiviso (Zenpark / Yespark)",
            category="Garage Privato Coperto (App)",
            estimated_cost=zenpark_cost,
            daily_rate=round(zenpark_cost / stay_days, 2),
            details=zenpark_desc,
            recommended=is_rec
        ))

        # Raccomandazione
        if stay_days >= 10:
            rec_sol = (
                "Abbonamento mensile Zenpark/Yespark (~98 €): è la soluzione più sicura ed economica "
                "per 15 giorni. Evita il limite legale dei 7 giorni in strada e costa la metà della sosta pubblica."
            )
            rec_cost = zenpark_cost
        else:
            rec_sol = "Parcheggio coperto Zenpark o Zona Verde su strada nei giorni feriali."
            rec_cost = min(o.estimated_cost for o in options)

        apps = ["Zenpark", "Yespark", "PayByPhone", "Indigo Neo", "EasyPark"]

        return ParkingResult(
            destination="Montreuil (93100, Francia)",
            stay_days=stay_days,
            regulations_summary=regulations,
            options=options,
            recommended_solution=rec_sol,
            recommended_cost=rec_cost,
            useful_apps=apps
        )

    def _analyze_paris(self, stay_days: int) -> ParkingResult:
        regulations = (
            "A Parigi intramuros la sosta su strada per i non residenti è costosissima (fino a 6-8 €/ora) "
            "e limitata a massimo 6 ore consecutive. È indispensabile utilizzare un parcheggio sotterraneo a lunga sosta."
        )
        cost_silos = stay_days * 28.0 if stay_days < 7 else 140.0 * (stay_days / 7)
        zenpark_cost = 135.0 if stay_days >= 10 else stay_days * 20.0

        options = [
            ParkingOption(
                name="Parcheggio Sotterraneo Saemes / Indigo",
                category="Silos Pubblico",
                estimated_cost=round(cost_silos, 2),
                details="Prenotabile in anticipo online con tariffa forfait turistico.",
                recommended=stay_days < 5
            ),
            ParkingOption(
                name="Abbonamento Lunga Sosta Zenpark / Yespark",
                category="Garage Privato Condiviso",
                estimated_cost=zenpark_cost,
                details="Abbonamento mensile senza impegno per soggiorni lunghi.",
                recommended=stay_days >= 5
            )
        ]

        return ParkingResult(
            destination="Parigi (Francia)",
            stay_days=stay_days,
            regulations_summary=regulations,
            options=options,
            recommended_solution="Parcheggio sotterraneo custodito (Zenpark o Saemes) con prenotazione anticipata.",
            recommended_cost=zenpark_cost,
            useful_apps=["Zenpark", "Saemes", "Indigo Neo", "Parclick"]
        )

    def _analyze_generic(self, destination: str, stay_days: int) -> ParkingResult:
        regulations = (
            f"Regolamentazione standard per {destination}: la sosta su strada è generalmente a pagamento "
            "nelle aree centrali (strisce blu o equivalenti, 9:00-19:00 feriali). Per soggiorni prolungati si consigliano parcheggi scambiatori (P+R) o silos custoditi."
        )
        street_estimate = round(stay_days * 12.0, 2)
        silos_estimate = round(stay_days * 18.0, 2)

        options = [
            ParkingOption(
                name="Sosta su Strada (Strisce Blu / Zone Tariffate)",
                category="In strada",
                estimated_cost=street_estimate,
                daily_rate=12.0,
                details="Tariffa media oraria giornaliera nei giorni feriali.",
                recommended=stay_days <= 2
            ),
            ParkingOption(
                name="Parcheggio di Struttura / Silos Custodito",
                category="Silos Coperto",
                estimated_cost=silos_estimate,
                daily_rate=18.0,
                details="Posto auto protetto e videosorvegliato con tariffa giornaliera forfettaria.",
                recommended=stay_days > 2
            )
        ]

        return ParkingResult(
            destination=destination,
            stay_days=stay_days,
            regulations_summary=regulations,
            options=options,
            recommended_solution="Parcheggio di struttura o P+R per soste prolungate oltre 2 giorni.",
            recommended_cost=silos_estimate if stay_days > 2 else street_estimate,
            useful_apps=["EasyPark", "Parkopedia", "Google Maps"]
        )
