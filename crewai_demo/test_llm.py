import os
from langchain_google_genai import ChatGoogleGenerativeAI

# Check for API Key
if "GOOGLE_API_KEY" not in os.environ:
    print("❌ Error: GOOGLE_API_KEY environment variable is not set.")
    exit(1)

print(f"🔑 API Key found: {os.environ['GOOGLE_API_KEY'][:5]}... (masked)")

try:
    print("🤖 Connecting to Gemini-1.5-Pro...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        verbose=True,
        temperature=0.7,
        google_api_key=os.environ["GOOGLE_API_KEY"]
    )
    
    response = llm.invoke("Say 'Hello from Gemini!' if you can hear me.")
    print("\n✅ SUCCESS!")
    print(response.content)

except Exception as e:
    print("\n❌ FAILURE!")
    print(e)
