
import sys
import os
import asyncio
import traceback

sys.path.append(os.getcwd())

# Force load Env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[DEBUG] Env loaded")
except ImportError:
    pass

async def verify_runtime_translation():
    print("-" * 20)
    print("Verifying Runtime Translation Flow...")
    
    try:
        from app.config.config_manager import get_config, ConfigManager
        
        # 1. Check Config
        config = get_config()
        model_id = config.get_translation_model()
        print(f"[VERIFY] Configured Model: {model_id}")
        
        # 2. Force set to gemini if it's default to test correct flow
        if model_id == "gpt-4o-mini":
             print("[VERIFY] Current config is gpt-4o-mini. Switching to gemini-2.0-flash for this test...")
             config.set_translation_model("gemini-2.0-flash")
             model_id = config.get_translation_model()
             print(f"[VERIFY] New Configured Model: {model_id}")

        # 3. Call Handler
        from app.lyrics.openai_handler import translate_lyrics
        
        test_lyrics = ["안녕하세요", "테스트입니다", "Hello"]
        print(f"[VERIFY] Input: {test_lyrics}")
        
        result = await translate_lyrics(test_lyrics)
        print(f"[VERIFY] Output: {result}")
        
        if result and len(result) == 3 and result[0] != "안녕하세요":
             print("[PASS] Translation successful (Output changed from input).")
        else:
             print("[FAIL] Translation returned identical/empty output.")

    except Exception as e:
        print(f"[FAIL] Runtime verification failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_runtime_translation())
