"""
Book & Article Ingestion Script
Converts PDF books and web articles into a searchable knowledge base using ChromaDB.
"""

import os
import sys
import io
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Check for required packages
try:
    import chromadb
    from chromadb.utils import embedding_functions
    import pymupdf  # PyMuPDF for PDF extraction
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Missing package: {e}")
    print("Install with: pip install chromadb pymupdf google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 beautifulsoup4 requests")
    sys.exit(1)

# Configuration
DEFAULT_BOOKS_DIR = Path(__file__).parent / "books"
BOOKS_DIR = Path(os.environ.get("BOOKS_DIR", str(DEFAULT_BOOKS_DIR)))
DB_DIR = Path(__file__).parent / "knowledge_db"
COLLECTION_NAME = "historical_sources"
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks

DRIVE_TOKEN_PATH = Path(__file__).parent / "token_drive.json"
DRIVE_CREDENTIALS_PATH = Path(__file__).parent / "credentials.json"
DEFAULT_DRIVE_SYNC_DIR = BOOKS_DIR / "_drive"

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def _safe_filename(name: str) -> str:
    """Make a filename safe for Windows/macOS/Linux filesystems."""
    # Remove reserved characters: \ / : * ? " < > |
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def _parse_rfc3339(ts: str) -> datetime:
    # Example: "2025-12-14T12:34:56.123Z"
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)

def get_drive_service(token_path: Path = DRIVE_TOKEN_PATH, credentials_path: Path = DRIVE_CREDENTIALS_PATH):
    """Create an authenticated Google Drive service using OAuth token_drive.json."""
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), DRIVE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError(
                "No valid Drive OAuth token found.\n"
                "Run: python setup_drive_token.py\n"
                f"Expected token file: {token_path}\n"
                f"Expected credentials file: {credentials_path}"
            )

    return build("drive", "v3", credentials=creds)

def list_pdfs_in_drive_folder(service, folder_id: str) -> list[dict]:
    """List PDFs in a Drive folder."""
    q = f"mimeType='application/pdf' and trashed=false and '{folder_id}' in parents"
    files: list[dict] = []
    page_token = None

    while True:
        resp = (
            service.files()
            .list(
                q=q,
                spaces="drive",
                fields="nextPageToken, files(id, name, modifiedTime, size)",
                pageToken=page_token,
                pageSize=200,
            )
            .execute()
        )
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # Keep a deterministic order
    return sorted(files, key=lambda f: f.get("name", "").lower())

