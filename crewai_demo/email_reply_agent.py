import os
import os.path
import base64
from email.mime.text import MIMEText
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# NOTE: This script requires 'credentials.json' AND 'token.json' in the same directory.

# Check for API Key
if "GOOGLE_API_KEY" not in os.environ:
    print("Error: GOOGLE_API_KEY environment variable is not set.")
    print("Please set it with: $env:GOOGLE_API_KEY='your_api_key_here'")
    exit(1)

# Set the specific environment variable that LiteLLM looks for
os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

# ============================================================================
# SECURITY CONFIGURATION - Emails matching these patterns will NEVER get replies
# ============================================================================

# Domains that should NEVER receive auto-replies
BLOCKED_DOMAINS = [
    "noreply@",
    "no-reply@",
    "donotreply@",
    "mailer-daemon@",
    "postmaster@",
    "notifications@",
    "alert@",
    "alerts@",
    "newsletter@",
    "news@",
    "marketing@",
    "promo@",
    "promotions@",
    "offers@",
    "deals@",
    "unsubscribe@",
]

# Subject keywords that indicate spam/scam/automated messages
BLOCKED_SUBJECTS = [
    "unsubscribe",
    "verify your account",
    "confirm your email",
    "password reset",
    "security alert",
    "unusual activity",
    "act now",
    "limited time",
    "you've won",
    "congratulations",
    "claim your",
    "urgent action required",
    "account suspended",
    "verify immediately",
    "nigerian",
    "inheritance",
    "lottery",
    "million dollars",
    "wire transfer",
]

# Sender domains that are automated/should not receive replies
BLOCKED_SENDER_DOMAINS = [
    "github.com",
    "google.com",
    "googleapis.com",
    "amazonses.com",
    "sendgrid.net",
    "mailchimp.com",
    "constantcontact.com",
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "tiktok.com",
    "spotify.com",
    "netflix.com",
    "apple.com",
    "microsoft.com",
    "paypal.com",
    "squarespace.com",
    "wix.com",
    "shopify.com",
]


def is_safe_to_reply(sender: str, subject: str) -> tuple[bool, str]:
    """Check if an email is safe to reply to. Returns (is_safe, reason)."""
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    
    # Check blocked sender patterns
    for blocked in BLOCKED_DOMAINS:
        if blocked in sender_lower:
            return False, f"Sender matches blocked pattern: {blocked}"
    
    # Check blocked sender domains
    for domain in BLOCKED_SENDER_DOMAINS:
        if domain in sender_lower:
            return False, f"Sender from automated/no-reply domain: {domain}"
    
    # Check blocked subject keywords
    for keyword in BLOCKED_SUBJECTS:
        if keyword in subject_lower:
            return False, f"Subject contains blocked keyword: {keyword}"
    
    return True, "Email appears safe for reply"


# ============================================================================
# GMAIL TOOLS
# ============================================================================

def get_gmail_service():
    """Get authenticated Gmail service."""
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
    ]
    creds = None
    
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None
    
    return build("gmail", "v1", credentials=creds)


