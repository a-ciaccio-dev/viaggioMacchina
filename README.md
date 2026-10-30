# 🚗 Trip Cost Calculator - Multi-Agent System

Un team di agenti intelligenti in Python progettato per calcolare il percorso migliore, i costi del carburante e i pedaggi autostradali per qualsiasi viaggio in macchina.

---

## 👥 Architettura del Team di Agenti

1. **`RouteAgent`**:
   - Calcola il percorso ottimale, distanza e tempi di percorrenza.
   - Supporta **Google Maps Routes API v2** (`computeRoutes`) per dati ufficiali e in tempo reale.
   - Include un motore di fallback automatico su **OpenStreetMap (OSRM + Nominatim)**, permettendo al sistema di funzionare anche senza una chiave API configurata.
2. **`TollAgent`**:
   - Estrae i pedaggi esatti da Google Maps Routes API oppure calcola la tariffa chilometrica autostradale italiana (media AISCAT: ~0.082 €/km sulle tratte autostradali effettive).
3. **`FuelAgent`**:
   - Converte i consumi sia in **km/l** che in **l/100km**.
   - Supporta diversi tipi di carburante: benzina, diesel, GPL, metano ed elettrico.
   - Permette di inserire un prezzo personalizzato al litro o applica i prezzi medi aggiornati.
4. **`CoordinatorAgent`**:
   - Supervisiona il flusso, sintetizza le informazioni, calcola il costo complessivo e la ripartizione per passeggero.
   - Fornisce una tabella di confronto opzionale tra il percorso con pedaggio e quello senza pedaggio.

---

## 🛠️ Requisiti e Installazione

Il progetto include già l'ambiente virtuale configurato in `.venv`.

Se desideri riattivarlo o reinstallare le dipendenze:
```powershell
# Attivazione dell'ambiente virtuale su Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Installazione dei requisiti
pip install -r requirements.txt
```

---

## 🔑 Configurazione Google Maps (Opzionale)

Se possiedi una Google Maps API Key con abilitata la **Routes API**:
1. Apri il file `.env`
2. Inserisci la tua chiave:
   ```env
   GOOGLE_MAPS_API_KEY=la_tua_api_key_qui
   ```
*Nota: se lasci il campo vuoto, il sistema utilizzerà automaticamente il motore OpenStreetMap/OSRM con stima autostradale AISCAT.*

---

## 🚀 Utilizzo

### Modalità Interattiva (CLI)
Avvia la riga di comando interattiva con interfaccia formattata Rich:
```powershell
.\.venv\Scripts\python.exe main.py
```
Ti verranno richiesti:
- Città/Indirizzo di partenza e arrivo
- Consumo medio (es. `16.5` km/l o `6.0` l/100km)
- Tipo di alimentazione
- Prezzo carburante al litro/kWh (facoltativo)
- Numero di passeggeri
- Eventuale confronto con il percorso senza pedaggi

### Esecuzione del Test Programmatico
```powershell
.\.venv\Scripts\python.exe test_calculator.py
```

### 📄 Conversione Report Markdown in PDF
Per convertire qualsiasi report di viaggio `.md` in un PDF professionale formattato:
```powershell
.\.venv\Scripts\python.exe md_to_pdf.py percorsi/Tolmezzo_Montreuil/report_viaggio.md percorsi/Tolmezzo_Montreuil/report_viaggio.pdf
```
*(Se lanciato senza argomenti, converte di default il report di Tolmezzo-Montreuil).*

