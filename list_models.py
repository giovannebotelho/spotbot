
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Try loading from parent dir or current
load_dotenv('../.env')
if not os.getenv("gemini_api"):
    load_dotenv('.env')

api_key = os.getenv("gemini_api")

if not api_key:
    print("Error: gemini_api key not found in environment variables.")
else:
    genai.configure(api_key=api_key)
    print("Listing available models...")
    try:
        found = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
                found = True
        if not found:
            print("No models found supporting generateContent.")
    except Exception as e:
        print(f"Error listing models: {e}")
