# Plan: NeuroQuant Monitor

## Översikt
Automatiskt övervakningssystem somNotifierar via e-post när ny data dyker upp på NeuroQuant "NQ Värde & Momentum"-sida.

## Teknisk Stack
- **Språk**: Python 3
- **Webbskrapning**: Playwright (hanterar JavaScript)
- **E-post**: SMTP (använder ditt befintliga e-postkonto)
- **Schemaläggning**: Cron (var 5:e minut)
- **Konfiguration**: .env-fil (aldrig i git)

---

## Task 1: Spara spec-dokumentation
- [ ] Spara denna plan
- [ ] Skapa shape.md med beslut och kontext
- [ ] Skapa standards.md (om relevanta standarder finns)
- [ ] Skapa references.md (referensimplementationer)
- [ ] Skapa visuals/-mapp (om visuals finns)

## Task 2: Sätt upp projektstruktur
- [ ] Skapa Python-projekt (.gitignore, requirements.txt)
- [ ] Skapa config.py för konfiguration
- [ ] Skapa .env.example (mall för credentials)

## Task 3: Implementera inloggning & skrapning
- [ ] Implementera login-flow med Playwright
- [ ] Navigera till Modellportföljer → NQ Värde & Momentum
- [ ] Extrahera datum och aktiedata
- [ ] Spara last-known state till JSON

## Task 4: Implementera e-postnotifiering
- [ ] Konfigurera SMTP för e-post
- [ ] Skapa e-postmall med aktiedetaljer
- [ ] Testa e-postutskick

## Task 5: Implementera övervakningsloop
- [ ] Jämför ny data med last-known state
- [ ] Skicka notifiering vid nytt datum
- [ ] Uppdatera state efter lyckad notifiering

## Task 6: Konfigurera schemaläggning
- [ ] Skapa cron-jobb för var 5:e minut
- [ ] Testa hela flödet

---

## Beslut att fatta
1. **Vilken e-postleverantör?** (Gmail, Outlook, annat?)
2. **Vill du använda din vanliga Gmail eller skapa en app-specifik?** (rekommenderar app-lösenord för Gmail)
3. **Vilka detaljer ska inkluderas i e-postmeddelandet?** (aktienamn, antal, köp/sälj, etc.)

## Kända risker
- Webbplatsen kan ändra struktur → behöver underhåll
- Inloggningstoken kan gå ut → behöver hantera session-förnyelse
- Rate limiting från webbplatsen → kan behöva justera intervall
