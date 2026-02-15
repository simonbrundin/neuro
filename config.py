import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"

load_dotenv()


@dataclass
class Config:
    email_user: str = os.getenv("EMAIL_USER", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    recipient_email: str = os.getenv("RECIPIENT_EMAIL", "")
    neuro_email: str = os.getenv("NEURO_EMAIL", "")
    neuro_password: str = os.getenv("NEURO_PASSWORD", "")
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    check_interval: int = int(os.getenv("CHECK_INTERVAL", "300"))

    def get_recipient_list(self) -> list:
        if not self.recipient_email:
            return [self.email_user]
        return [
            email.strip() for email in self.recipient_email.split(",") if email.strip()
        ]


config = Config()
