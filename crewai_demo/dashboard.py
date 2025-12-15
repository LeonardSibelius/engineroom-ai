import streamlit as st
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load API key from .env file if it exists
load_dotenv()

# ============================================================================
# PAGE CONFIG - Must be first Streamlit command
# ============================================================================
st.set_page_config(
    page_title="The Engine Room",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS - Engine Room Dark Theme
# ============================================================================
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0f172a;
        border-right: 1px solid #334155;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Main title glow */
    .main-title {
        font-size: 3rem;
        font-weight: 700;
        color: #f8fafc;
        text-align: center;
        text-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
        margin-bottom: 0;
    }
    
    .subtitle {
        text-align: center;
        color: #3b82f6;
        font-size: 1.1rem;
        margin-top: 0;
    }
    
    /* Agent cards */
    .agent-card {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .agent-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
    }
    
    .agent-card.reader {
        border-left: 4px solid #3b82f6;
    }
    
    .agent-card.replier {
        border-left: 4px solid #8b5cf6;
    }
    
    /* Status indicators */
    .status-ready {
        color: #22c55e;
    }
    
    .status-running {
        color: #f59e0b;
    }
    
    .status-error {
        color: #ef4444;
    }
    
    /* Output terminal */
    .terminal-output {
        background: #0c0c0c;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 0.85rem;
        color: #22c55e;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
        transform: translateY(-2px);
    }
    
    /* Info boxes */
    .info-box {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_api_key():
    """Check if API key is configured."""
    return "api_key" in st.session_state and st.session_state.api_key

def check_gmail_token():
    """Check if Gmail token exists."""
    return os.path.exists("token.json")

def check_drive_token():
    """Check if Google Drive token exists."""
    return os.path.exists("token_drive.json")

def run_agent(script_name: str, args: list = None) -> str:
    """Run an agent script and capture output."""
    # Only some scripts require the Gemini API key.
    requires_api_key = script_name in {"email_agent.py", "email_reply_agent.py", "topic_expert_agent.py"}
    if requires_api_key and not check_api_key():
        return "ERROR: API key not configured. Please enter it in the sidebar."
    
    env = os.environ.copy()
    if requires_api_key:
        env["GOOGLE_API_KEY"] = st.session_state.api_key
        env["GEMINI_API_KEY"] = st.session_state.api_key
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONLEGACYWINDOWSSTDIO"] = "1"
    
    # Build command list
    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=600,  # 10 minutes - let the agent think deeply
            errors='replace'  # Handle encoding issues
        )
        
        # Combine stdout and stderr, filter out noise
        all_output = []
        
        if result.stdout:
            all_output.append(result.stdout)
        
        if result.stderr:
            # Filter out encoding warnings and noise
            useful_stderr = [line for line in result.stderr.split('\n') 
                           if 'charmap' not in line 
                           and 'CrewAIEventsBus' not in line
                           and line.strip()]
            if useful_stderr:
                all_output.append("\n".join(useful_stderr))
        
        output = "\n".join(all_output)
        
        # Clean up output
        import re
        
        # Try to extract just the RESULT section (cleanest output)
        result_match = re.search(r'={50,}\s*\nRESULT:\s*\n={50,}\s*\n(.+?)(?:={50,}|$)', output, re.DOTALL)
        if result_match:
            output = result_match.group(1).strip()
        
        # Remove garbled box-drawing characters and other noise
        output = re.sub(r'[""¦¢Œ˜œ‚ï¸�]+', '', output)  # Remove garbled chars
        output = re.sub(r'ðŸ[^\s]*', '', output)  # Remove broken emoji codes
        output = re.sub(r'š"[^\s]*', '', output)  # Remove more broken codes
        output = re.sub(r'\s*\|\s*', ' ', output)  # Remove pipes
        output = re.sub(r'\n{3,}', '\n\n', output)  # Remove excessive newlines
        output = re.sub(r'^\s*$', '', output, flags=re.MULTILINE)  # Remove blank lines
        
        return output.strip() if output.strip() else "Agent completed with no output."
    except subprocess.TimeoutExpired:
        return "ERROR: Agent timed out after 10 minutes."
    except Exception as e:
        return f"ERROR: {str(e)}"


# ============================================================================
# SIDEBAR - Configuration
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # Try to get API key from environment (.env file) or session state
    default_key = os.environ.get("GOOGLE_API_KEY", "")
    if "api_key" not in st.session_state and default_key:
        st.session_state.api_key = default_key
    
    # API Key input (password field)
    api_key = st.text_input(
        "Google API Key",
        type="password",
        value=st.session_state.get("api_key", ""),
        help="Your Gemini API key from Google AI Studio"
    )
    if api_key:
        st.session_state.api_key = api_key
    
    # Show if loaded from .env
    if default_key:
        st.caption("✅ Loaded from .env file")
    
    st.markdown("---")
    
    # Status indicators
    st.markdown("### 📊 System Status")
    
    # API Key status
    if check_api_key():
        st.markdown("✅ **API Key:** Configured")
    else:
        st.markdown("❌ **API Key:** Not set")
    
    # Gmail token status
    if check_gmail_token():
        st.markdown("✅ **Gmail:** Authenticated")
    else:
        st.markdown("❌ **Gmail:** Not authenticated")
        st.caption("Run `python setup_gmail_token.py` in terminal")

    # Drive token status
    if check_drive_token():
        st.markdown("✅ **Drive:** Authenticated")
    else:
        st.markdown("❌ **Drive:** Not authenticated")
        st.caption("Run `python setup_drive_token.py` in terminal")
    
    # Knowledge base status
    knowledge_db = Path(__file__).parent / "knowledge_db"
    if knowledge_db.exists():
        st.markdown("✅ **Knowledge Base:** Ready")
    else:
        st.markdown("⚠️ **Knowledge Base:** Not built")
        st.caption("Run `python ingest_books.py` (or use Drive sync below)")

    st.markdown("---")
    st.markdown("### ☁️ Google Drive Books")
    drive_folder_id = st.text_input(
        "Drive Folder ID (PDFs)",
        value=st.session_state.get("drive_folder_id", os.environ.get("DRIVE_FOLDER_ID", "")),
        help="Paste the folder ID from a Drive folder link. Example link contains: /folders/<ID>"
    )
    if drive_folder_id:
        st.session_state.drive_folder_id = drive_folder_id

    if st.button("⬇️ Sync PDFs from Drive + Ingest", use_container_width=True):
        if not check_drive_token():
            st.error("Drive is not authenticated. Run `python setup_drive_token.py` first.")
        elif not drive_folder_id:
            st.error("Please paste a Drive Folder ID first.")
        else:
            with st.spinner("Syncing PDFs from Drive and rebuilding knowledge base..."):
                st.session_state.ingest_output = run_agent(
                    "ingest_books.py",
                    ["--sync-drive", "--drive-folder-id", drive_folder_id],
                )
                st.session_state.ingest_time = datetime.now().strftime("%H:%M:%S")
    
    st.markdown("---")
    
    # Web Article Ingestion
    st.markdown("### 📰 Add Web Article")
    article_url = st.text_input(
        "Article URL",
        value="",
        placeholder="https://example.com/article",
        help="Paste a news article URL to add it to your knowledge base"
    )
    
    if st.button("📥 Add Article to Knowledge Base", use_container_width=True):
        if not article_url:
            st.error("Please paste an article URL first.")
        elif not article_url.startswith("http"):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            with st.spinner("Fetching and indexing article..."):
                st.session_state.article_output = run_agent(
                    "ingest_books.py",
                    ["--add-article", article_url],
                )
                st.session_state.article_time = datetime.now().strftime("%H:%M:%S")
                st.success("Article added! Check 'Article Output' tab.")
    
    st.markdown("---")
    
    # Model info
    st.markdown("### 🤖 Model")
    st.markdown("**Gemini 3 Pro** (Preview)")
    
    st.markdown("---")
    
    # Links
    st.markdown("### 🔗 Links")
    st.markdown("[📧 Gmail Drafts](https://mail.google.com/mail/#drafts)")
    st.markdown("[🌐 Engine Room Site](https://engineroom-ai.web.app)")
    st.markdown("[💾 GitHub Repo](https://github.com/LeonardSibelius/engineroom-ai)")


# ============================================================================
# MAIN CONTENT
# ============================================================================

# Header
st.markdown('<h1 class="main-title">THE ENGINE ROOM</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI Agent Control Center</p>', unsafe_allow_html=True)

st.markdown("---")

# Agent Cards in columns
col1, col2, col3 = st.columns(3)

# Email Reader Agent
with col1:
    st.markdown("""
    <div class="agent-card reader">
        <h3>📨 Email Reader</h3>
        <p style="color: #94a3b8;">Chief of Staff</p>
        <p style="color: #cbd5e1; font-size: 0.85rem;">
            Monitors inbox, filters spam, surfaces important emails.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Run Email Reader", key="run_reader", use_container_width=True):
        with st.spinner("Agent is reading your inbox..."):
            st.session_state.reader_output = run_agent("email_agent.py")
            st.session_state.reader_time = datetime.now().strftime("%H:%M:%S")

# Email Replier Agent
with col2:
    st.markdown("""
    <div class="agent-card replier">
        <h3>✉️ Email Replier</h3>
        <p style="color: #94a3b8;">Executive Communications</p>
        <p style="color: #cbd5e1; font-size: 0.85rem;">
            Drafts replies in Leonard's voice. Security filters block scams.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Run Email Replier", key="run_replier", use_container_width=True):
        with st.spinner("Agent is composing replies..."):
            st.session_state.replier_output = run_agent("email_reply_agent.py")
            st.session_state.replier_time = datetime.now().strftime("%H:%M:%S")

# Topic Expert Agent
with col3:
    st.markdown("""
    <div class="agent-card" style="border-left: 4px solid #22c55e;">
        <h3>📚 Topic Expert</h3>
        <p style="color: #94a3b8;">Historical Evidence Analyst</p>
        <p style="color: #cbd5e1; font-size: 0.85rem;">
            Creates educational content from historical sources.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    topic_input = st.text_input("Topic:", placeholder="e.g., patterns of conquest", key="topic_input")
    
    if st.button("🚀 Research Topic", key="run_expert", use_container_width=True):
        if topic_input:
            with st.spinner("Agent is researching..."):
                st.session_state.expert_output = run_agent("topic_expert_agent.py", [topic_input])
                st.session_state.expert_time = datetime.now().strftime("%H:%M:%S")
        else:
            st.warning("Please enter a topic first.")

st.markdown("---")

# Output Section
st.markdown("### 📟 Agent Output")

# Tabs for different outputs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📨 Reader Output", "✉️ Replier Output", "📚 Expert Output", "☁️ Ingestion Output", "📰 Article Output"])

with tab1:
    if "reader_output" in st.session_state:
        st.caption(f"Last run: {st.session_state.get('reader_time', 'Unknown')}")
        st.markdown(f'<div class="terminal-output">{st.session_state.reader_output}</div>', 
                   unsafe_allow_html=True)
    else:
        st.info("Click 'Run Email Reader' to see output here.")

with tab2:
    if "replier_output" in st.session_state:
        st.caption(f"Last run: {st.session_state.get('replier_time', 'Unknown')}")
        st.markdown(f'<div class="terminal-output">{st.session_state.replier_output}</div>', 
                   unsafe_allow_html=True)
    else:
        st.info("Click 'Run Email Replier' to see output here.")

with tab3:
    if "expert_output" in st.session_state:
        st.caption(f"Last run: {st.session_state.get('expert_time', 'Unknown')}")
        st.markdown(f'<div class="terminal-output">{st.session_state.expert_output}</div>', 
                   unsafe_allow_html=True)
    else:
        st.info("Enter a topic and click 'Research Topic' to see output here.")

with tab4:
    if "ingest_output" in st.session_state:
        st.caption(f"Last run: {st.session_state.get('ingest_time', 'Unknown')}")
        st.markdown(f'<div class="terminal-output">{st.session_state.ingest_output}</div>',
                   unsafe_allow_html=True)
    else:
        st.info("Use the sidebar button 'Sync PDFs from Drive + Ingest' to rebuild the knowledge base.")

with tab5:
    if "article_output" in st.session_state:
        st.caption(f"Last run: {st.session_state.get('article_time', 'Unknown')}")
        st.markdown(f'<div class="terminal-output">{st.session_state.article_output}</div>',
                   unsafe_allow_html=True)
    else:
        st.info("Use the sidebar to add a web article URL to your knowledge base.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.8rem;">
    <p>THE ENGINE ROOM • Powered by CrewAI + Gemini 3 Pro • Leonard Sibelius</p>
</div>
""", unsafe_allow_html=True)

