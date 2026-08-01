def load_template_bytes_from_sheet(shipper_name):
    """गूगल शीट से शिपर की सिंगल-कॉलम Base64 फाइल को डिकोड करके बाइट्स लौटाता है"""
    data = fetch_all_from_sheet()
    if not data:
        return None
    
    files_list = data.get("files", [])
    for f_row in files_list:
        s_name = get_val_case_insensitive(f_row, "ShipperName", "shipper")
        
        if s_name.lower().strip() == shipper_name.lower().strip():
            b64_str = get_val_case_insensitive(f_row, "FileBase64", "base64", "file")
            if b64_str and len(b64_str.strip()) > 0:
                try:
                    # 🛠️ यहाँ नई लाइन और अनचाहे स्पेसेस को साफ किया गया है
                    clean_b64 = str(b64_str).strip()
                    clean_b64 = clean_b64.replace("\n", "").replace("\r", "").replace(" ", "+")
                    
                    missing_padding = len(clean_b64) % 4
                    if missing_padding:
                        clean_b64 += '=' * (4 - missing_padding)
                    
                    decoded_bytes = base64.b64decode(clean_b64)
                    if decoded_bytes.startswith(b'PK'):
                        return decoded_bytes
                except Exception as e:
                    pass
    return None
