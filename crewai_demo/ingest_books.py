"""
Book Ingestion Script
Converts PDF books into a searchable knowledge base using ChromaDB.
"""

import os
import sys
from pathlib import Path

# Check for required packages
try:
    import chromadb
    from chromadb.utils import embedding_functions
    import pymupdf  # PyMuPDF for PDF extraction
except ImportError as e:
    print(f"Missing package: {e}")
    print("Install with: pip install chromadb pymupdf")
    sys.exit(1)

# Configuration
BOOKS_DIR = Path(__file__).parent / "books"
DB_DIR = Path(__file__).parent / "knowledge_db"
COLLECTION_NAME = "historical_sources"
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    print(f"  Extracting text from: {pdf_path.name}")
    
    doc = pymupdf.open(pdf_path)
    text = ""
    page_count = len(doc)
    
    for page_num, page in enumerate(doc):
        text += page.get_text()
        if (page_num + 1) % 50 == 0:
            print(f"    Processed {page_num + 1} pages...")
    
    doc.close()
    print(f"  Extracted {len(text):,} characters from {page_count} pages")
    return text


def chunk_text(text: str, source_name: str) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk_text.rfind('.')
            if last_period > CHUNK_SIZE // 2:
                chunk_text = chunk_text[:last_period + 1]
                end = start + last_period + 1
        
        chunks.append({
            "id": f"{source_name}_{chunk_id}",
            "text": chunk_text.strip(),
            "source": source_name,
            "chunk_index": chunk_id
        })
        
        chunk_id += 1
        start = end - CHUNK_OVERLAP
    
    return chunks


def ingest_books():
    """Main function to ingest all PDFs into ChromaDB."""
    print("=" * 60)
    print("BOOK INGESTION - Building Knowledge Base")
    print("=" * 60)
    
    # Check for books
    if not BOOKS_DIR.exists():
        print(f"Creating books directory: {BOOKS_DIR}")
        BOOKS_DIR.mkdir(parents=True)
        print("Please add PDF files to the books folder and run again.")
        return
    
    pdf_files = list(BOOKS_DIR.glob("*.pdf"))
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
        source_name = pdf_path.stem  # filename without extension
        chunks = chunk_text(text, source_name)
        print(f"  Created {len(chunks)} chunks")
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"], "chunk_index": c["chunk_index"]} for c in batch]
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
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_query(" ".join(sys.argv[2:]) if len(sys.argv) > 2 else "What is jihad?")
    else:
        ingest_books()

