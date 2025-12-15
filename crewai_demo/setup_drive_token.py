import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token_drive.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def main():
    creds = None

    # token_drive.json stores the user's access and refresh tokens.
    if os.path.exists("token_drive.json"):
        creds = Credentials.from_authorized_user_file("token_drive.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Starting new OAuth flow for Google Drive...")
            if not os.path.exists("credentials.json"):
                print("Error: credentials.json not found in current directory.")
                print("Put the OAuth client file (Desktop app) next to this script.")
                return

            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open("token_drive.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())
            print("token_drive.json created successfully!")
    else:
        print("Valid token_drive.json already exists.")


if __name__ == "__main__":
    main()


