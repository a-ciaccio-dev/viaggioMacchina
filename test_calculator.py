"""
Test programmatico del team di agenti per il calcolo costi viaggio.
"""
from models.trip_models import TripInput
from agents.coordinator_agent import CoordinatorAgent

def test_trip_calculation():
    print("Avvio test simulazione Milano -> Bologna...")
    trip_input = TripInput(
        origin="Milano",
        destination="Bologna",
        fuel_consumption=16.5, # 16.5 km con 1 litro
        fuel_unit="km_l",
        fuel_type="benzina",
        custom_fuel_price=1.82,
        passengers=2,
        avoid_tolls=False
    )

    coordinator = CoordinatorAgent()
    main_report, alt_report = coordinator.process_trip(trip_input, compare_no_tolls=False)

    print("\n--- RISULTATO TEST ---")
    print(f"Tratta: {main_report.origin} -> {main_report.destination}")
    print(f"Distanza: {main_report.route.distance_km:.1f} km")
    print(f"Tempo stimato: {main_report.route.duration_formatted}")
    print(f"Litri necessari: {main_report.fuel.effective_liters:.2f} L")
    print(f"Costo carburante: {main_report.fuel.total_fuel_cost:.2f} €")
    print(f"Costo pedaggi: {main_report.toll.total_toll_cost:.2f} € ({main_report.toll.notes})")
    print(f"Costo totale: {main_report.total_trip_cost:.2f} €")
    print(f"Costo a persona (2 passeggeri): {main_report.cost_per_passenger:.2f} €")

    assert main_report.route.distance_km > 150, "La distanza tra Milano e Bologna dovrebbe essere superiore a 150 km"
    assert main_report.fuel.total_fuel_cost > 0, "Il costo carburante deve essere > 0"
    assert main_report.total_trip_cost > 0, "Il costo totale deve essere > 0"
    print("\n[OK] Tutti i test di coerenza sono stati superati con successo!")

if __name__ == "__main__":
    test_trip_calculation()
