import re

def apply_value_replacement(extracted_text, mapping_str):
    """
    Parses 'FIND=REPLACE, FIND2=REPLACE2' mapping syntax and applies it to extracted_text.
    """
    if not extracted_text or not mapping_str or "=" not in mapping_str:
        return extracted_text

    text_clean = str(extracted_text).strip()
    pairs = [p.strip() for p in mapping_str.split(",") if "=" in p]
    
    for pair in pairs:
        parts = pair.split("=")
        if len(parts) == 2:
            find_kw = parts[0].strip()
            replace_kw = parts[1].strip()
            
            if text_clean.lower() == find_kw.lower():
                return replace_kw
            elif find_kw.lower() in text_clean.lower():
                pattern = re.compile(re.escape(find_kw), re.IGNORECASE)
                return pattern.sub(replace_kw, text_clean)
                
    return text_clean

def apply_rule_filter(raw_text, mode, stop_kw, flt, keyword=""):
    """
    Core Unified Extraction Engine: Filters raw PDF extracted text based on user rules
    """
    # 🎯 1. यदि नया 'Exact Keyword Paste' फिल्टर चुना गया है
    if flt == "Exact Keyword Paste (If Found)":
        target_check = stop_kw.strip() if stop_kw and str(stop_kw).strip() else keyword.strip()
        if target_check and target_check.lower() in str(raw_text).lower():
            return target_check
        return target_check if target_check else ""

    if not raw_text:
        return ""
        
    text = raw_text.strip()
    if text.startswith(":"):
        text = text[1:].strip()
    
    if mode == "Word Position" or mode.startswith("Word "):
        w_num = int(stop_kw.strip()) if stop_kw and str(stop_kw).strip().isdigit() else 1
        parts = text.split()
        text = parts[w_num - 1].strip() if len(parts) >= w_num else ""
    elif mode == "After Word" and stop_kw:
        if "=" not in stop_kw and stop_kw.lower() in text.lower():
            start_idx = text.lower().find(stop_kw.lower()) + len(stop_kw)
            text = text[start_idx:].strip()
            if text.startswith(":"):
                text = text[1:].strip()
    elif mode == "Between Keywords" and stop_kw:
        if "=" not in stop_kw and stop_kw.lower() in text.lower():
            text = text.lower().split(stop_kw.lower())[0].strip()
    elif mode == "Exact Word":
        parts = text.split()
        text = parts[0].strip() if parts else ""
    elif mode == "Full Line":
        # 🎯 मल्टी-लाइन एड्रेस को काटने के बजाय सुरक्षित रखा गया है
        text = text.strip()

    # 🎯 FILTERS IMPLEMENTATION
    if flt in ["Text Inside Parentheses ()", "Inside Parentheses ()"]:
        bracket_match = re.search(r'\((.*?)\)', text)
        text = bracket_match.group(1).strip() if bracket_match else text.strip()
    elif flt == "Container Number (ISO Format)":
        cntr_match = re.search(r'\b[A-Za-z]{4}\s*\d{7}\b', text)
        text = cntr_match.group(0).replace(" ", "") if cntr_match else text.strip()
    elif flt == "Remove All Spaces":
        text = text.replace(" ", "").strip()
    elif flt == "Numbers Only":
        nums = re.findall(r'[\d,.]+', text)
        text = nums[0].strip() if nums else ""
    elif flt == "Letters Only":
        text = re.sub(r'[^A-Za-z\s]', '', text).strip()
    elif flt == "Clean Date (DD/MM/YYYY)":
        d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', text)
        text = d_match.group(0).replace(".", "/").replace("-", "/") if d_match else text.strip()

    if stop_kw and "=" in stop_kw:
        text = apply_value_replacement(text, stop_kw)
    if flt and "=" in flt:
        text = apply_value_replacement(text, flt)

    return text.strip()

def extract_header_value(pdf_lines, pdf_text, keyword, position, mode, stop_kw, filter_type):
    """
    Extracts specific header keyword values from parsed PDF lines with side-by-side splitting logic
    """
    raw_t = ""
    
    if filter_type == "Exact Keyword Paste (If Found)":
        raw_t = pdf_text
    elif keyword:
        for line_i, line in enumerate(pdf_lines):
            if keyword.lower() in line.lower():
                if position == "Right (आगे)":
                    start_idx = line.lower().find(keyword.lower()) + len(keyword)
                    raw_t = line[start_idx:].strip()
                    if raw_t.startswith(":"):
                        raw_t = raw_t[1:].strip()
                    if raw_t:
                        break
                elif position == "Below (नीचे)":
                    # 🎯 साइड-बाय-साइड (Consignee और Buyer) की खिचड़ी रोकने के लिए स्पेशल स्प्लिट लॉजिक[cite: 7]
                    collected_lines = []
                    is_consignee = "consignee" in keyword.lower()
                    
                    for offset in range(1, 5):  # नीचे की 4 लाइनें[cite: 7]
                        if line_i + offset < len(pdf_lines):
                            next_line = pdf_lines[line_i + offset].strip()
                            lower_next = next_line.lower()
                            
                            # यदि कोई दूसरा मुख्य सेक्शन शुरू हो जाए तो रुक जाएं[cite: 7]
                            if not next_line or any(stop_lbl in lower_next for stop_lbl in [
                                "notify:", "pre-carriage", "vessel", "port of", "place of", "terms of", "sales order", "invoice no"
                            ]):
                                break
                                
                            # अगर एक ही लाइन में Consignee और Buyer दोनों आपस में चिपके हुए हैं[cite: 7]
                            if " - " in next_line and "Welspun USA Inc" in next_line:
                                parts = next_line.split("Welspun USA Inc")
                                if is_consignee:
                                    collected_lines.append(parts[0].strip())
                                else:
                                    collected_lines.append("Welspun USA Inc" + parts[1].strip())
                            else:
                                collected_lines.append(next_line)
                    if collected_lines:
                        raw_t = "\n".join(collected_lines)
                        break
                elif position == "2 Lines Below":
                    if line_i + 2 < len(pdf_lines):
                        raw_t = pdf_lines[line_i + 2].strip()
                        break
    else:
        raw_t = pdf_text

    return apply_rule_filter(raw_t, mode, stop_kw, filter_type, keyword)

def detect_igst_status(pdf_text, lut_keywords="", paid_keywords=""):
    """
    Detects whether invoice is 'LUT' or 'P' based on shipper custom keywords
    Returns: 'LUT', 'P', or 'UNKNOWN'
    """
    if not pdf_text:
        return "UNKNOWN"
        
    text_lower = pdf_text.lower()
    
    default_lut_kws = ["lut arn no", "w/o payment", "without payment", "under bond", "letter of undertaking"]
    custom_lut_kws = [k.strip().lower() for k in lut_keywords.split(",") if k.strip()]
    all_lut_kws = list(set(default_lut_kws + custom_lut_kws))
    
    for kw in all_lut_kws:
        if kw in text_lower:
            return "LUT"
            
    default_paid_kws = ["on payment of integrated tax", "with payment of integrated tax", "payment of integrated tax"]
    custom_paid_kws = [k.strip().lower() for k in paid_keywords.split(",") if k.strip()]
    all_paid_kws = list(set(default_paid_kws + custom_paid_kws))
    
    for kw in all_paid_kws:
        if kw in text_lower:
            return "P"
            
    return "UNKNOWN"
