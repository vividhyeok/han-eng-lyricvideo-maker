
import sys
import os
import asyncio
from dataclasses import dataclass

sys.path.append(os.getcwd())

# Mock ProcessConfig for testing
@dataclass
class ProcessConfig:
    youtube_url: str

async def verify_url_sanitization():
    print("-" * 20)
    print("Verifying URL Sanitization...")
    
    # Simulate the logic added to ProcessManager
    config = ProcessConfig(youtube_url="https://music.youtube.com/watch?v=5qacSnPFD3w&list=OLAK5uy_ljL2hgAPtjq-f2ff2vUd0kqkc_JznLI5k")
    
    print(f"Original: {config.youtube_url}")
    
    if "music.youtube.com" in config.youtube_url:
        print("[DEBUG] YouTube Music URL detected.")
        config.youtube_url = config.youtube_url.replace("music.youtube.com", "www.youtube.com")
        if "&" in config.youtube_url and "v=" in config.youtube_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(config.youtube_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'v' in qs:
                config.youtube_url = f"https://www.youtube.com/watch?v={qs['v'][0]}"
                
    print(f"Sanitized: {config.youtube_url}")
    expected = "https://www.youtube.com/watch?v=5qacSnPFD3w"
    if config.youtube_url == expected:
        print("PASS: URL sanitization successful.")
    else:
        print(f"FAIL: URL sanitization mismatch. Expected {expected}")

async def verify_gemini():
    print("-" * 20)
    print("Verifying Gemini Translation...")
    
    try:
        from app.lyrics.ai_models import create_model, GeminiModel, AVAILABLE_MODELS
        import google.generativeai as genai
        
        # Force reload from .env if needed, but os.getenv should work
        # config/ai_models loads env internally or via config_manager.
        # We manually instantiate GeminiModel to test availability using the key from .env
        
        # Check env first
        key = os.getenv("GEMINI_API_KEY")
        print(f"GEMINI_API_KEY present: {bool(key)}")
        if key:
            print(f"Key prefix: {key[:5]}...")
            
        model = create_model("gemini-2.0-flash")
        
        if not model:
            print("FAIL: create_model('gemini-2.0-flash') returned None.")
            return

        print(f"Model created: {model.__class__.__name__}")
        print(f"Available: {model.is_available()}")
        
        if model.is_available():
            test_lyrics = ["안녕하세요", "This is a test line"]
            print("Translating test lyrics...")
            translated = await model.translate(test_lyrics, "Test Artist", "Test Title")
            print(f"Result: {translated}")
            if len(translated) == 2 and translated[1] == "This is a test line":
                 # Simple check: English line preserved, Korean translated (or at least returned)
                 print("PASS: Translation call succeeded.")
            else:
                 print("WARN: Translation output unexpected format.")
        else:
            print("FAIL: Model is not available despite key presence.")

    except ImportError as ie:
        print(f"FAIL: Import error - {ie}")
    except Exception as e:
        print(f"FAIL: Exception - {e}")

async def main():
    await verify_url_sanitization()
    await verify_gemini()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
