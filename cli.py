import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm
from models.trip_models import TripInput, FuelType, FuelUnit, TripReport, ParkingResult
from agents.coordinator_agent import CoordinatorAgent
from config import DEFAULT_PRICES, GOOGLE_MAPS_API_KEY

console = Console()

def print_banner():
    banner_text = (
        "[bold cyan]🚗 TRIP COST CALCULATOR - MULTI-AGENT SYSTEM[/bold cyan]\n"
        "[dim]Team di agenti specializzati per percorsi, pedaggi, consumi e parcheggi a destinazione[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan", expand=False))

def prompt_trip_data() -> TripInput:
    console.print("\n[bold yellow]📍 1. Informazioni sull'Itinerario[/bold yellow]")
    origin = Prompt.ask("[bold]Punto di partenza[/bold] (es. Tolmezzo, Milano, Bologna)").strip()
    destination = Prompt.ask("[bold]Punto di arrivo[/bold] (es. Montreuil 93100 Francia, Parigi, Roma)").strip()
    stay_days = IntPrompt.ask("[bold]Giorni di soggiorno a destinazione[/bold]", default=1)

    console.print("\n[bold yellow]⛽ 2. Veicolo e Consumi[/bold yellow]")
    fuel_unit_choice = Prompt.ask(
        "[bold]Formato consumo[/bold]",
        choices=["km/l", "l/100km"],
        default="km/l"
    )
    fuel_unit: FuelUnit = "km_l" if fuel_unit_choice == "km/l" else "l_100km"

    unit_label = "km con 1 litro" if fuel_unit == "km_l" else "litri per 100 km"
    fuel_consumption = FloatPrompt.ask(f"[bold]Consumo medio della macchina[/bold] ({unit_label})")

    fuel_type_choice = Prompt.ask(
        "[bold]Tipo di alimentazione[/bold]",
        choices=["benzina", "diesel", "gpl", "metano", "elettrico"],
        default="benzina"
    ).lower()
    fuel_type: FuelType = fuel_type_choice # type: ignore

    default_price = DEFAULT_PRICES.get(fuel_type, 1.85)
    unit_str = "€/kWh" if fuel_type == "elettrico" else "€/litro"
    
    use_custom_price = Confirm.ask(
        f"Vuoi indicare un prezzo specifico del carburante? (Default stimato: [green]{default_price:.3f} {unit_str}[/green])",
        default=False
    )
    
    custom_fuel_price = None
    if use_custom_price:
        custom_fuel_price = FloatPrompt.ask(f"[bold]Inserisci il prezzo ({unit_str})[/bold]")

    console.print("\n[bold yellow]👥 3. Preferenze e Passeggeri[/bold yellow]")
    passengers = IntPrompt.ask("[bold]Numero di passeggeri[/bold] (per dividere i costi)", default=1)
    avoid_tolls = Confirm.ask("Vuoi impostare il percorso evitando pedaggi autostradali?", default=False)

    return TripInput(
        origin=origin,
        destination=destination,
        stay_days=stay_days,
        fuel_consumption=fuel_consumption,
        fuel_unit=fuel_unit,
        fuel_type=fuel_type,
        custom_fuel_price=custom_fuel_price,
        passengers=passengers,
        avoid_tolls=avoid_tolls
    )

def render_report_table(report: TripReport, title: str = "RIEPILOGO COSTI DI VIAGGIO"):
    table = Table(title=f"[bold green]{title}[/bold green]", border_style="bright_blue", show_header=True, header_style="bold magenta")
    table.add_column("Categoria", style="cyan", width=24)
    table.add_column("Dettaglio", style="white", width=44)
    table.add_column("Costo (€)", justify="right", style="bold yellow", width=14)

    # Tratta
    provider_str = "Google Maps API" if report.route.is_google_api else "OpenStreetMap (OSRM)"
    table.add_row("Partenza", report.route.origin_resolved[:42], "")
    table.add_row("Arrivo", report.route.destination_resolved[:42], "")
    table.add_row("Distanza tratta", f"{report.route.distance_km:.1f} km ({provider_str})", "")
    table.add_row("Tempo stimato", report.route.duration_formatted, "")
    table.add_row("Durata soggiorno", f"{report.stay_days} giorni a destinazione", "")

    table.add_section()

    # Carburante
    unit_symbol = "kWh" if report.fuel.fuel_type == "elettrico" else "L"
    fuel_desc = f"{report.fuel.effective_liters:.2f} {unit_symbol} ({report.fuel.fuel_price_per_unit:.3f} €/{unit_symbol})"
    table.add_row(f"Carburante (Sola Andata)", fuel_desc, f"{report.fuel.total_fuel_cost:.2f} €")
    table.add_row("Incidenza carburante", f"{report.fuel.cost_per_km:.3f} €/km", "")

    table.add_section()

    # Pedaggi
    toll_desc = report.toll.notes or report.toll.toll_source
    if len(toll_desc) > 42:
        toll_desc = toll_desc[:39] + "..."
    table.add_row("Pedaggi Autostradali", f"{toll_desc}", f"{report.toll.total_toll_cost:.2f} €")

    table.add_section()

    # Totali viaggio andata
    table.add_row("[bold white]TOTALE VIAGGIO (Andata)[/bold white]", "[bold white]Carburante + Pedaggi[/bold white]", f"[bold green]{report.total_trip_cost:.2f} €[/bold green]")
    if report.passengers > 1:
        table.add_row(f"[bold cyan]Quota a Persona[/bold cyan]", f"Diviso per {report.passengers} passeggeri", f"[bold cyan]{report.cost_per_passenger:.2f} €[/bold cyan]")

    console.print(table)

