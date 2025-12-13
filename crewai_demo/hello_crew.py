import os
from crewai import Agent, Task, Crew

# Check for API Key
if "GOOGLE_API_KEY" not in os.environ:
    print("❌ Error: GOOGLE_API_KEY environment variable is not set.")
    print("Please set it with: $env:GOOGLE_API_KEY='your_api_key_here'")
    exit(1)

# Set the specific environment variable that LiteLLM looks for
os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

# Define the model string (LiteLLM format: provider/model)
# Using "gemini/gemini-pro" as it is the most stable identifier
my_llm = "gemini/gemini-3-pro-preview"

# 1. Define Agents
researcher = Agent(
    role='Senior Research Analyst',
    goal='Uncover cutting-edge developments in AI Agents',
    backstory="""You work at a leading tech think tank.
    Your expertise lies in identifying emerging trends.""",
    verbose=True,
    allow_delegation=False,
    llm=my_llm
)

writer = Agent(
    role='Tech Content Strategist',
    goal='Craft compelling content on tech advancements',
    backstory="""You are a renowned Content Strategist.
    You transform complex concepts into compelling narratives.""",
    verbose=True,
    allow_delegation=True,
    llm=my_llm
)

# 2. Define Tasks
task1 = Task(
    description="""Find 3 key trends in AI Agents for 2024.""",
    expected_output="Bullet point list of 3 trends",
    agent=researcher
)

task2 = Task(
    description="""Write a short paragraph summarizing these trends.""",
    expected_output="A 4-sentence paragraph",
    agent=writer
)

# 3. Instantiate Crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    verbose=True,
)

# 4. Kickoff!
print("🚀 Starting the Crew with Gemini Pro (Native)...")
result = crew.kickoff()

print("\n\n########################")
print("## Here is the result ##")
print("########################\n")
print(result)
