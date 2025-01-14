# This file is an expansion of the previous code I have completed, that uses the same kind of retrieval and processing framework for sentiment analysis.
# This project is structured to utilize newsletters and casual sources of information frequented by investment bankers and to quantify the sentiments these sources of information express about particular companies.
# The backend is set up, similarly to the main project, to extract emails, extract from them numerical sentiment ratings, and then to put them into a database.
# The next step from this project would be to sort and analyze the sentiment data, and to employ database maintenance techniques to accomplish this goal.

import os
from datetime import datetime
from flask import Flask, request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import json
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Optional
from ratelimit import limits, sleep_and_retry
import google.generativeai as genai

# Flask app setup
app = Flask(__name__)

db_path = "financial_sentiments.db"

# Database initialization
def initialize_db():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_sentiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                company_name TEXT,
                sentiment_score REAL,
                date TEXT,
                source TEXT
            )
        """)
        conn.commit()

initialize_db()

# Gmail API client
@dataclass
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    date: datetime
    body: str

class GmailAPIClient:
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

    def __init__(self):
        self.credentials = None
        self.service = None

    def authenticate(self):
        try:
            if os.path.exists("token.json"):
                self.credentials = Credentials.from_authorized_user_file("token.json", self.SCOPES)

            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", self.SCOPES)
                    self.credentials = flow.run_local_server(port=9500)

                with open("token.json", "w") as token_file:
                    token_file.write(self.credentials.to_json())

            self.service = build("gmail", "v1", credentials=self.credentials)

        except Exception as e:
            raise Exception(f"Failed to authenticate Gmail API: {str(e)}")

    def fetch_emails(self, query: str = 'label:inbox is:unread', max_results: int = 10) -> List[EmailMessage]:
        try:
            response = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()

            emails = []
            if 'messages' in response:
                for message in response['messages']:
                    email = self._get_email_details(message['id'])
                    if email:
                        emails.append(email)

            return emails
        except Exception as e:
            raise Exception(f"Error fetching emails: {str(e)}")

    def _get_email_details(self, message_id: str) -> Optional[EmailMessage]:
        try:
            message = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
            headers = message['payload']['headers']

            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            date = datetime.strptime(date_str.split(' +')[0], '%a, %d %b %Y %H:%M:%S')

            body = self._extract_body(message['payload'])
            return EmailMessage(message_id, subject, sender, date, body)
        except Exception as e:
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
        except Exception:
            return "Error decoding body."

# Gemini API client
class GeminiExtractor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    @sleep_and_retry
    @limits(calls=50, period=60)
    def extract_sentiment(self, email_body: str) -> List[Dict]:
        query = (
            "Analyze the email content for mentions of companies or commodities. "
            "For each mention, return a JSON object with fields: "
            "'Ticker', 'CompanyName', 'SentimentScore (1-10)', 'Date', and 'Source'."
        )
        try:
            response = self.model.generate_content(f"{query}\n\n{email_body}").text
            return json.loads(response.strip())
        except Exception:
            return []

# Integration function
@app.route("/update", methods=["POST"])
def update_financial_sentiments():
    gmail_client = GmailAPIClient()
    gmail_client.authenticate()

    gemini_extractor = GeminiExtractor(api_key=os.getenv("GEMINI_API_KEY"))

    emails = gmail_client.fetch_emails()
    sentiments = []

    for email in emails:
        extracted = gemini_extractor.extract_sentiment(email.body)
        sentiments.extend(extracted)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        for sentiment in sentiments:
            cursor.execute("""
                INSERT INTO financial_sentiments (ticker, company_name, sentiment_score, date, source)
                VALUES (?, ?, ?, ?, ?)
            """, (
                sentiment.get('Ticker'),
                sentiment.get('CompanyName'),
                sentiment.get('SentimentScore'),
                email.date.strftime('%Y-%m-%d'),
                email.sender
            ))
        conn.commit()

    return "Financial sentiments updated successfully.", 200

if __name__ == "__main__":
    app.run(debug=True)