def download_drive_file(service, file_id: str, dest_path: Path):
    """Download a Drive file to dest_path."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    with io.FileIO(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

def sync_drive_pdfs(folder_id: str, dest_dir: Path = DEFAULT_DRIVE_SYNC_DIR, force: bool = False) -> list[Path]:
    """Sync PDFs from a Drive folder into dest_dir. Returns local PDF paths."""
    print(f"Syncing PDFs from Google Drive folder: {folder_id}")
    service = get_drive_service()
    files = list_pdfs_in_drive_folder(service, folder_id)

    if not files:
        print("No PDFs found in that Drive folder.")
        return []

    print(f"Found {len(files)} PDF(s) in Drive.")
    downloaded: list[Path] = []

    for f in files:
        name = _safe_filename(f.get("name", "unknown.pdf"))
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        dest_path = dest_dir / name

        remote_size = int(f.get("size") or 0)
        remote_mtime = f.get("modifiedTime")

        should_download = force or (not dest_path.exists())
        if not should_download and remote_size and dest_path.exists():
            try:
                local_size = dest_path.stat().st_size
                if local_size != remote_size:
                    should_download = True
            except OSError:
                should_download = True

        if not should_download and remote_mtime and dest_path.exists():
            try:
                remote_dt = _parse_rfc3339(remote_mtime)
                local_dt = datetime.fromtimestamp(dest_path.stat().st_mtime, tz=timezone.utc)
                if local_dt < remote_dt:
                    should_download = True
            except Exception:
                # If time parsing fails, fall back to "don't re-download"
                pass

        if should_download:
            print(f"  Downloading: {name}")
            download_drive_file(service, f["id"], dest_path)
        else:
            print(f"  Up-to-date: {name}")

        downloaded.append(dest_path)

    return downloaded

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    print(f"  Extracting text from: {pdf_path.name}")

    doc = None
    try:
        doc = pymupdf.open(pdf_path)
        text = ""
        page_count = len(doc)

        for page_num, page in enumerate(doc):
            text += page.get_text()
            if (page_num + 1) % 50 == 0:
                print(f"    Processed {page_num + 1} pages...")

        print(f"  Extracted {len(text):,} characters from {page_count} pages")
        return text
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def chunk_text(text: str, source_name: str, source_type: str = "book") -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text_content = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk_text_content.rfind('.')
            if last_period > CHUNK_SIZE // 2:
                chunk_text_content = chunk_text_content[:last_period + 1]
                end = start + last_period + 1
        
        chunks.append({
            "id": f"{source_name}_{chunk_id}",
            "text": chunk_text_content.strip(),
            "source": source_name,
            "source_type": source_type,
            "chunk_index": chunk_id
        })
        
        chunk_id += 1
        start = end - CHUNK_OVERLAP
    
    return chunks


# ============================================================================
# WEB ARTICLE INGESTION
# ============================================================================

def extract_article_text(url: str) -> dict:
    """
    Scrape a web article and extract the main content.
    Returns dict with 'title', 'text', 'url', 'domain'.
    """
    print(f"Fetching article: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL: {e}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract title
    title = ""
    if soup.title:
        title = soup.title.string or ""
    # Try Open Graph title as fallback
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        title = og_title['content']
    # Try h1 as another fallback
    if not title:
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
    
    # Remove unwanted elements
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 
                     'form', 'iframe', 'noscript', 'svg', 'button']):
        tag.decompose()
    
    # Try to find the main article content
    article_text = ""
    
    # Method 1: Look for article tag
    article = soup.find('article')
    if article:
        article_text = article.get_text(separator='\n', strip=True)
    
    # Method 2: Look for main content div
    if not article_text or len(article_text) < 500:
        main = soup.find('main') or soup.find('div', class_=re.compile(r'(content|article|post|entry)', re.I))
        if main:
            article_text = main.get_text(separator='\n', strip=True)
    
    # Method 3: Fall back to body with cleanup
    if not article_text or len(article_text) < 500:
        body = soup.find('body')
        if body:
            # Get all paragraphs
            paragraphs = body.find_all('p')
            article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50)
    
    # Clean up text
    article_text = re.sub(r'\n{3,}', '\n\n', article_text)
    article_text = re.sub(r' {2,}', ' ', article_text)
    
    # Extract domain for source attribution
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    
    print(f"  Title: {title[:60]}...")
    print(f"  Extracted {len(article_text):,} characters")
    
    return {
        'title': title.strip(),
        'text': article_text.strip(),
        'url': url,
        'domain': domain
    }


def add_article_to_knowledge_base(url: str) -> int:
    """
    Add a single web article to the existing knowledge base.
    Returns number of chunks added.
    """
    print("=" * 60)
    print("ARTICLE INGESTION")
    print("=" * 60)
    
    # Extract article content
    article = extract_article_text(url)
    
    if not article['text'] or len(article['text']) < 100:
        print("ERROR: Could not extract meaningful content from the article.")
        return 0
    
    # Initialize ChromaDB (get existing collection)
    print(f"\nConnecting to ChromaDB at: {DB_DIR}")
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(DB_DIR))
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    
    # Get or create collection
    try:
        collection = client.get_collection(COLLECTION_NAME, embedding_function=embedding_fn)
        print(f"Using existing collection: {COLLECTION_NAME}")
    except:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn,
            metadata={"description": "Historical sources for counter-extremism education"}
        )
        print(f"Created new collection: {COLLECTION_NAME}")
    
    # Create source name from title and domain
    safe_title = _safe_filename(article['title'][:50]) if article['title'] else "untitled"
    source_name = f"[Article] {safe_title} ({article['domain']})"
    
    # Chunk the article text
    chunks = chunk_text(article['text'], source_name, source_type="article")
    print(f"  Created {len(chunks)} chunks")
    
    # Check for duplicates (by URL in metadata)
    # First, let's add URL to metadata
    for chunk in chunks:
        chunk['url'] = article['url']
    
    # Add to ChromaDB
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{
                "source": c["source"], 
                "source_type": c["source_type"],
                "url": c["url"],
                "chunk_index": c["chunk_index"]
            } for c in batch]
        )
    
    print("\n" + "=" * 60)
    print("ARTICLE ADDED")
    print("=" * 60)
    print(f"Title: {article['title']}")
    print(f"URL: {article['url']}")
    print(f"Chunks added: {len(chunks)}")
    
    return len(chunks)


def ingest_books(sync_drive: bool = False, drive_folder_id: str | None = None, drive_dest_dir: Path = DEFAULT_DRIVE_SYNC_DIR):
    """Main function to ingest all PDFs into ChromaDB."""
    print("=" * 60)
    print("BOOK INGESTION - Building Knowledge Base")
    print("=" * 60)

    # Optional: sync PDFs from Google Drive first
    if sync_drive:
        folder_id = drive_folder_id or os.environ.get("DRIVE_FOLDER_ID")
        if not folder_id:
            print("ERROR: Drive sync requested but no folder ID provided.")
            print("Provide --drive-folder-id <FOLDER_ID> or set env var DRIVE_FOLDER_ID.")
            return
        try:
            sync_drive_pdfs(folder_id=folder_id, dest_dir=drive_dest_dir)
        except Exception as e:
            print(f"ERROR: Drive sync failed: {e}")
            return
    
    # Check for books
    if not BOOKS_DIR.exists():
        print(f"Creating books directory: {BOOKS_DIR}")
        BOOKS_DIR.mkdir(parents=True)
        print("Please add PDF files to the books folder and run again.")
        return
    
    pdf_files = list(BOOKS_DIR.glob("*.pdf"))
    # Include synced Drive PDFs if present
    if drive_dest_dir.exists():
        pdf_files.extend(list(drive_dest_dir.glob("*.pdf")))

    # Deduplicate by full path
    pdf_files = sorted({p.resolve() for p in pdf_files})
    if not pdf_files:
        print(f"No PDF files found in {BOOKS_DIR}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        print(f"  - {pdf.name} ({pdf.stat().st_size / 1024:.1f} KB)")
    
    # Initialize ChromaDB
    print(f"\nInitializing ChromaDB at: {DB_DIR}")
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(DB_DIR))
    
    # Use default embedding function (all-MiniLM-L6-v2)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    
    # Delete existing collection if exists (fresh start)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection: {COLLECTION_NAME}")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "Historical sources for counter-extremism education"}
    )
    
    # Process each PDF
    total_chunks = 0
    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        
        # Extract text
        text = extract_text_from_pdf(pdf_path)
        
        # Clean up text
        text = ' '.join(text.split())  # Normalize whitespace
        
        # Chunk text
        source_name = f"[Book] {pdf_path.stem}"  # filename without extension
        chunks = chunk_text(text, source_name, source_type="book")
        print(f"  Created {len(chunks)} chunks")
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"], "source_type": c.get("source_type", "book"), "chunk_index": c["chunk_index"]} for c in batch]
            )
            print(f"    Added batch {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}")
        
        total_chunks += len(chunks)
    
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total chunks indexed: {total_chunks}")
    print(f"Knowledge base location: {DB_DIR}")
    print(f"Collection name: {COLLECTION_NAME}")
    print("\nYou can now run the Topic Expert Agent!")


def test_query(query: str):
    """Test a query against the knowledge base."""
    print(f"\nTest Query: '{query}'")
    print("-" * 40)
    
    client = chromadb.PersistentClient(path=str(DB_DIR))
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_collection(COLLECTION_NAME, embedding_function=embedding_fn)
    
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\nResult {i + 1} (from {metadata['source']}):")
        print(f"  {doc[:300]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDF books and web articles into a ChromaDB knowledge base.")
    parser.add_argument("--books-dir", default=str(BOOKS_DIR), help="Local books directory (default: crewai_demo/books).")
    parser.add_argument("--sync-drive", action="store_true", help="Sync PDFs from a Google Drive folder before ingesting.")
    parser.add_argument("--drive-folder-id", default=None, help="Google Drive folder ID that contains your PDFs.")
    parser.add_argument("--drive-dest-dir", default=str(DEFAULT_DRIVE_SYNC_DIR), help="Where to download Drive PDFs locally.")
    parser.add_argument("--add-article", default=None, metavar="URL", help="Add a web article to the knowledge base by URL.")
    parser.add_argument("command", nargs="*", help="Optional: use 'test <query>' to test the knowledge base.")

    args = parser.parse_args()

    # Apply books dir override
    BOOKS_DIR = Path(args.books_dir)

    drive_dest = Path(args.drive_dest_dir)

    if args.add_article:
        # Add a single article
        add_article_to_knowledge_base(args.add_article)
    elif args.command and args.command[0] == "test":
        test_query(" ".join(args.command[1:]) if len(args.command) > 1 else "What is jihad?")
    else:
        ingest_books(sync_drive=args.sync_drive, drive_folder_id=args.drive_folder_id, drive_dest_dir=drive_dest)

