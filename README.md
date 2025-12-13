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
│   ├── .env                # API key (gitignored)
│   └── token.json          # Gmail token (gitignored)
├── images/                 # Site assets
└── firebase.json           # Firebase config
```

## Security
- API keys stored in local `.env` file (never pushed to GitHub)
- Gmail OAuth tokens stay local
- Email reply agent has security filters blocking scams, phishing, automated senders

## Created
December 2025

## Links
- [GitHub Repo](https://github.com/LeonardSibelius/engineroom-ai)
- [Firebase Console](https://console.firebase.google.com/project/engineroom-ai)
- [Google AI Studio](https://aistudio.google.com)

