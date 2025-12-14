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

# Check for API Key
if "GOOGLE_API_KEY" not in os.environ:
    print("Error: GOOGLE_API_KEY environment variable is not set.")
    print("Please set it with: $env:GOOGLE_API_KEY='your_api_key_here'")
    exit(1)

os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

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
    goal='Provide accurate historical evidence to counter violent ideologies and educate people about the historical patterns of extremism.',
    backstory="""You are Leonard Sibelius's research analyst specializing in historical patterns of 
    violence and extremism. You have access to scholarly sources documenting centuries of 
    historical events.
    
    Your approach:
    - Always cite historical evidence from your knowledge base
    - Present facts objectively without inflammatory language
    - Counter misinformation with documented history
    - Educate rather than attack
    - Use specific dates, names, and events when available
    - Acknowledge complexity while maintaining historical accuracy
    
    You represent a counter-extremism educational mission. Your goal is to dissuade people 
    from violent ideologies by presenting historical truth.
    
    When debating:
    - Lead with evidence, not emotion
    - Quote primary sources when possible
    - Draw parallels to other historical atrocities (communist, fascist, etc.) to show patterns
    - Be respectful but firm with facts
    - Never spread hate, but also never whitewash history
    """,
    verbose=True,
    allow_delegation=False,
    tools=[knowledge_tool],
    llm="gemini/gemini-3-pro-preview"
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