def render_parking_table(parking: ParkingResult):
    console.print("\n")
    p_table = Table(
        title=f"[bold blue]🅿️ ANALISI PARCHEGGI A DESTINAZIONE ({parking.destination} - Soggiorno {parking.stay_days} gg)[/bold blue]",
        border_style="blue"
    )
    p_table.add_column("Opzione Parcheggio", style="cyan", width=25)
    p_table.add_column("Dettagli e Condizioni", style="white", width=42)
    p_table.add_column("Costo Stimato", justify="right", style="bold yellow", width=14)

    for opt in parking.options:
        badge = " [bold green](Consigliato)[/bold green]" if opt.recommended else ""
        name_str = f"{opt.name}{badge}"
        cost_str = f"{opt.estimated_cost:.2f} €"
        p_table.add_row(name_str, opt.details, cost_str)

    console.print(p_table)

    # Box raccomandazione
    rec_text = (
        f"[bold green]💡 Soluzione Consigliata:[/bold green] {parking.recommended_solution}\n"
        f"[dim]App utili da installare: {', '.join(parking.useful_apps)}[/dim]"
    )
    console.print(Panel(rec_text, border_style="green", expand=False))

def render_comparison_table(main: TripReport, alt: TripReport):
    table = Table(title="[bold yellow]⚖️ CONFRONTO: Percorso con Pedaggio vs Senza Pedaggio[/bold yellow]", border_style="yellow")
    table.add_column("Parametro", style="cyan")
    table.add_column("Con Autostrada / Pedaggio", justify="right", style="green")
    table.add_column("Senza Pedaggio", justify="right", style="magenta")
    table.add_column("Differenza", justify="right", style="bold")

    km_diff = alt.route.distance_km - main.route.distance_km
    time_diff = alt.route.duration_minutes - main.route.duration_minutes
    fuel_diff = alt.fuel.total_fuel_cost - main.fuel.total_fuel_cost
    total_diff = alt.total_trip_cost - main.total_trip_cost

    table.add_row(
        "Distanza", 
        f"{main.route.distance_km:.1f} km", 
        f"{alt.route.distance_km:.1f} km", 
        f"{'+' if km_diff >= 0 else ''}{km_diff:.1f} km"
    )
    table.add_row(
        "Tempo", 
        main.route.duration_formatted, 
        alt.route.duration_formatted, 
        f"{'+' if time_diff >= 0 else ''}{int(time_diff)} min"
    )
    table.add_row(
        "Pedaggi", 
        f"{main.toll.total_toll_cost:.2f} €", 
        f"{alt.toll.total_toll_cost:.2f} €", 
        f"-{main.toll.total_toll_cost:.2f} €"
    )
    table.add_row(
        "Carburante", 
        f"{main.fuel.total_fuel_cost:.2f} €", 
        f"{alt.fuel.total_fuel_cost:.2f} €", 
        f"{'+' if fuel_diff >= 0 else ''}{fuel_diff:.2f} €"
    )
    table.add_row(
        "Costo Totale", 
        f"{main.total_trip_cost:.2f} €", 
        f"{alt.total_trip_cost:.2f} €", 
        f"{'+' if total_diff >= 0 else ''}{total_diff:.2f} €"
    )

    console.print(table)

def run_cli():
    print_banner()
    
    if GOOGLE_MAPS_API_KEY:
        console.print("[green]✓ Google Maps API Key rilevata e attiva.[/green]")
    else:
        console.print("[dim]ℹ Nessuna Google Maps API Key specificata in .env. Utilizzo motore OpenStreetMap / OSRM e stima tariffaria AISCAT.[/dim]")

    trip_input = prompt_trip_data()

    compare = False
    if not trip_input.avoid_tolls:
        compare = Confirm.ask("\nVuoi calcolare anche il confronto con l'alternativa senza pedaggio?", default=False)

    coordinator = CoordinatorAgent()

    with console.status("[bold green]Il team di agenti sta calcolando itinerario, pedaggi, consumi e parcheggi...", spinner="dots"):
        main_report, alt_report = coordinator.process_trip(trip_input, compare_no_tolls=compare)

    console.print("\n")
    render_report_table(main_report, title="SCHEDA DETTAGLIO COSTI VIAGGIO")

    if main_report.parking:
        render_parking_table(main_report.parking)

    if alt_report:
        console.print("\n")
        render_comparison_table(main_report, alt_report)

    console.print("\n[bold green]✓ Analisi completa terminata con successo![/bold green]\n")

if __name__ == "__main__":
    run_cli()
