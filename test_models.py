
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Try loading from parent dir or current
load_dotenv('../.env')
if not os.getenv("gemini_api"):
    load_dotenv('.env')

api_key = os.getenv("gemini_api")
genai.configure(api_key=api_key)

candidates = [
    "gemini-1.5-flash", 
    "gemini-1.5-flash-latest", 
    "gemini-1.5-flash-001", 
    "gemini-1.5-flash-002",
    "gemini-flash-latest",
    "gemini-2.0-flash-exp",
    "gemini-exp-1121"
]


with open('model_test.log', 'w', encoding='utf-8') as f:
    f.write(f"Testing {len(candidates)} candidates...\n")
    for model in candidates:
        try:
            m = genai.GenerativeModel(model)
            resp = m.generate_content("Hello")
            f.write(f"✅ SUCCESS: {model}\n")
            print(f"✅ SUCCESS: {model}")
        except Exception as e:
            f.write(f"❌ FAILED: {model} - {e}\n")
            print(f"❌ FAILED: {model}")
