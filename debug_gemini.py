
import os
import sys

sys.path.append(os.getcwd())

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Environment variables loaded.")
    key = os.getenv("GEMINI_API_KEY")
    print(f"Key loaded: {bool(key)}")
    
    import google.generativeai as genai
    print("Module google.generativeai imported successfully.")
    
    if key:
        print("Configuring genai...")
        genai.configure(api_key=key)
        print("Configuration done.")
        
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            print("GenerativeModel instantiated.")
            
            response = model.generate_content("Hello, can you hear me?")
            print(f"Test generation response: {response.text}")
            
        except Exception as api_e:
            print(f"API Call failed: {api_e}")
            
    else:
        print("No GEMINI_API_KEY found.")

except ImportError:
    print("Failed to import google.generativeai")
except Exception as e:
    print(f"General error: {e}")