class GmailReadTool(BaseTool):
    name: str = "Read Latest Email"
    description: str = "Reads the most recent unread email and returns its details including sender, subject, and body."

    def _run(self, query: str = "is:unread") -> str:
        service = get_gmail_service()
        if not service:
            return "Error: Gmail not authenticated. Run setup_gmail_token.py first."
        
        try:
            results = service.users().messages().list(userId="me", q="is:unread", maxResults=1).execute()
            messages = results.get("messages", [])
            
            if not messages:
                return "No unread emails found."
            
            msg = messages[0]
            txt = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
            payload = txt.get("payload", {})
            headers = payload.get("headers", [])
            
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "(Unknown Sender)")
            message_id = next((h["value"] for h in headers if h["name"] == "Message-ID"), "")
            
            # Get body
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        data = part.get("body", {}).get("data", "")
                        if data:
                            body = base64.urlsafe_b64decode(data).decode("utf-8")
                            break
            elif "body" in payload:
                data = payload["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
            
            if not body:
                body = txt.get("snippet", "(No body content)")
            
            # Security check
            is_safe, reason = is_safe_to_reply(sender, subject)
            safety_status = "SAFE TO REPLY" if is_safe else f"DO NOT REPLY - {reason}"
            
            return f"""
EMAIL DETAILS:
==============
From: {sender}
Subject: {subject}
Message-ID: {message_id}
Gmail-ID: {msg["id"]}

SECURITY CHECK: {safety_status}

BODY:
{body[:2000]}{"..." if len(body) > 2000 else ""}
"""
        except Exception as e:
            return f"Error reading email: {e}"


class GmailDraftTool(BaseTool):
    name: str = "Create Draft Reply"
    description: str = "Creates a draft reply to an email. Input should be: recipient_email|subject|body|original_message_id"

    def _run(self, input_str: str) -> str:
        service = get_gmail_service()
        if not service:
            return "Error: Gmail not authenticated. Run setup_gmail_token.py first."
        
        try:
            parts = input_str.split("|")
            if len(parts) < 4:
                return "Error: Input must be: recipient_email|subject|body|original_message_id"
            
            to_email = parts[0].strip()
            subject = parts[1].strip()
            body = parts[2].strip()
            original_id = parts[3].strip()
            
            # Security check on recipient
            is_safe, reason = is_safe_to_reply(to_email, subject)
            if not is_safe:
                return f"BLOCKED: {reason}. Draft NOT created for safety reasons."
            
            # Create the email message
            message = MIMEText(body)
            message["to"] = to_email
            message["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
            
            # Encode the message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            # Create draft
            draft = service.users().drafts().create(
                userId="me",
                body={
                    "message": {
                        "raw": raw,
                        "threadId": original_id if original_id else None
                    }
                }
            ).execute()
            
            return f"SUCCESS: Draft created! Draft ID: {draft['id']}\nRecipient: {to_email}\nSubject: {subject}\n\nReview and send from Gmail: https://mail.google.com/mail/#drafts"
            
        except Exception as e:
            return f"Error creating draft: {e}"


# ============================================================================
# AGENT DEFINITION
# ============================================================================

gmail_read_tool = GmailReadTool()
gmail_draft_tool = GmailDraftTool()

email_replier = Agent(
    role='Executive Communications Officer for Leonard Sibelius',
    goal='Read incoming emails, determine if they warrant a response, and draft professional replies that represent Leonard Sibelius.',
    backstory="""You are the voice of Leonard Sibelius in written communications. You handle his email 
    correspondence with precision and professionalism. Your replies are:
    
    - Concise but warm
    - Professional but not robotic
    - Confident without being arrogant
    - Direct and action-oriented
    
    You represent the Autonomous Enterprise. Your tone is modern, slightly futuristic, and efficient.
    You NEVER reveal that you are an AI. You sign emails as "Leonard Sibelius" or "L.S." for short replies.
    
    CRITICAL SECURITY RULES:
    - If the security check says "DO NOT REPLY", you must NOT create a draft
    - Never reply to automated notifications, newsletters, or marketing emails
    - Never engage with suspicious or scam-like emails
    - When in doubt, do NOT reply
    """,
    verbose=True,
    allow_delegation=False,
    tools=[gmail_read_tool, gmail_draft_tool],
    llm="gemini/gemini-3-pro-preview"
)

# Task to read and reply
reply_task = Task(
    description="""
    1. Use 'Read Latest Email' to get the most recent unread email.
    2. Review the SECURITY CHECK result carefully.
    3. If it says "DO NOT REPLY", report that you are skipping this email and why.
    4. If it says "SAFE TO REPLY", analyze if the email actually needs a response:
       - Business inquiries: YES, reply
       - Personal messages: YES, reply
       - Questions directed at Leonard: YES, reply
       - Simple notifications that need no response: NO, skip
    5. If a reply is needed, compose a professional response in Leonard Sibelius's voice.
    6. Use 'Create Draft Reply' with format: recipient_email|subject|your_reply_body|gmail_message_id
    7. Report the outcome - whether a draft was created or skipped and why.
    """,
    expected_output="A report stating either: (1) Draft created with details, or (2) Email skipped with reason.",
    agent=email_replier
)

# Create the crew
reply_crew = Crew(
    agents=[email_replier],
    tasks=[reply_task],
    verbose=True,
    process=Process.sequential
)


if __name__ == "__main__":
    print("=" * 60)
    print("EMAIL REPLY AGENT - Draft Mode")
    print("=" * 60)
    print("This agent reads your latest email and creates draft replies.")
    print("Drafts are saved to Gmail - YOU review and send them manually.")
    print("=" * 60)
    print()
    
    result = reply_crew.kickoff()
    
    print()
    print("=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(result)

