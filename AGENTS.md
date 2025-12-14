# Engine Room Agents 🤖

Documentation of all AI agents in the system.

---

## 1. Email Reader Agent
**File:** `crewai_demo/email_agent.py`

**Role:** Chief of Staff for Leonard Sibelius

**Purpose:** 
- Monitors Gmail inbox for unread emails
- Filters spam, newsletters, and irrelevant messages
- Surfaces important emails that need attention
- Provides summaries of who sent what and why it matters

**How to Run:**
```powershell
python email_agent.py
```

**Output:** Terminal report of important emails with summaries.

---

## 2. Email Reply Agent
**File:** `crewai_demo/email_reply_agent.py`

**Role:** Executive Communications Officer for Leonard Sibelius

**Purpose:**
- Reads latest unread email
- Checks security filters (blocks scams, phishing, automated senders)
- If safe, drafts a professional reply in Leonard's voice
- Saves draft to Gmail (does NOT auto-send)

**How to Run:**
```powershell
python email_reply_agent.py
```

**Output:** Draft saved to Gmail Drafts folder for review.

**Security Filters:**
- Blocked sender patterns: `noreply@`, `newsletter@`, `marketing@`, etc.
- Blocked domains: github.com, google.com, linkedin.com, paypal.com, etc.
- Blocked subject keywords: "verify your account", "you've won", "urgent action", etc.

---

## 3. Topic Expert Agent
**File:** `crewai_demo/topic_expert_agent.py`

**Role:** Historical Evidence Analyst for Leonard Sibelius

**Purpose:**
- Creates educational content from ingested books
- Uses RAG (Retrieval Augmented Generation) to search knowledge base
- Provides sourced, factual responses for debates
- Counter-extremism education mission

**How to Run:**
```powershell
# Interactive mode
python topic_expert_agent.py

# Command line mode
python topic_expert_agent.py "historical patterns of conquest"
```

**Output:** Researched, cited content formatted for social media.

**Knowledge Base:**
- Books are stored in `crewai_demo/books/` as PDFs
- Run `python ingest_books.py` to index new books
- Database stored in `crewai_demo/knowledge_db/`

**Current Sources:**
- "The History of Jihad" by Robert Spencer (449 pages, 1,235 chunks)

---

## 4. Research Crew (Demo)
**File:** `crewai_demo/hello_crew.py`

**Purpose:** Demo/test of multi-agent collaboration.

**Agents:**
- **Senior Research Analyst** - Finds trends and information
- **Tech Content Strategist** - Summarizes findings into content

**How to Run:**
```powershell
python hello_crew.py
```

---

## Agent Personality

All agents represent Leonard Sibelius with these traits:
- Concise but warm
- Professional but not robotic
- Confident without being arrogant
- Direct and action-oriented
- Modern, slightly futuristic tone

Agents sign emails as "Leonard Sibelius" or "L.S." for short replies.

---

## Adding New Agents

To create a new agent:

1. Copy `email_agent.py` as a template
2. Define the agent's role, goal, and backstory
3. Create tools the agent needs (API integrations, etc.)
4. Define tasks for the agent to complete
5. Add to dashboard.py if you want a button for it

CrewAI Docs: https://docs.crewai.com/

