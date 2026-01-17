
import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ API Key missing")
    exit(1)

genai.configure(api_key=api_key)

async def test_rag_formats():
    print("🧪 Starting Gemini 2.5 RAG Diagnostic...")
    
    # 1. Create a dummy file
    with open("test_doc.txt", "w") as f:
        f.write("This is a test document for Gemini RAG diagnostics.")
    
    try:
        # 2. Upload file
        print("📤 Uploading test file...")
        uploaded_file = genai.upload_file("test_doc.txt", display_name="Debug_Doc")
        print(f"✅ File uploaded: {uploaded_file.name} (State: {uploaded_file.state.name})")
        
        # Wait for processing
        while uploaded_file.state.name == "PROCESSING":
            print("⏳ Waiting for file processing...")
            await asyncio.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        if uploaded_file.state.name != "ACTIVE":
            print(f"❌ File failed processing: {uploaded_file.state.name}")
            return

        # 3. Test Models
        models_to_test = ["models/gemini-2.5-flash-lite", "models/gemini-1.5-flash"]
        
        for model_name in models_to_test:
            print(f"\n🤖 Testing Model: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            # Format A: List [file, text] (Current Implementation)
            print("   👉 Testing Format A: [file, text]")
            try:
                response = await model.generate_content_async([uploaded_file, "What is in this document?"])
                print(f"      ✅ Success! Response: {response.text[:50]}...")
            except Exception as e:
                print(f"      ❌ Failed: {e}")

            # Format B:  Explicit Content Dict (Proposed Fix)
            print("   👉 Testing Format B: content=[file, text]")
            try:
                # Constructing parts manually if needed, but let's test the dict first
                response = await model.generate_content_async(
                    contents=[uploaded_file, "Summarize this."]
                )
                print(f"      ✅ Success! Response: {response.text[:50]}...")
            except Exception as e:
                print(f"      ❌ Failed: {e}")

        # Cleanup
        print("\n🧹 Cleaning up...")
        genai.delete_file(uploaded_file.name)
        os.remove("test_doc.txt")
        print("✨ Done.")
        
    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_rag_formats())
