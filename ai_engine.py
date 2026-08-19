import os
import json
import google.generativeai as genai
import requests

CONFIG_DIR = "local_shipper_data"
CONFIG_FILE = os.path.join(CONFIG_DIR, "gemini_config.json")
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def save_gemini_api_key(api_key):
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": api_key.strip()}, f, indent=4)
        return True
    except Exception as e:
        return False

def load_gemini_api_key():
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("gemini_api_key", "")
        except:
            pass
    return ""

def push_all_to_sheet(shippers_json_payload):
    """शिपर का डेटा और रूल्स गूगल शीट (Shipper_JSON_Database) पर सेव करने के लिए"""
    try:
        payload = {
            "action": "save_shipper_json",
            "shippers_data": shippers_json_payload
        }
        response = requests.post(WEB_APP_URL, data=json.dumps(payload), timeout=120)
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False

def ask_local_ai(messages):
    """
    Google Gemini API के माध्यम से डेटा एक्सट्रैक्ट करने का सुपर-फास्ट इंजन।
    """
    api_key = load_gemini_api_key()
    if not api_key:
        return "❌ Error: Gemini API Key सेट नहीं है। कृपया UI में जाकर अपनी API Key दर्ज करें।"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        full_prompt = ""
        if isinstance(messages, list):
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                full_prompt += f"\n[{role.upper()}]: {content}\n"
        else:
            full_prompt = str(messages)

        response = model.generate_content(full_prompt)
        if response and response.text:
            return response.text.strip()
        else:
            return "❌ Error: Gemini से खाली रिस्पॉन्स मिला।"
    except Exception as e:
        return f"❌ Gemini API Error: {str(e)}"
