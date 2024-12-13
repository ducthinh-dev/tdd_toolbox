import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from mimetypes import guess_type
from email.encoders import encode_base64


class MailSender:
    def __init__(self, sender: str, password: str, host: str = "smtp-mail.outlook.com", port: int = 587) -> None:
        self.sender = sender
        self.__password = password
        self.host = host
        self.port = port
        self.__context = ssl.create_default_context()

    def __create_mime_object(self, receivers: list[str], subject: str, content: str, content_type: str,
                             cc_receivers: list[str] = [], bcc_receivers: list[str] = [],
                             attachments: str = ''):
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = self.sender
        if receivers:
            message["To"] = ",".join(receivers)
        if cc_receivers:
            message["Cc"] = ",".join(cc_receivers)
        if bcc_receivers:
            message["Bcc"] = ",".join(bcc_receivers)
        message.attach(MIMEText(content, content_type))
        if attachments:
            for filename in attachments:
                mimetype, _ = guess_type(filename)
                if not mimetype:
                    continue
                mimetype = mimetype.split('/', 1)
                fp = open(filename, 'rb')
                attachment = MIMEBase(mimetype[0], mimetype[1])
                attachment.set_payload(fp.read())
                fp.close()
                encode_base64(attachment)
                attachment.add_header('Content-Disposition', 'attachment',
                                      filename=os.path.basename(filename))
                message.attach(attachment)
        return message

    def send_email(self, subject: str, content: str, content_type: str = "plain",
                   receivers: list[str] = [], cc_receivers: list[str] = [], bcc_receivers: list[str] = [],
                   attachments: str = '') -> bool:
        message = self.__create_mime_object(
            receivers=receivers,
            cc_receivers=cc_receivers,
            bcc_receivers=bcc_receivers,
            subject=subject,
            content=content,
            content_type=content_type,
            attachments=attachments
        )
        receivers = receivers + cc_receivers + bcc_receivers
        with smtplib.SMTP(self.host, self.port) as server:
            server.ehlo()
            server.starttls(context=self.__context)
            server.ehlo()
            server.login(self.sender, self.__password)
            server.sendmail(
                self.sender, receivers, message.as_string()
            )
        return True
