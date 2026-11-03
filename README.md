# neuro

Övervakar en NeuroQuant-portfölj ("NQ Värde & Momentum") och skickar e-post
när portföljen publiceras om med materiella förändringar.

## När skickas ett mejl?

Ett mejl skickas när **två** villkor är uppfyllda:

1. NeuroQuant har publicerat en ny version av portföljen
   (`updatedAt`/datum har ändrats), och
2. minst en position ändrats mer än `MIN_CHANGE_THRESHOLD` procentenheter
   (standard 0,2).

Vikterna som visas på NeuroQuant-sajten är volatilitetsjusterade och räknas
om löpande, så en viktändring ensam räcker inte för att trigga ett mejl -
då hade varje ny publicering kunnat ge tiotals mejl.

Ändringar mäts mellan två publiceringar: state-filen uppdateras bara när
en ny publicering upptäcks, så en ändring som räknats om dagligen inte
rapporteras.

Tröskeln är strikt ("större än 0,2"), så en ändring på exakt 0,2
procentenheter filtreras bort. Nya och borttagna positioner filtreras på
samma sätt (en ny position på 0,1 % är en ändring på 0,1 procentenheter).

Om en publicering bara innehåller förändringar under tröskeln skickas inget
mejl.

## Körning

Programmet körs via cron på pxe-serven:

```
*/15 * * * * cd ~/repos/neuro && ./run.sh >> ~/repos/neuro/monitor.log 2>&1
```

Det ger 96 körningar per dygn. Programmet har dessutom ett eget skydd
(se nedan), så även om cron-frekvensen ändras finns en gräns.

## Hur datan hämtas

NeuroQuant exponerar ett tRPC-API (`app.neuroquant.ai/api/trpc`) som ger
strukturerad portföljdata - det används i stället för DOM-skrapping.
`scraper.py`:

1. Loggar in med sparade cookies (`cookies.json`) om de fortfarande gäller.
2. Annars loggas in med e-post + lösenord. Kontot kräver ett 6-siffrigt
   verifieringskode som skickas till e-post - koden hämtas automatiskt från
   inkorgen via IMAP (`EMAIL_USER` / `EMAIL_PASSWORD`).
3. Hämtar portföljlistan via API:t, väljer "NQ Värde & Momentum" på titel
   och hämtar positionerna med vikt och datum (`updatedAt`).

`portfolio_data.py` innehåller formatering och tolkning (tabellrader,
datum, verifieringskod, igenkänning av låst konto/felaktigt lösenord) och
testas utan browser.

## Skydd mot låsta konton

NeuroQuant låser ett konto efter 100 misslyckade inloggningsförsök. `run_guard.py`
skyddar mot att det händer:

| Skydd | Standard | Miljövariabel |
|---|---|---|
| Max antal körningar per dygn | 96 | `MAX_RUNS_PER_DAY` |
| Paus efter upprepade fel | 3 fel | `MAX_CONSECUTIVE_FAILURES` |
| Pausens längd vid fel | 60 min × antal fel | `FAILURE_COOLDOWN_MINUTES` |
| Pausens längd vid låst konto | 120 min | `LOCKED_COOLDOWN_MINUTES` |
| Pausens längd vid felaktigt lösenord | 1440 min | `INVALID_CREDENTIALS_COOLDOWN_MINUTES` |

Ett låst konto upptäcks på inloggningssidan (`Account locked`) och då görs
**inga** fler inloggningsförsök förrän pausen gått ut.

Om NeuroQuant avvisar lösenordet (`Lösenordet är felaktigt`) görs inga nya
inloggningsförsök på 24 timmar (`INVALID_CREDENTIALS_COOLDOWN_MINUTES`) och
ett larm mejlas till mottagarna (max en gång per dygn).

Körningsstatistik (antal körningar, fel i rad) sparas i `runs.json`
(gitignoreras).

Nollställ räkningen efter att lösenordet har fixats:

```bash
./run.sh --reset
```

## Övriga inställningar

Variablerna i `.env`:

| Variabel | Beskrivning |
|---|---|
| `NEURO_EMAIL` / `NEURO_PASSWORD` | Inloggning till NeuroQuant |
| `EMAIL_USER` / `EMAIL_PASSWORD` | Skicka och läsa e-post (SMTP + IMAP) |
| `RECIPIENT_EMAIL` | Mottagare av notifieringar (komma-separerad lista) |
| `SMTP_HOST` / `SMTP_PORT` | SMTP-server för utgående e-post |
| `IMAP_HOST` | IMAP-server för att hämta verifieringskoder |
| `MIN_CHANGE_THRESHOLD` | Minsta viktändring (procentenheter) som triggar e-post. Ändringar måste vara **större** än värdet |

## Utveckling

```bash
.venv/bin/python -m pytest tests/ -q   # tester
.venv/bin/behave                         # feature-tester
./run.sh                                 # kör en gång manuellt
```
