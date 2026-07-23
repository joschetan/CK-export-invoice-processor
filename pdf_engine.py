def detect_igst_status(pdf_text, lut_keywords="", paid_keywords=""):
    """
    Detects whether invoice is 'LUT' or 'P' based on shipper custom keywords
    Returns: 'LUT', 'P', or 'UNKNOWN'
    """
    if not pdf_text:
        return "UNKNOWN"
        
    text_lower = pdf_text.lower()
    
    # 1. Prepare default + custom LUT keywords
    default_lut_kws = ["lut arn no", "w/o payment", "without payment", "under bond", "letter of undertaking"]
    custom_lut_kws = [k.strip().lower() for k in lut_keywords.split(",") if k.strip()]
    all_lut_kws = list(set(default_lut_kws + custom_lut_kws))
    
    # 2. Check for LUT Match
    for kw in all_lut_kws:
        if kw in text_lower:
            return "LUT"
            
    # 3. Prepare default + custom Paid (P) keywords
    default_paid_kws = ["on payment of integrated tax", "with payment of integrated tax", "payment of integrated tax"]
    custom_paid_kws = [k.strip().lower() for k in paid_keywords.split(",") if k.strip()]
    all_paid_kws = list(set(default_paid_kws + custom_paid_kws))
    
    # 4. Check for Paid Match
    for kw in all_paid_kws:
        if kw in text_lower:
            return "P"
            
    # 5. If neither found, return UNKNOWN for Safety Prompt/Popup
    return "UNKNOWN"
