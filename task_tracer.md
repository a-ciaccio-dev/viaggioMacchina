# Task Tracer — PercorsoAuto Overpass/OSRM Fallback (`feature/overpass-osm-fallback`)

Questo file traccia in tempo reale lo stato di avanzamento dei Task e Sotto-Task previsti dal Piano di Implementazione sul branch `feature/overpass-osm-fallback`.
Le attività sono ordinate per dipendenze in modo da evitare conflitti tra le esecuzioni ed eliminare ripetizioni.
Al termine di ogni singolo task/sottotask: **Test -> Aggiornamento Task Tracer -> Commit & Push**.

---

## 📊 Riepilogo Avanzamento

**Progresso Globale:** `5 / 6` step operativi completati (**83%**)

```text
[█████████████████░░░] 83% (5/6 Task & Sotto-Task)
```

- **Branch attivo**: `feature/overpass-osm-fallback`
- **Fasi totali**: `4`
- **Step operativi totali**: `6` (`5` completati, `1` rimanenti)
- **Stato attuale**: 🟡 In corso (Task 4)

---

## 🏷️ Legenda

- **Difficoltà**: `🟢 Bassa` | `🟡 Media` | `🔴 Alta (scomposta in sottotask)`
- **Stato**: `⏳ Da fare` | `🔄 In corso` | `✅ Completato` | `❌ Bloccato`

---

## 📋 Tabella di Tracciamento Dettagliata

| Fase | ID | Task / Sotto-Task | Difficoltà | Stato | Test Verificati | Commit Hash | Data/Ora Completamento |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Init** | **Init** | Creazione e push branch `feature/overpass-osm-fallback` + `task_tracer.md` | 🟢 Bassa | ✅ Completato | `11/11 passed` | `init` | 2026-11-13 11:58 |
| **1. Fondamenta** | **Task 1** | `RouteAgent` OSRM: supporto `waypoints`, `overview=full&geometries=polyline` ed esposizione `polyline.encodedPolyline` | 🟡 Media | ✅ Completato | `11/11 passed` | `task-1` | 2026-11-13 11:59 |
| **2. Sviluppo** | **Task 2.1** | `PlacesAgent`: decoder polyline5, campionamento punti Haversine e client Overpass API | 🟡 Media | ✅ Completato | `11/11 passed` | `task-2.1` | 2026-11-13 12:01 |
| **2. Sviluppo** | **Task 2.2** | `PlacesAgent`: fallback automatico Overpass/Nominatim senza API key e normalizzazione output | 🟡 Media | ✅ Completato | `11/11 passed` | `task-2.2` | 2026-11-13 12:02 |
| **3. Verifica** | **Task 3** | Test unitari con mock HTTP per OSRM polyline/waypoints e Overpass fallback (`test_places_agent.py`) | 🟡 Media | ✅ Completato | `16/16 passed` | `task-3` | 2026-11-13 12:04 |
| **4. E2E & Chiusura** | **Task 4** | Verifica reale su tratta Montreuil -> Metz (TotalEnergies su A4) e chiusura `task_tracer.md` | 🟢 Bassa | ⏳ Da fare | `—` | `—` | `—` |

---

## 📝 Log Note & Eventuali Blocchi

> Annotare qui eventuali errori bloccanti incontrati durante l'esecuzione, decisioni architetturali prese in corso d'opera o modifiche all'ordine dei task.

- *Inizializzazione branch dedicato `feature/overpass-osm-fallback` con baseline Google Places/Routes già presente.*
