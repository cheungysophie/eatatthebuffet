import smtplib, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
try:
    from . import secrets
except ImportError:
    import secrets

def send_email(ticker, user_email, message):
    s = smtplib.SMTP(host=secrets.server, port=secrets.port)
    s.starttls()
    s.login(secrets.admin_email, secrets.admin_password)
    msg = MIMEMultipart()
    msg['To'] = user_email
    msg['From'] = secrets.admin_email
    msg['Subject'] = f'{ticker} is on sale!'
    msg.attach(MIMEText(message, 'html'))
    s.send_message(msg)
    print('notice sent')
    del msg