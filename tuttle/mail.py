import email
import smtplib
import ssl
import getpass

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def create_email(
    email_from, email_to, subject, body, email_cc=None, attachments=None
) -> MIMEMultipart:
    """Create an email message.

    Args:
        email_from (_type_): _description_
        email_to (_type_): _description_
        subject (_type_): _description_
        body (_type_): _description_
        email_cc (_type_, optional): _description_. Defaults to None.
        attachments (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = email_from
    message["To"] = email_to
    message["Subject"] = subject
    message["Cc"] = email_cc  #

    # Add body to email
    message.attach(MIMEText(body, "plain"))

    for path in attachments:
        with open(path, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)

            # Add header as key/value pair to attachment part
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {path}",
            )

            # Add attachment to message and convert message to string
            message.attach(part)

    return message


def send_email(
    message: MIMEMultipart,
    server: str,
):

    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(server, 465, context=context) as server:
        server.login(message["From"], getpass.getpass())
        server.sendmail(
            message["From"],
            message["To"],
            message.as_string(),
        )
