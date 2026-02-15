# Shape: NeuroQuant Monitor

## Scope
Bygga en automatiserad övervakare som kollar NeuroQuant var 5:e minut och skickar e-post när nytt datum dyker upp i "NQ Värde & Momentum"-portföljen.

## Tekniska beslut

### Varför Python + Playwright?
- **Python**: Enkelt, bra bibliotek för allt vi behöver
- **Playwright**: Modernare än Selenium, bättre dokumentation, funkar bra med Python

### Varför inte API?
- NeuroQuant verkar inte ha offentligt API
- Webbplatsen är JavaScript-renderad → behöver headless browser

### Credential-hantering
- .env-fil med EMAIL_USER, EMAIL_PASSWORD, NEURO_USER, NEURO_PASSWORD
- .gitignore exkluderar .env
- .env.example visar mall utan känslig data

## Data att hämta
Från sidan behöver vi:
1. **Datum** - för att detektera ny information
2. **Tabell data** - aktier att köpa/sälja med:
   - Aktienamn
   - Antal/andel
   - Köp/Sälj-indikation

## E-postinnehåll
```
Subject: NeuroQuant: Ny portföljuppdatering [2026-01-28]

Hej!

Ny portföljdata har publicerats för NQ Värde & Momentum.

📅 Datum: 2026-01-28

📈 Köpa:
- ABB Ltd: 150 st
- Atlas Copco: 80 st
...

📉 Sälja:
- SEB: 100 st
...

🔗 Länk: https://app.neuroquant.ai/modellportfoljer
```

## Kompromisser
- Ingen direkt orderläggning (för riskfyllt utan manuell granskning)
- Ingen push-notis till mobil (kräver extra setup)
- Ingen GUI-konfiguration (env-filer är enklare)

## Externa beroenden
- python-dotenv
- playwright
- aiosmtplib (async) eller smtplib
