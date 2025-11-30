from dotenv import load_dotenv
import os
import requests

load_dotenv()

BASE_URL = os.getenv("EMAIL_SERVER_API_URL")

def list_all_emails():
    """Fetches all emails from the email server API."""
    response = requests.get(f"{BASE_URL}/emails/")
    response.raise_for_status()
    return response.json()

def list_unread_emails():
    """Fetches unread emails from the email server API."""
    response = requests.get(f"{BASE_URL}/emails/unread/")
    response.raise_for_status()
    return response.json()

def search_emails(query: str):
    """Searches emails based on a query string."""
    response = requests.get(f"{BASE_URL}/emails/search/", params={"query": query})
    response.raise_for_status()
    return response.json()

def filter_emails(recipient: str = None, date_from: str = None, date_to: str = None):
    """Filters emails based on recipient and date range."""
    params = {}
    if recipient:
        params["recipient"] = recipient
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    response = requests.get(f"{BASE_URL}/emails/filter/", params=params)
    response.raise_for_status()
    return response.json()

def get_email(email_id: int):
    """Fetches details of a specific email by ID."""
    response = requests.get(f"{BASE_URL}/emails/{email_id}/")
    response.raise_for_status()
    return response.json()

def mark_email_as_read(email_id: int):
    """Marks a specific email as read."""
    response = requests.patch(f"{BASE_URL}/emails/{email_id}/read/")
    response.raise_for_status()
    return response.json()

def mark_email_as_unread(email_id: int):
    """Marks a specific email as unread."""
    response = requests.patch(f"{BASE_URL}/emails/{email_id}/unread/")
    response.raise_for_status()
    return response.json()

def send_email(recipient: str, subject: str, body: str):
    """Sends a new email."""
    payload = {
        "recipient": recipient,
        "subject": subject,
        "body": body
    }
    response = requests.post(f"{BASE_URL}/send/", json=payload)
    response.raise_for_status()
    return response.json()

def delete_email(email_id: int):
    """Deletes a specific email by ID."""
    response = requests.delete(f"{BASE_URL}/emails/{email_id}/")
    response.raise_for_status()
    return response.json()

def search_unread_from_sender(sender: str):
    """Searches unread emails from a specific sender."""
    response = requests.get(f"{BASE_URL}/emails/unread/")
    response.raise_for_status()
    unread_emails = response.json()
    filtered_emails = [email for email in unread_emails if email['sender'].lower() == sender.lower()]
    return filtered_emails


