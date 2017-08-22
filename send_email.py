import smtplib
from os.path import basename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def py_mail(subject, body, to, sender, attachments, password, cc):
    html_body = MIMEText(body, 'html')
    msg = MIMEMultipart(_subparts=(html_body))
    for a in attachments.split(','):
        try:
            attachment_path = '/srv/www/engibot/data/{}'.format(a)
            with open(attachment_path, 'rb') as pdf_file:
                pdf = MIMEApplication(pdf_file.read(), _subtype = 'pdf')
                pdf.add_header('content-disposition', 'attachment', filename=basename(attachment_path))
        except FileNotFoundError as e:
            print(e)
    msg = MIMEMultipart(_subparts=(html_body, pdf))
    msg['subject'] = subject
    msg['To'] = to
    msg['From'] = sender
    msg['CC'] = cc

    # The actual sending of the e-mail
    server = smtplib.SMTP('smtp.gmail.com:587')

    # Print debugging output when testing
    if __name__ == "__main__":
        server.set_debuglevel(1)

    server.starttls()
    server.login(sender ,password)
    server.sendmail(sender , [to], msg.as_string())
    server.quit()
