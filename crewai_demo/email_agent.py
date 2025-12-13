import os
import os.path
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# NOTE: This script requires 'credentials.json' AND 'token.json' in the same directory.

# Check for API Key
if "GOOGLE_API_KEY" not in os.environ:
    print("❌ Error: GOOGLE_API_KEY environment variable is not set.")
    print("Please set it with: $env:GOOGLE_API_KEY='your_api_key_here'")
    exit(1)

# Set the specific environment variable that LiteLLM looks for
os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

# --- Custom Gmail Tool ---
class GmailSearchTool(BaseTool):
    name: str = "Search Inbox"
    description: str = "Searches the user's Gmail inbox for the latest 5 unread emails. Returns a summary."

    def _run(self, query: str = "unread") -> str:
        SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        creds = None
        
        # Load credentials from token.json
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        # If no valid credentials, fail gracefully
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    return f"Error: Token expired and refresh failed: {e}. Please run setup_gmail_token.py again."
            else:
                return "Error: No valid token.json found. Please run setup_gmail_token.py."

        try:
            service = build("gmail", "v1", credentials=creds)
            
            # List messages
            results = service.users().messages().list(userId="me", q="is:unread", maxResults=5).execute()
            messages = results.get("messages", [])

            if not messages:
                return "No unread emails found."

            email_summaries = []
            for msg in messages:
                txt = service.users().messages().get(userId="me", id=msg["id"]).execute()
                payload = txt.get("payload", {})
                headers = payload.get("headers", [])
                
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "(Unknown Sender)")
                snippet = txt.get("snippet", "")
                
                email_summaries.append(f"From: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")

            return "\n".join(email_summaries)

        except Exception as e:
            return f"Error accessing Gmail API: {e}"

# --- Agent Definition ---

# Instantiate the tool
gmail_tool = GmailSearchTool()

# Define the Agent
email_handler = Agent(
    role='Chief of Staff for Leonard Sibelius',
    goal='Filter incoming emails, discard spam, and forward important opportunities to the Boss.',
    backstory="""You are the AI Gatekeeper for Leonard Sibelius, the architect of the Autonomous Enterprise.
    Your job is to protect his time. You strictly filter out spam, cold sales pitches, and newsletters.
    You ONLY let through high-value opportunities, personal messages from known contacts, or urgent business matters.
    You represent the "Machine" - efficient, professional, and slightly futuristic.""",
    verbose=True,
    allow_delegation=False,
    tools=[gmail_tool],
    llm="gemini/gemini-2.5-pro"
)

# Define the Task
filter_emails_task = Task(
    description="""
    1. Use the 'Search Inbox' tool to find the latest unread emails.
    2. For each email, analyze the sender and subject.
    3. If it is SPAM or IRRELEVANT, mark it as read and ignore.
    4. If it is IMPORTANT (a lead, a client, a partner), draft a summary of who it is and what they want.
    5. Compile a report of the IMPORTANT emails found.
    """,
    expected_output="A bulleted list of important emails with summaries, or 'No important emails found'.",
    agent=email_handler
)

# Define the Crew
email_crew = Crew(
    agents=[email_handler],
    tasks=[filter_emails_task],
    verbose=True,
    process=Process.sequential
)

if __name__ == "__main__":
    print("## Starting Email Agent (Class Tool Version)...")
    result = email_crew.kickoff()
    print("######################")
    print(result)
