# 💶 Finanz Guru Local

Aplicație personală de finanțe similară cu Finanzguru, **100% locală**. Testată pe extrase Deutsche Bank reale (Kontoauszug PDF).

## Ce face

Parsează extrasele PDF Deutsche Bank, categorizează automat tranzacțiile (99% acuratețe pe extrase reale cu ~100 tranzacții), și oferă dashboard + trenduri + bugete.

## Pornire

```powershell
# Windows PowerShell, din folderul finanzguru-local:
.\venv\Scripts\python.exe -m streamlit run app.py

# Sau fără venv, direct:
pip install -r requirements.txt
streamlit run app.py
```

Se deschide în browser la `http://localhost:8501`.

## Features

- 📊 **Dashboard** — carduri gradient cu Einnahmen/Ausgaben/Saldo, donut chart categorii, evoluție sold, top tranzacții recente, progres bugete
- 📤 **Import PDF** — drag & drop unul sau mai multe Kontoauszug, preview înainte de salvare
- 💳 **Tranzacții** — filtre (perioadă, categorie, căutare), editor inline pentru recategorizare
- 🎯 **Bugete** — separate în "Active" vs "Alte categorii", sugestii automate pe baza mediilor ultimelor 3 luni
- 📈 **Trenduri** — Venituri vs Cheltuieli lunar (bar + linie saldo), evoluție pe categorii
- ⚙️ **Reguli custom** — keyword → categorie, prioritare față de cele implicite
- 📥 **Export** — CSV complet sau rezumat lunar

## Categorizare

22 categorii cu ~200 keyword-uri specifice extraselor reale din Chemnitz:

- **Einkommen** → salarii (Community4you, DMI Archivorg), Familienkasse, rambursări
- **Wohnen** → Mario Endrich (proprietar), Grundsteuer, Gebäudeversicherung
- **Energie** → Vattenfall, Naturwerke, Stadtwerke, Montana Erdgas
- **Lebensmittel** → Edeka, Lidl, Netto, Norma, DM, Rossmann, Mix Markt
- **Transport** → ADAC, EasyPark, STAR Chemnitz (benzinărie), CVAG
- **Versicherung** → HUK-Coburg, ADAC Autovers, Hausrat, Haftpflicht
- **Online Shopping** → PayPal, Amazon, Klarna, Otto Payments
- **Gastronomie** → McDonalds, Persepolis, Bäckerei Moebius
- **Transport familie** → Roman Liuba, Raisa, Revolut, MoneyGram (separat ca **Transfer**)
- și multe altele...

## Keyword matching inteligent

Parser-ul folosește **word boundaries** pentru keyword-uri problematice (`hem`, `rwe`, `bvg`, etc.) ca să evite false positives gen `rwe` prinzând în "übe**rwe**isung" sau `hem` în "C**hem**nitz".

Pentru keyword-uri lungi folosește substring simplu, ca să prindă chiar și cuvinte concatenate de pdfplumber (ex: "NORMASAGTDANKE" → `norma` prinde).

## Probleme cunoscute / limite

- **Doar Deutsche Bank.** Parser-ul e calibrat pe formatul exact al Kontoauszug DB (2026). Pentru alte bănci, trebuie un parser nou.
- **PDF-uri scanate (imagini)** nu funcționează — ai nevoie de OCR. Pot adăuga dacă cazul apare.
- **Merchant necunoscut** → `Sonstiges`. Adaugi regulă în secțiunea ⚙️ Reguli sau editezi manual în 💳 Tranzacții.
- **Rambursări** (Mario Endrich "Rueckerstattung Grundsteuer") ajung în Einkommen datorită keyword-ului "rueckerstattung". Dacă vrei să le urmărești separat, șterge keyword-ul din Einkommen și adaugă regulă custom "rueckerstattung grundsteuer" → Wohnen.

## Structura

```
finanzguru-local/
├── app.py              # UI Streamlit (7 pagini)
├── parser_db.py        # Parser PDF Deutsche Bank
├── categorizer.py      # Categorizare cu word-boundary matching
├── db.py               # SQLite (transactions, budgets, rules)
├── requirements.txt
├── data/finanzen.db    # Creat automat
└── uploads/            # PDF-uri temporare după import
```

## Design

- Light theme curat, tipografie Inter
- Carduri gradient pentru metrici cheie (verde venituri, roșu cheltuieli, albastru saldo pozitiv, portocaliu saldo negativ, mov tranzacții)
- Donut chart cu totalul în centru
- Progress bars colorate (verde/galben/roșu) pentru bugete
- Lista tranzacții cu sume colorate inline

## Securitate

Toate datele rămân **local** în `data/finanzen.db`. Zero requests spre internet. Adaugă `data/` în backup-ul tău (Syncthing, rsync) și **nu** pe GitHub (deja în `.gitignore`).
