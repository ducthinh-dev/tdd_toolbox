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
                             attachments: str = '', embedded_images: dict = {}):
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

        # Handle attachments
        if attachments:
            for filename in attachments:
                mimetype, _ = guess_type(filename)
                if not mimetype:
                    continue
                mimetype = mimetype.split('/', 1)
                with open(filename, 'rb') as fp:
                    attachment = MIMEBase(mimetype[0], mimetype[1])
                    attachment.set_payload(fp.read())
                encode_base64(attachment)
                attachment.add_header('Content-Disposition', 'attachment',
                                      filename=os.path.basename(filename))
                message.attach(attachment)

        # Handle embedded images
        for cid, img_path in embedded_images.items():
            mimetype, _ = guess_type(img_path)
            if not mimetype:
                continue
            mimetype = mimetype.split('/', 1)
            with open(img_path, 'rb') as fp:
                img = MIMEBase(mimetype[0], mimetype[1])
                img.set_payload(fp.read())
            encode_base64(img)
            img.add_header('Content-ID', f'<{cid}>')
            img.add_header('Content-Disposition', 'inline',
                           filename=os.path.basename(img_path))
            message.attach(img)

        return message

    def send_email(self, subject: str, content: str, content_type: str = "plain",
                   receivers: list[str] = [], cc_receivers: list[str] = [], bcc_receivers: list[str] = [],
                   attachments: str = '', embedded_images: dict = {}) -> bool:
        message = self.__create_mime_object(
            receivers=receivers,
            cc_receivers=cc_receivers,
            bcc_receivers=bcc_receivers,
            subject=subject,
            content=content,
            content_type=content_type,
            attachments=attachments,
            embedded_images=embedded_images
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


def get_recipients(conn, code):
    query_recipient = '''
        select recipient_mail, receive_type  
        from MailRecipients
        where mail_code in ('*', '{job_code}');
    '''
    
    _, data = conn.query_data(query=query_recipient.format(
        job_code=code
    ))
    list_to = []
    list_cc = []
    list_bcc = []
    for email, rec_type in data:
        match rec_type:
            case 0:
                list_to.append(email)
            case 1:
                list_cc.append(email)
            case 2:
                list_bcc.append(email)
            case _:
                list_bcc.append(email)
    return {
        'to': list_to,
        'cc': list_cc,
        'bcc': list_bcc
    }
