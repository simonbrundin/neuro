# References: NeuroQuant Monitor

## Liknande projekt

### Webbskrapning med Playwright + Python
- Officiell Playwright-dokumentation: https://playwright.dev/python/
- Exempel på login-flöden: https://playwright.dev/python/docs/auth

### E-post i Python
- smtplib standardbiblioteket
- python-dotenv för .env-hantering

### Schemaläggning
- Cron (systemets standard)
- Eller schedule-biblioteket: https://schedule.readthedocs.io/

## Arkitekturmönster
- State-baserad detektering (spara last-known till JSON)
- Idempotent körning (samma resultat om körs flera gånger)

## Debugging
- Spara screenshots vid fel
- Logga alla försök
- Behåll cookies mellan sessioner
