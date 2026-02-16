# Python Project Structure

## Flat Module Structure

Use a flat directory structure for small projects (<15 files). Skip `__init__.py` files.

```python
# Root directory
config.py
monitor.py
scraper.py
notifier.py
```

**Why**: Reduces boilerplate for small projects. Add `__init__.py` only if the project grows beyond ~15 modules or needs proper package testing.

## BASE_DIR Pattern

Define `BASE_DIR` at the top of each module that needs file-relative paths:

```python
from pathlib import Path

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"
```

**Why**: Ensures paths work regardless of where the script is run from (cron, IDE, CLI).

## Global Config Singleton

Define config as a module-level singleton:

```python
# config.py
@dataclass
class Config:
    email_user: str = os.getenv("EMAIL_USER", "")
    # ...

config = Config()
```

```python
# other modules
from config import config
```

**Why**: Single source of truth. Avoids passing config through every function.

## Dataclass Config with Environment Variables

Use `@dataclass` with `os.getenv` defaults:

```python
@dataclass
class Config:
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
```

**Why**: Type-safe, self-documenting, easy to add new settings.

## load_dotenv at Import Time

Call `load_dotenv()` at module level in config.py:

```python
# config.py
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # ...
```

**Why**: Config is available immediately on import. No need to call initialization in `main()`.

**Caution**: Ensure `.env` exists or has all required keys, or provide sensible defaults.
