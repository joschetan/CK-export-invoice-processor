import streamlit as st
import requests
import json
import base64
from io import BytesIO
import openpyxl

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

def get_val_case_insensitive(d, *keys, default=""):
    if not isinstance(d, dict):
        return default
    d_lower = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        if str(k).lower() in d_lower:
            val = d_lower[str(k).lower()]
            if val is not None:
                return str(val).strip()
    return default

def fetch_all_from_sheet():
    """गूगल शीट से सारे रूल्स और एक्सेल टेम्पलेट बाइट्स खींचकर लाता है"""
    try:
        response = requests.get(f"{WEB_APP_URL}?action=get_data", timeout=15)
        if response.status_code == 200:
            res_text = response.text.strip()
            if res_text.startswith("<"):
                return None, None
            return response.json()
    except Exception:
        pass
    return None

def push_all_to_sheet(rules_payload, files_payload):
    """सारे रूल्स और एक्सेल बेस64 चंक्स को गूगल शीट पर सेव करता है"""
    try:
        payload = {
            "action": "save_all",
            "rules": rules_payload,
            "files": files_payload
        }
        response = requests.post(WEB_APP_URL, data=json.dumps(payload), timeout=30)
        return response.status_code == 200
    except Exception:
        return False

def load_template_from_sheet(shipper_name):
    """गूगल शीट से शिपर की बेस64 फाइल को वापस सही openpyxl Workbook में बदलता है"""
    data = fetch_all_from_sheet()
    if not data:
        return None
    
    files_list = data.get("files", [])
    for f_row in files_list:
        s_name = get_val_case_insensitive(f_row, "ShipperName", "shipper")
        target_key = "WELSPUN GLOBAL BRANDS LIMITED" if "welspun" in s_name.lower() else s_name
        
        if target_key.lower() == shipper_name.lower():
            b64_str = get_val_case_insensitive(f_row, "FileBase64", "base64", "file")
            if b64_str and len(b64_str.strip()) > 0:
                try:
                    clean_b64 = b64_str.lstrip("'").strip().replace(" ", "+")
                    missing_padding = len(clean_b64) % 4
                    if missing_padding:
                        clean_b64 += '=' * (4 - missing_padding)
                    
                    decoded_bytes = base64.b64decode(clean_b64)
                    if decoded_bytes.startswith(b'PK'):
                        return openpyxl.load_workbook(BytesIO(decoded_bytes))
                except Exception:
                    pass
    return None
