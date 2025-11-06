"""
Email utilities for sending magic links
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import get_settings

settings = get_settings()


async def send_magic_link_email(email: str, token: str) -> bool:
    """
    Send magic link email

    Args:
        email: Recipient email
        token: Magic link token

    Returns:
        True if sent successfully
    """
    magic_link = f"{settings.FRONTEND_URL}/login?token={token}"

    # Create HTML message
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🗺️ Geo-Engineering Platform</h1>
            </div>
            <div class="content">
                <h2>Login zu Ihrem Account</h2>
                <p>Hallo!</p>
                <p>Klicken Sie auf den Button unten, um sich anzumelden:</p>
                <center>
                    <a href="{magic_link}" class="button">Jetzt anmelden</a>
                </center>
                <p>Oder kopieren Sie diesen Link in Ihren Browser:</p>
                <p style="word-break: break-all; background: white; padding: 10px; border-radius: 5px;">
                    {magic_link}
                </p>
                <p><strong>Dieser Link ist {settings.MAGIC_LINK_EXPIRATION_MINUTES} Minuten gültig.</strong></p>
                <p>Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese Email.</p>
            </div>
            <div class="footer">
                <p>Geo-Engineering Platform © 2025</p>
                <p>Powered by hoehendaten.de</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Create plain text fallback
    text_content = f"""
    Geo-Engineering Platform - Login

    Hallo!

    Klicken Sie auf diesen Link, um sich anzumelden:
    {magic_link}

    Dieser Link ist {settings.MAGIC_LINK_EXPIRATION_MINUTES} Minuten gültig.

    Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese Email.

    ---
    Geo-Engineering Platform © 2025
    """

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Ihr Login-Link für Geo-Engineering Platform"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email

    # Attach parts
    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    message.attach(part1)
    message.attach(part2)

    try:
        # Send email
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
