import email as email_lib
import imaplib
import os
from email.header import decode_header

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from gmail_creds import GmailCreds

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"data": "Gmail Backend Ready!"}


def check_gmail_login(email: str, password: str) -> bool:
    try:
        # Connect to the Gmail IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")

        # Log in to the Gmail account
        mail.login(email, password)

        # Logout to close the connection
        mail.logout()

        # If the login was successful, return True
        return True
    except Exception as e:
        # If an exception occurs, return False
        return False


@app.post("/api/gmail_login")
async def login(creds: GmailCreds):
    # Check if the login is successful
    if check_gmail_login(creds.email, creds.password):
        # If successful, write credentials to the creds.txt file
        with open("creds.txt", "w") as file:
            file.write(f"Email: {creds.email}\nPassword: {creds.password}")

        # Return a success message
        return {"message": "Login successful!"}
    else:
        # If login fails, return an error message
        return {"message": "Login failed. Please check your email and password."}


def read_credentials() -> dict:
    with open("creds.txt", "r") as file:
        lines = file.readlines()
        email = lines[0].split(":")[1].strip()
        password = lines[1].split(":")[1].strip()
    return {"email": email, "password": password}


def login_and_count_unread():
    credentials = read_credentials()
    if credentials:
        email_address = credentials["email"]
        password = credentials["password"]

        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")

        # Log in to the email account
        mail.login(email_address, password)

        # Select the mailbox you want to check (e.g., "INBOX")
        mail.select("inbox", readonly=True)

        # Search for unread emails
        status, messages = mail.search(None, 'X-GM-RAW "is:unread"')

        # Get the count of unread emails
        unseen_count = len(messages[0].split())

        # Logout and close the connection
        mail.logout()

        return unseen_count
    else:
        return {"message": "Unauthorized! Please login again!"}


@app.get("/api/unread_count")
async def unread_count():
    try:
        login_and_count_unread()
        return {"unread_count": login_and_count_unread()}
    except Exception as e:
        return {"message": "Unauthorized! Please login again!"}


def login_and_fetch_unread_emails(search_criteria: str):
    credentials = read_credentials()
    if credentials:
        email_address = credentials["email"]
        password = credentials["password"]

        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")

        # Log in to the email account
        mail.login(email_address, password)

        # Select the mailbox you want to check (e.g., "INBOX")
        mail.select("inbox", readonly=True)

        # Search for unread emails
        status, messages = mail.search(None, search_criteria)

        # Get the list of email IDs
        email_ids = messages[0].split()

        # List to store email details
        emails_data = []

        for email_id in email_ids:
            # Fetch the email by ID
            status, msg_data = mail.fetch(email_id, "(RFC822)")

            # Parse the email content
            raw_email = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw_email)

            # Get the subject, sender, date, and body
            subject, encoding = decode_header(msg["Subject"])[0]
            subject = subject.decode(encoding) if isinstance(subject, bytes) else subject
            from_, encoding = decode_header(msg.get("From"))[0]
            from_ = from_.decode(encoding) if isinstance(from_, bytes) else from_

            # Initialize an empty variable to store the body
            body = ""

            # Get the body of the email
            if msg.is_multipart():
                # If the email is multipart (contains both text and HTML)
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8")
                        break
            else:
                # If the email is not multipart
                body = msg.get_payload(decode=True).decode("utf-8")

            # Add email details to the list
            email_data = {
                "Subject": subject,
                "From": from_,
                "Date": msg.get("Date"),
                "Body": body
            }
            emails_data.append(email_data)

        # Logout and close the connection
        mail.logout()

        return emails_data
    else:
        return {"message": "Unauthorized! Please login again!"}


@app.get("/api/unread_emails")
async def unread_emails():
    try:
        return login_and_fetch_unread_emails('X-GM-RAW "is:unread"')
    except Exception as e:
        return {"message": "Unauthorized! Please login again!"}


@app.get("/api/all_emails")
async def all_emails():
    try:
        return login_and_fetch_unread_emails('X-GM-RAW "is:all"')
    except Exception as e:
        return {"message": "Unauthorized! Please login again!"}


def delete_creds_file():
    try:
        # Delete the creds.txt file if it exists
        os.remove("creds.txt")
        return True
    except FileNotFoundError:
        # If the file doesn't exist, return False
        return False


@app.get("/api/logout")
async def logout():
    # Delete the creds.txt file
    deleted = delete_creds_file()

    if deleted:
        return {"message": "Logout successful!"}
    else:
        return {"message": "Logout unsuccessful!"}

