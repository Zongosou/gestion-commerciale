import smtplib
from email.mime.text import MIMEText


class EmailService:

    def send_reset(self, to_email, new_password):

        msg = MIMEText(
            f"Votre nouveau mot de passe temporaire est : {new_password}"
        )

        msg["Subject"] = "Réinitialisation mot de passe"
        msg["From"] = "ton_email@gmail.com"
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("ton_email@gmail.com", "mot_de_passe_app")
            server.send_message(msg)