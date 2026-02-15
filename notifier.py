import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import config


def send_notification(portfolio_data: dict, changes: dict = None) -> bool:
    if not portfolio_data:
        return False

    date = portfolio_data.get("date", "Okänt datum")

    if changes is None:
        changes = {"increased": [], "decreased": [], "added": [], "removed": []}

    increased = changes.get("increased", [])
    decreased = changes.get("decreased", [])
    added = changes.get("added", [])
    removed = changes.get("removed", [])

    body = f"""Hej!

Ny portföljdata har publicerats för NQ Värde & Momentum.

📅 Datum: {date}

📈 Öka vikt:"""

    if not increased:
        body += "\nInga förändringar"
    else:
        for stock in increased:
            body += (
                f"\n- {stock['name']}: {stock['old_weight']} → {stock['new_weight']}"
            )

    body += f"\n\n📉 Minska vikt:"

    if not decreased:
        body += "\nInga förändringar"
    else:
        for stock in decreased:
            body += (
                f"\n- {stock['name']}: {stock['old_weight']} → {stock['new_weight']}"
            )

    body += f"\n\n➕ Nya bolag:"

    if not added:
        body += "\nInga"
    else:
        for stock in added:
            body += f"\n- {stock['name']} ({stock['new_weight']})"

    body += f"\n\n➖ Borttagna bolag:"

    if not removed:
        body += "\nInga"
    else:
        for stock in removed:
            body += f"\n- {stock}"

    body += """

🔗 Länk: https://app.neuroquant.ai/portfolios

---
Skickat från NeuroQuant Monitor
"""

    subject = f"NeuroQuant: Ny portföljuppdatering {date}"

    return send_email(subject, body)


def send_email(subject: str, body: str) -> bool:
    try:
        recipients = config.get_recipient_list()

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls()
            server.login(config.email_user, config.email_password)

            for recipient in recipients:
                msg = MIMEMultipart()
                msg["From"] = config.email_user
                msg["To"] = recipient
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain", "utf-8"))
                server.send_message(msg)

        print(f"Email sent successfully to {recipients}")
        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


if __name__ == "__main__":
    test_data = {
        "date": "2026-01-28",
        "data": [
            ["ABB Ltd", "Köp", "150", "285.50"],
            ["Atlas Copco", "Köp", "80", "142.30"],
            ["SEB", "Sälj", "100", "125.00"],
        ],
        "timestamp": "2026-01-28T10:00:00",
    }
    send_notification(test_data)
