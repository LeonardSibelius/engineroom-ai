import os
import google.generativeai as genai

# Check for API Key
if "GOOGLE_API_KEY" not in os.environ:
    print("❌ Error: GOOGLE_API_KEY environment variable is not set.")
    exit(1)

print(f"🔑 API Key found: {os.environ['GOOGLE_API_KEY'][:5]}... (masked)")

# Configure the SDK
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

print("🤖 Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"   - {m.name}")
except Exception as e:
    print(f"❌ Error listing models: {e}")

print("\n🤖 Testing generation with 'gemini-1.5-flash'...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Say 'Hello from Direct API!'")
    print("\n✅ SUCCESS!")
    print(response.text)
except Exception as e:
    print(f"\n❌ Failed with gemini-1.5-flash: {e}")

    print("\n🤖 Testing generation with 'gemini-pro'...")
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'Hello from Direct API!'")
        print("\n✅ SUCCESS!")
        print(response.text)
    except Exception as e:
        print(f"\n❌ Failed with gemini-pro: {e}")
