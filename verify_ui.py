
import sys
import os
import asyncio

sys.path.append(os.getcwd())

# Force load Env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def verify_ui_population():
    print("-" * 20)
    print("Verifying UI Model List Population...")
    
    try:
        from app.lyrics.ai_models import get_available_models
        from app.config.config_manager import get_config
        
        # 1. Check Available Models (What UI sees)
        available = get_available_models()
        print(f"Available Models: {available}")
        
        has_gemini = any("gemini" in k for k in available.keys())
        if has_gemini:
             print("PASS: Gemini is available in the list.")
        else:
             print("FAIL: Gemini is NOT in the list (User cannot select it).")

        # 2. Check Config Saving
        from app.config.paths import CONFIG_FILE_PATH
        config = get_config()
        original_model = config.get_translation_model()
        print(f"Original Model: {original_model}")
        
        # Simulate User Selection
        test_model = "gemini-2.0-flash" 
        print(f"Simulating selection of: {test_model}")
        config.set_translation_model(test_model)
        
        # Reload to verify save
        new_config = get_config()
        # Force reload from file logic if needed, but get_config singleton might mask it.
        # Let's inspect the file directly
        import json
        with open(CONFIG_FILE_PATH, 'r') as f:
             saved_data = json.load(f)
             saved_model = saved_data.get("translation_model")
             print(f"Saved Config File Model: {saved_model}")
             
        if saved_model == test_model:
             print("PASS: Settings successfully saved to file.")
        else:
             print("FAIL: Settings NOT saved to file.")
             
        # Cleanup (restore original)
        config.set_translation_model(original_model)

    except Exception as e:
        print(f"FAIL: UI Verification Logic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_ui_population()
