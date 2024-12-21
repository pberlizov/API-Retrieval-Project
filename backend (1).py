# Updated email-to-website integration code

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import base64
import json
from pathlib import Path
from dataclasses import dataclass
from flask import Flask, render_template, request
from cs50 import SQL
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai
from ratelimit import limits, sleep_and_retry
import threading

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s",
                    handlers=[
                        logging.FileHandler("app.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
db = SQL("sqlite:///events.db")

# Gmail API client
@dataclass
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    date: datetime
    body: str
    labels: List[str]

class GmailAPIClient:
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

    def __init__(self):
        self.credentials = None
        self.service = None

    def authenticate(self):
        """
        Authenticates the Gmail API using credentials stored in token.json or initiates a login flow.
        IMPORTANT: Do not run this function on GitHub. Export the code to VSCode to run the local server.
        """
        try:
            # Check for existing credentials
            if os.path.exists("token.json"):
                self.credentials = Credentials.from_authorized_user_file("token.json", self.SCOPES)

            # If no valid credentials, initiate the login flow
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", self.SCOPES)
                    self.credentials = flow.run_local_server(port=9500)

                # Save the credentials for future use
                with open("token.json", "w") as token_file:
                    token_file.write(self.credentials.to_json())

            # Build the Gmail API service
            self.service = build("gmail", "v1", credentials=self.credentials)
            logger.info("Gmail API authenticated successfully.")

        except Exception as e:
            logger.error(f"Failed to authenticate Gmail API: {str(e)}")
            raise

    def fetch_emails(self, query: str = 'label:inbox is:unread', max_results: int = 10) -> List[EmailMessage]:
        try:
            response = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()

            emails = []
            if 'messages' in response:
                for message in response['messages']:
                    email = self._get_email_details(message['id'])
                    if email:
                        emails.append(email)

            logger.info(f"Fetched {len(emails)} emails.")
            return emails
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []

    def _get_email_details(self, message_id: str) -> Optional[EmailMessage]:
        try:
            message = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
            headers = message['payload']['headers']

            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            date = datetime.strptime(date_str.split(' +')[0], '%a, %d %b %Y %H:%M:%S')

            body = self._extract_body(message['payload'])
            return EmailMessage(message_id, subject, sender, date, body, message.get('labelIds', []))
        except Exception as e:
            logger.error(f"Error fetching email details: {str(e)}")
            return None

    def _extract_body(self, payload: Dict) -> str:
        try:
            if 'body' in payload and payload['body'].get('data'):
                return base64.urlsafe_b64decode(payload['body']['data']).decode()

            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode()
            return "No body content."
        except Exception as e:
            logger.error(f"Error extracting email body: {str(e)}")
            return "Error decoding body."

# Gemini API client
class GeminiExtractor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    @sleep_and_retry
    @limits(calls=50, period=60)
    def extract_events(self, email_body: str) -> List[Dict]:
        query = (
            "Extract events from the email content. Return as JSON with fields: Date, Name, Time, Location, Description, Price."
        )
        try:
            response = self.model.generate_content(f"{query}\n\n{email_body}").text
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Error extracting events: {str(e)}")
            return []

# Integration function
@app.route("/update", methods=["POST"])
def update_events_backend():
    gmail_client = GmailAPIClient()
    gmail_client.authenticate()

    gemini_extractor = GeminiExtractor(api_key=os.getenv("GEMINI_API_KEY"))

    emails = gmail_client.fetch_emails()
    events = []

    for email in emails:
        extracted = gemini_extractor.extract_events(email.body)
        events.extend(extracted)

    for event in events:
        db.execute("""
            INSERT INTO events (date, name, time, location, description, price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, event.get('Date'), event.get('Name'), event.get('Time'), event.get('Location'), event.get('Description'), event.get('Price'))

    return "Events updated successfully.", 200

# Flask routes
@app.route("/")
def homepage():
    today = datetime.now().strftime('%Y-%m-%d')
    events = db.execute("SELECT * FROM events WHERE date >= ? ORDER BY date, time", today)
    return render_template("homepage.html", events=events)

if __name__ == "__main__":
    app.run(debug=True)
