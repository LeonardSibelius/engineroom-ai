# Leonard's Notes 📝

Personal reminders and thoughts about the Engine Room project.

---

## Quick Reference

### Launch Dashboard
```powershell
cd C:\engineroom\crewai_demo
python -m streamlit run dashboard.py
```

### Deploy Website
```powershell
cd C:\engineroom
npx firebase deploy
```

### Backup to GitHub
```powershell
cd C:\engineroom
git add .
git commit -m "your message"
git push
```

---

## Accounts & Keys

| Service | Account | Notes |
|---------|---------|-------|
| Gmail (agents) | wpneural@gmail.com | OAuth token in token.json |
| Firebase | wpneural@gmail.com | Project: engineroom-ai |
| GitHub | LeonardSibelius | Pseudonym for safety |
| Google AI | wpneural@gmail.com | API key in .env |

---

## Important Files (Local Only - Not on GitHub)

- `crewai_demo/.env` - Google API key
- `crewai_demo/token.json` - Gmail OAuth token
- `crewai_demo/credentials.json` - Gmail OAuth app credentials
- `crewai_demo/token_drive.json` - Google Drive OAuth token (book sync)

If you set up on a new computer, you'll need to:
1. Create new `.env` with your API key
2. Run `python setup_gmail_token.py` to re-authenticate Gmail
3. Run `python setup_drive_token.py` to re-authenticate Drive (optional)

---

## Google Drive Book Backup (Recommended)

If your PC is acting up, treat Google Drive as the canonical “books library”:

1. Upload PDFs to a Drive folder
2. Copy the folder URL (it contains `/folders/<FOLDER_ID>`)
3. Ingest from Drive (downloads PDFs first):

```powershell
cd C:\engineroom\crewai_demo
python ingest_books.py --sync-drive --drive-folder-id "<FOLDER_ID>"
```

You can also do it from the Streamlit dashboard sidebar: **Google Drive Books → “Sync PDFs from Drive + Ingest”**.

## Reminders

- The pseudonym "Leonard Sibelius" is used in case agents cause problems
- Real name: Walt Parkman
- Email reply agent creates DRAFTS only - review before sending!
- Security filters block most automated emails from getting replies

---

## Session Log

### Dec 12, 2025
- Built email reader agent
- Built email reply agent with security filters
- Created Streamlit dashboard
- Upgraded to Gemini 3 Pro
- Set up Firebase hosting
- Set up GitHub backup
- Created documentation files

---

## Ideas to Explore

*Add your thoughts here as you have them...*

- 
- 
- 

---

*This file is for your personal notes. Feel free to edit however you like!*

