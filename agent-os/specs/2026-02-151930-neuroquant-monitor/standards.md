# Standards: NeuroQuant Monitor

## Tillämpliga standarder

### Säkerhet
- **Credentials aldrig i kod** → använd .env
- **Credentials aldrig i git** → .gitignore
- **Minsta behörighetsprincip** → endast läsrättigheter på webbplatsen

### Kodstil
- PEP 8 för Python
- Typ-hinting där möjligt
- Docstrings för funktioner

### Felhantering
- Logga fel, fortsätt kör
- Spara state även vid fel
- Retry-logik vid tillfälliga fel

### Privatsfär
- Ingen extern datalagraring
- E-post endast till användarens egen adress
