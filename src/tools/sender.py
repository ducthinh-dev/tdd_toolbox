import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class MailSender:
    def __init__(self, sender: str, password: str, host: str = "smtp-mail.outlook.com", port: int = 587) -> None:
        self.sender = sender
        self.__password = password
        self.host = host
        self.port = port
        self.__context = ssl.create_default_context()

    def __create_mime_object(self, receivers: str, subject: str, content: str, content_type: str,
                             cc_receivers: list[str] = [], bcc_receivers: list[str] = []):
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = self.sender
        message["To"] = ",".join(receivers)
        if cc_receivers:
            message["Cc"] = ",".join(cc_receivers)
        if bcc_receivers:
            message["Bcc"] = ",".join(bcc_receivers)
        message.attach(MIMEText(content, content_type))
        return message

    def send_email(self, receivers: list[str], subject: str, content: str, content_type: str = "plain",
                   cc_receivers: list[str] = [], bcc_receivers: list[str] = []) -> bool:
        message = self.__create_mime_object(
            receivers=receivers,
            cc_receivers=cc_receivers,
            bcc_receivers=bcc_receivers,
            subject=subject,
            content=content,
            content_type=content_type
        )
        with smtplib.SMTP(self.host, self.port) as server:
            server.ehlo()
            server.starttls(context=self.__context)
            server.ehlo()
            server.login(self.sender, self.__password)
            server.sendmail(
                self.sender, receivers, message.as_string()
            )
        return True
