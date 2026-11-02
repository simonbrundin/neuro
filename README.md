# neuro

Övervakar en NeuroQuant-portfölj ("NQ Värde & Momentum") och skickar e-post
när portföljen ändras.

## Körning

Programmet körs via cron på pxe-serven:

```
*/15 * * * * cd ~/repos/neuro && ./run.sh >> ~/repos/neuro/monitor.log 2>&1
```

Det ger 96 körningar per dygn. Programmet har dessutom ett eget skydd
(se nedan), så även om cron-frekvensen ändras finns en gräns.

## Skydd mot låsta konton

NeuroQuant låser ett konto efter 100 misslyckade inloggningsförsök. `run_guard.py`
skyddar mot att det händer:

| Skydd | Standard | Miljövariabel |
|---|---|---|
| Max antal körningar per dygn | 96 | `MAX_RUNS_PER_DAY` |
| Paus efter upprepade fel | 3 fel | `MAX_CONSECUTIVE_FAILURES` |
| Pausens längd vid fel | 60 min | `FAILURE_COOLDOWN_MINUTES` |
| Pausens längd vid låst konto | 120 min | `LOCKED_COOLDOWN_MINUTES` |
| Pausens längd vid felaktigt lösenord | 1440 min | `INVALID_CREDENTIALS_COOLDOWN_MINUTES` |

Ett låst konto upptäcks på inloggningssidan (`Account locked`) och då görs
**inga** fler inloggningsförsök förrän pausen gått ut.

Om NeuroQuant avvisar lösenordet (`Lösenordet är felaktigt`) görs inga nya
inloggningsförsök på 24 timmar (`INVALID_CREDENTIALS_COOLDOWN_MINUTES`) och
ett larm mejlas till mottagarna.

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
| `RECIPIENT_EMAIL` | Mottagare av notifieringar (komma-separerad lista) |
| `SMTP_HOST` / `SMTP_PORT` | SMTP-server för utgående e-post |
| `MIN_CHANGE_THRESHOLD` | Minsta viktändring (procentenheter) som triggar e-post |

## Utveckling

```bash
.venv/bin/python -m pytest tests/ -q   # tester
./run.sh                                # kör en gång manuellt
```
