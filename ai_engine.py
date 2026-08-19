import os
import json
import base64
import google.generativeai as genai
import requests

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

def save_gemini_api_key_to_sheet(api_key):
    """Gemini API Key को सीधे Google Sheet पर सेव करने के लिए"""
    try:
        payload = {
            "action": "save_api_key",
            "api_key": api_key.strip()
        }
        response = requests.post(WEB_APP_URL, data=json.dumps(payload), timeout=30)
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False

def load_gemini_api_key_from_sheet():
    """Google Sheet से सेव की गई Gemini API Key फेच करने के लिए"""
    try:
        response = requests.get(WEB_APP_URL, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                return data.get("api_key", "")
    except Exception:
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

def create_new_parser_file_on_github(parser_name, github_token, repo_owner="joschetan", repo_name="CK-export-invoice-processor"):
    """
    GitHub API का उपयोग करके सीधे रिपॉजिटरी में एक नई ब्लैंक पार्सर फाइल (.py) क्रिएट करता है।
    """
    clean_name = str(parser_name).strip().lower()
    if not clean_name.endswith(".py"):
        clean_name += ".py"
    if not clean_name.startswith("parser_"):
        clean_name = f"parser_{clean_name}"
        
    file_path = clean_name  
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    initial_content = f"# Parser Rule File: {file_path}\n# Created automatically by CK Export Invoice Pro\n\n"
    encoded_content = base64.b64encode(initial_content.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": f"Create new parser rule file: {file_path}",
        "content": encoded_content,
        "branch": "main"
    }
    
    try:
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [201, 200]:
            return True, f"सफलता! फाइल '{file_path}' GitHub पर बन गई है।"
        else:
            err_msg = response.json().get('message', 'Unknown error')
            return False, f"GitHub Error: {err_msg}"
    except Exception as e:
        return False, f"Connection Error: {str(e)}"

def ask_local_ai(messages):
    """
    Google Gemini API के माध्यम से डेटा एक्सट्रैक्ट करने का सुपर-फास्ट इंजन।
    """
    api_key = load_gemini_api_key_from_sheet()
    if not api_key:
        return "❌ Error: Gemini API Key सेट नहीं है। कृपया UI में जाकर अपनी API Key दर्ज करें।"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.6-flash")
        
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
