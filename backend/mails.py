import base64
import os
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

subject = f"""
          Saksham Bansal | Resume
          """

class _send:

    def __init__(self, email, metadata = None):
        self.email = email
        self.name = metadata[-1]['name'] if metadata else None
        self.subject = subject
        self.pdf_path = "data/Saksham_Bansal.pdf"
        self.metadata = metadata
        self.phone = metadata[-1]['phone'] if metadata else None
    
    def _get_mail_body(self):
        name = self.name
        name = f"Dear {name}," if name else "Dear,"
        body = f"""
        {name}

        Thank you so much for connecting me over chat,
        Please refer to the attached Resume for your reference..

        Thanks & Regards,
        Saksham Bansal
        +91-9990955372
        """
        return body


    def notify_via_ntfy(self):
        url = os.getenv("NTFY_URL")
        email = self.email
        name = self.name
        unanswered_questions = "\n".join([i['unanswered_questions'] for i in self.metadata if i['unanswered_questions']])
        phone = self.phone
        message = (
            f"📢 Resume Agent Alert Email sent to {name}\n"
            f"Email: {email}\n"
            f"Name: {name}\n"
            f"Phone: {phone}\n"
            f"Unaswered Questions: {unanswered_questions}"
            )

        try:
            requests.post(url, data=message.encode("utf-8"), timeout=5)
            print("✅ NTFY alert sent successfully.")
        except Exception as e:
            print("⚠️ Notification failed:", e)


    # def send_email(self, to_name:str):
    #     """ Send out an email with the given body to all sales prospects via Gmail SMTP """
        
    #     # Set up email sender, recipient, and content
    #     from_email = os.getenv("GMAIL_USER")  # Replace with your Gmail address or set as env var
    #     to_email = to_name     # Replace with recipient or set as env var
    #     gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")  # Use your Gmail app password or set as env var
    #     subject = self.subject
        
    #     if not from_email or not to_email or not gmail_app_password:
    #         return {"status": "failure", "message": "Missing environment variables in .env file."}
    #     else:
    #         print(f"from - {from_email}; to - {to_email}")
        
    #     metadata = self.metadata
    #     log_mails = [e.keys() for e in metadata]
        
    #     if to_email in log_mails:
    #         print(f"⚠️ Email with subject '{subject}' already sent to {to_email}. Skipping...")
    #         return {"status": "skipped", "message": f"Already sent to {to_email} for this subject."}


    #     # Create the email
    #     msg = MIMEMultipart("alternative")
    #     msg['Subject'] = subject
    #     msg['From'] = "Saksham Bansal"
    #     msg['To'] = to_email

    #     body = self._get_mail_body()

    #     html_part = MIMEText(body)
    #     msg.attach(html_part)
        
    #     if self.pdf_path and os.path.exists(self.pdf_path):
    #         try:
    #             with open(self.pdf_path, "rb") as f:
    #                 part = MIMEBase("application", "octet-stream")
    #                 part.set_payload(f.read())
    #             encoders.encode_base64(part)
    #             part.add_header(
    #                 "Content-Disposition",
    #                 f'attachment; filename="{os.path.basename(self.pdf_path)}"',
    #             )
    #             msg.attach(part)
    #             print(f"📎 Attached PDF: {self.pdf_path}")
    #         except Exception as e:
    #             print(f"⚠️ Could not attach PDF: {e}")
    #     elif self.pdf_path:
    #         print(f"⚠️ PDF not found at path: {self.pdf_path}")
            

    #     try:
    #         with smtplib.SMTP('smtp.gmail.com', 587) as server:
    #             server.starttls()  # Secure the connection
    #             server.login(from_email, gmail_app_password)
    #             server.send_message(msg)

    #         return {"status": "success"}
    #     except Exception as e:
    #         return {"status": "failure", "message": str(e)}

    # def send_email(self, to_name: str):
    #     """Send email using Gmail API (OAuth) — works in Lambda"""

    #     from_email = os.getenv("GMAIL_USER")
    #     to_email = to_name

    #     client_id = os.getenv("GMAIL_CLIENT_ID")
    #     client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    #     refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")

    #     if not (from_email and to_email and client_id and client_secret and refresh_token):
    #         return {"status": "failure", "message": "Missing Gmail API environment variables."}

    #     # Create OAuth credentials
    #     creds = Credentials(
    #         None,
    #         refresh_token=refresh_token,
    #         token_uri="https://oauth2.googleapis.com/token",
    #         client_id=client_id,
    #         client_secret=client_secret,
    #         scopes=["https://www.googleapis.com/auth/gmail.send"]
    #     )

    #     # Auto-refresh the access token
    #     creds.refresh(Request())

    #     # Build Gmail API client
    #     service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)

    #     # Create email message
    #     msg = MIMEMultipart("alternative")
    #     msg["Subject"] = self.subject
    #     msg["From"] = from_email
    #     msg["To"] = to_email

    #     body = self._get_mail_body()
    #     html_part = MIMEText(body)
    #     msg.attach(html_part)

    #     # Attach PDF if exists
    #     if self.pdf_path and os.path.exists(self.pdf_path):
    #         try:
    #             with open(self.pdf_path, "rb") as f:
    #                 part = MIMEBase("application", "octet-stream")
    #                 part.set_payload(f.read())
    #             encoders.encode_base64(part)
    #             part.add_header(
    #                 "Content-Disposition",
    #                 f'attachment; filename="{os.path.basename(self.pdf_path)}"'
    #             )
    #             msg.attach(part)
    #         except Exception as e:
    #             print(f"PDF attachment failed: {e}")

    #     # Gmail requires base64 encoded message
    #     raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    #     try:
    #         sent = service.users().messages().send(
    #             userId="me",
    #             body={"raw": raw_message}
    #         ).execute()

    #         return {"status": "success", "message_id": sent.get("id")}

    #     except Exception as e:
    #         return {"status": "failure", "message": str(e)}



