import re

def apply_rule_filter(raw_text, mode, stop_kw, flt):
    """
    Core Extraction Engine: Filters raw PDF extracted text based on user rules
    """
    if not raw_text:
        return ""
        
    text = raw_text.strip()
    if text.startswith(":"):
        text = text[1:].strip()
    
    if mode == "Word Position":
        w_num = int(stop_kw.strip()) if stop_kw and str(stop_kw).strip().isdigit() else 1
        parts = text.split()
        text = parts[w_num - 1].strip() if len(parts) >= w_num else ""
    elif mode == "After Word" and stop_kw:
        if stop_kw.lower() in text.lower():
            start_idx = text.lower().find(stop_kw.lower()) + len(stop_kw)
            text = text[start_idx:].strip()
            if text.startswith(":"):
                text = text[1:].strip()
    elif mode == "Between Keywords" and stop_kw:
        if stop_kw.lower() in text.lower():
            text = text.lower().split(stop_kw.lower())[0].strip()
    elif mode == "Exact Word":
        parts = text.split()
        text = parts[0].strip() if parts else ""
    elif mode == "Full Line":
        text = text.split("\n")[0].strip()

    if flt == "Container Number (ISO Format)":
        cntr_match = re.search(r'\b[A-Za-z]{4}\s*\d{7}\b', text)
        return cntr_match.group(0).replace(" ", "") if cntr_match else text.strip()
    elif flt == "Numbers Only":
        nums = re.findall(r'[\d,.]+', text)
        return nums[0].strip() if nums else ""
    elif flt == "Letters Only":
        return re.sub(r'[^A-Za-z\s]', '', text).strip()
    elif flt == "Clean Date (DD/MM/YYYY)":
        d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', text)
        return d_match.group(0).replace(".", "/").replace("-", "/") if d_match else text.strip()

    return text.strip()

def extract_header_value(pdf_lines, pdf_text, keyword, position, mode, stop_kw, filter_type):
    """
    Extracts specific header keyword values from parsed PDF lines
    """
    raw_t = ""
    if keyword:
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
                    if line_i + 1 < len(pdf_lines):
                        raw_t = pdf_lines[line_i + 1].strip()
                        if raw_t:
                            break
                elif position == "2 Lines Below":
                    if line_i + 2 < len(pdf_lines):
                        raw_t = pdf_lines[line_i + 2].strip()
                        if raw_t:
                            break
    else:
        raw_t = pdf_text

    return apply_rule_filter(raw_t, mode, stop_kw, filter_type)
