# The Engine Room 🤖

**An Outstanding Agent Factory**

Personal AI agent system built by Leonard Sibelius (Walt Parkman). Autonomous agents that monitor email, filter spam, draft professional replies, and more.

## Live Site
🌐 https://engineroom-ai.web.app

## Tech Stack
- **AI Framework:** CrewAI
- **LLM:** Google Gemini 3 Pro (Preview)
- **Frontend:** HTML/CSS (Firebase Hosting)
- **Dashboard:** Streamlit
- **Email:** Gmail API with OAuth2

## Quick Start

### 1. Launch the Dashboard
```powershell
cd C:\engineroom\crewai_demo
python -m streamlit run dashboard.py
```
Then open http://localhost:8501

### 2. Or Run Agents Directly
```powershell
cd C:\engineroom\crewai_demo
$env:GOOGLE_API_KEY="your-key-here"
python email_agent.py        # Read & filter emails
python email_reply_agent.py  # Draft replies
```

## Project Structure
```
engineroom/
├── index.html              # Main presentation site
├── crewai_demo/
│   ├── dashboard.py        # Streamlit control center
│   ├── email_agent.py      # Email reader agent
│   ├── email_reply_agent.py # Email reply agent
│   ├── hello_crew.py       # Basic CrewAI test
│   ├── setup_gmail_token.py # Gmail OAuth setup
│   ├── setup_drive_token.py # Google Drive OAuth setup (book backup/sync)
│   ├── ingest_books.py     # Build knowledge base from PDFs (local or Drive)
│   ├── .env                # API key (gitignored)
│   └── token.json          # Gmail token (gitignored)
├── images/                 # Site assets
└── firebase.json           # Firebase config
```

## Security
- API keys stored in local `.env` file (never pushed to GitHub)
- Gmail OAuth tokens stay local
- Drive OAuth tokens stay local
- Email reply agent has security filters blocking scams, phishing, automated senders

## Google Drive (Book Backup + Sync)
If your PC is unreliable, you can keep your PDFs in a Drive folder and have the project download them before ingesting.

### 1) Create Drive OAuth token (one-time per PC)
```powershell
cd C:\engineroom\crewai_demo
python setup_drive_token.py
```
This creates `token_drive.json` (gitignored).

### 2) Get your Drive folder ID
In Google Drive (web), open the folder that contains your PDFs and copy the URL.
It looks like:
`https://drive.google.com/drive/folders/<FOLDER_ID>`

### 3) Sync PDFs + ingest
```powershell
cd C:\engineroom\crewai_demo
python ingest_books.py --sync-drive --drive-folder-id "<FOLDER_ID>"
```
Drive PDFs will download into `crewai_demo/books/_drive/` and then the knowledge base will rebuild in `crewai_demo/knowledge_db/`.

## Created
December 2025

## Links
- [GitHub Repo](https://github.com/LeonardSibelius/engineroom-ai)
- [Firebase Console](https://console.firebase.google.com/project/engineroom-ai)
- [Google AI Studio](https://aistudio.google.com)

