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

@st.cache_data(show_spinner=False)
def fetch_all_from_sheet():
    """गूगल शीट से सारे रूल्स और टेम्पलेट खींचकर लाता है (कैश्ड)"""
    try:
        response = requests.get(f"{WEB_APP_URL}?action=get_data", timeout=15)
        if response.status_code == 200:
            res_text = response.text.strip()
            if res_text.startswith("<"):
                return None
            return response.json()
    except Exception:
        pass
    return None

def clear_sheet_cache():
    """एडमिन द्वारा सेव करने पर कैच को तुरंत साफ़ करने के लिए"""
    fetch_all_from_sheet.clear()

def push_all_to_sheet(rules_payload, files_payload):
    """सारे रूल्स और Base64 डेटा को गूगल शीट पर सेव करता है"""
    try:
        # 🎯 यदि बेस64 बहुत बड़ा है, तो उसे छोटे टुकड़ों में बांटकर भेजना ताकि शीट में एरर न आए
        processed_files = []
        for item in files_payload:
            shipper = item.get("ShipperName", "")
            b64_data = item.get("FileBase64", "")
            
            # अगर डेटा डिक्शनरी या लिस्ट के रूप में आ रहा है तो उसे जोड़ लें
            if isinstance(b64_data, list):
                b64_data = "".join(str(x) for x in b64_data)
                
            chunk_size = 40000  # हर टुकड़े का साइज सुरक्षित सीमा में
            chunks = [b64_data[i:i+chunk_size] for i in range(0, len(b64_data), chunk_size)]
            
            file_entry = {"ShipperName": shipper, "TotalChunks": len(chunks)}
            for idx, chunk in enumerate(chunks):
                file_entry[f"Chunk_{idx}"] = chunk
            processed_files.append(file_entry)

        payload = {
            "action": "save_all",
            "rules": rules_payload,
            "files": processed_files
        }
        response = requests.post(WEB_APP_URL, data=json.dumps(payload), timeout=30)
        if response.status_code == 200:
            clear_sheet_cache()
            return True
        return False
    except Exception:
        return False

def load_template_bytes_from_sheet(shipper_name):
    """गूगल शीट से टूटे हुए टुकड़ों को आपस में जोड़कर बाइट्स लौटाता है"""
    data = fetch_all_from_sheet()
    if not data:
        return None
    
    files_list = data.get("files", [])
    for f_row in files_list:
        s_name = get_val_case_insensitive(f_row, "ShipperName", "shipper")
        
        if s_name.lower().strip() == shipper_name.lower().strip():
            # सभी टुकड़ों को ढूंढकर आपस में जोड़ना
            full_b64 = ""
            
            # नया तरीका (चंक आधारित)
            total_chunks = f_row.get("TotalChunks", 1)
            try:
                total_chunks = int(total_chunks)
            except:
                total_chunks = 1
                
            if total_chunks > 1:
                for idx in range(total_chunks):
                    chunk_val = f_row.get(f"Chunk_{idx}", "")
                    if chunk_val:
                        full_b64 += str(chunk_val)
            else:
                # पुराना तरीका (सिंगल कॉलम सपोर्ट के लिए)
                full_b64 = get_val_case_insensitive(f_row, "FileBase64", "base64", "file", "Chunk_0")
                if not full_b64:
                    # यदि ऊपर वाले किसी की में न मिले तो सारे सेल वैल्यू मिला लें
                    full_b64 = "".join(str(v) for k, v in f_row.items() if k != "ShipperName" and v)

            if full_b64 and len(full_b64.strip()) > 0:
                try:
                    clean_b64 = str(full_b64).strip()
                    clean_b64 = clean_b64.replace("\n", "").replace("\r", "").replace(" ", "+")
                    
                    missing_padding = len(clean_b64) % 4
                    if missing_padding:
                        clean_b64 += '=' * (4 - missing_padding)
                    
                    decoded_bytes = base64.b64decode(clean_b64)
                    if decoded_bytes.startswith(b'PK'):
                        return decoded_bytes
                except Exception:
                    pass
    return None

def load_template_from_sheet(shipper_name):
    """गूगल शीट से शिपर की फाइल को openpyxl Workbook में बदलता है"""
    raw_bytes = load_template_bytes_from_sheet(shipper_name)
    if raw_bytes:
        try:
            return openpyxl.load_workbook(BytesIO(raw_bytes))
        except Exception:
            pass
    return None
