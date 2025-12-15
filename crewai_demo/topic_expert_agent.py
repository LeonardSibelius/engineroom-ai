"""
Topic Expert Agent
Uses RAG to debate topics using knowledge from ingested books.
Designed for counter-extremism education and historical accuracy.
"""

import os
import sys
from pathlib import Path
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
import chromadb
from chromadb.utils import embedding_functions

# Check for API Key - prefer Anthropic (Claude), fall back to Google (Gemini)
if "ANTHROPIC_API_KEY" in os.environ:
    LLM_MODEL = "anthropic/claude-sonnet-4-20250514"
    print("Using Claude (Anthropic) as LLM")
elif "GOOGLE_API_KEY" in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
    LLM_MODEL = "gemini/gemini-3-pro-preview"
    print("Using Gemini (Google) as LLM")
else:
    print("Error: No API key found.")
    print("Set ANTHROPIC_API_KEY or GOOGLE_API_KEY")
    exit(1)

# Configuration
DB_DIR = Path(__file__).parent / "knowledge_db"
COLLECTION_NAME = "historical_sources"


class KnowledgeSearchTool(BaseTool):
    name: str = "Search Historical Sources"
    description: str = """Searches the knowledge base of historical books for relevant information.
    Use this to find facts, quotes, and historical evidence to support arguments.
    Input should be a search query describing what information you need."""

    def _run(self, query: str) -> str:
        try:
            client = chromadb.PersistentClient(path=str(DB_DIR))
            embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            collection = client.get_collection(COLLECTION_NAME, embedding_function=embedding_fn)
            
            results = collection.query(
                query_texts=[query],
                n_results=5
            )
            
            if not results['documents'][0]:
                return "No relevant information found in the knowledge base."
            
            output = "RELEVANT HISTORICAL EVIDENCE:\n\n"
            for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
                source = metadata.get('source', 'Unknown')
                output += f"[Source {i+1}: {source}]\n{doc}\n\n"
            
            return output
            
        except Exception as e:
            return f"Error searching knowledge base: {e}"


# Initialize tools
knowledge_tool = KnowledgeSearchTool()

# Define the Topic Expert Agent
topic_expert = Agent(
    role='Historical Evidence Analyst for Leonard Sibelius',
    goal='Provide direct, factual, well-sourced content about historical patterns of ideological conquest and resistance.',
    backstory="""You are Leonard Sibelius's research analyst. You specialize in documented historical 
    patterns of religious and ideological conquest, particularly Islamic expansion, dhimmitude, 
    and modern parallels.
    
    Your knowledge base contains scholarly sources including:
    - Robert Spencer's "The History of Jihad"
    - Bat Ye'or's "Islam and Dhimmitude"  
    - Sam Solomon's "Modern Day Trojan Horse: Al-Hijra"
    
    YOUR APPROACH - BE DIRECT:
    - Search the knowledge base and CITE SPECIFIC PASSAGES
    - State historical facts plainly - do NOT hedge or apologize
    - Do NOT "both sides" the issue or add unnecessary caveats
    - Do NOT dismiss the user's premise as a "myth" or "false"
    - Use specific dates, names, events, and quotes from sources
    - Draw clear parallels between historical and modern events
    - The goal is EDUCATION through documented evidence, not "balance"
    
    You are writing for an audience that wants the unvarnished historical truth, 
    not a sanitized version designed to avoid offense.
    
    When writing:
    - Lead with the strongest evidence from sources
    - Quote directly when possible
    - Be concise and punchy - this is for social media
    - End with a call to learn more or a thought-provoking question
    """,
    verbose=True,
    allow_delegation=False,
    tools=[knowledge_tool],
    llm=LLM_MODEL
)


def create_debate_response(topic: str, opponent_argument: str = None) -> str:
    """Create a debate response on the given topic."""
    
    if opponent_argument:
        task_description = f"""
        Someone has made the following argument: "{opponent_argument}"
        
        Your task:
        1. Search the historical sources for relevant evidence on this topic
        2. Craft a factual, educational response that addresses their argument
        3. Include specific historical evidence (dates, events, figures)
        4. Keep the response suitable for social media (under 280 characters for a tweet, 
           or longer for a thread - indicate if it should be a thread)
        5. Be educational, not inflammatory
        6. End with a thought-provoking question or fact
        """
    else:
        task_description = f"""
        Create an educational post about: {topic}
        
        Your task:
        1. Search the historical sources for interesting, lesser-known facts
        2. Craft an engaging, educational post about this topic
        3. Include specific historical evidence (dates, events, figures)
        4. Keep it suitable for social media
        5. Be educational, not inflammatory
        6. End with something that encourages further learning
        """
    
    debate_task = Task(
        description=task_description,
        expected_output="A well-researched response with historical citations, formatted for social media.",
        agent=topic_expert
    )
    
    crew = Crew(
        agents=[topic_expert],
        tasks=[debate_task],
        verbose=True,
        process=Process.sequential
    )
    
    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    print("=" * 60)
    print("TOPIC EXPERT AGENT")
    print("Counter-Extremism Education")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # Command line mode
        topic = " ".join(sys.argv[1:])
        print(f"\nTopic: {topic}\n")
        result = create_debate_response(topic)
    else:
        # Interactive mode
        print("\nModes:")
        print("1. Create educational post on a topic")
        print("2. Respond to an argument")
        
        mode = input("\nSelect mode (1 or 2): ").strip()
        
        if mode == "1":
            topic = input("Enter topic: ").strip()
            result = create_debate_response(topic)
        elif mode == "2":
            topic = input("Enter the topic area: ").strip()
            argument = input("Enter the argument to respond to: ").strip()
            result = create_debate_response(topic, argument)
        else:
            print("Invalid mode")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(result)

