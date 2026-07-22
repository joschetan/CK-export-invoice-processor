import re

def extract_item_table_rows(pdf_lines):
    """
    यह फ़ंक्शन PDF की सभी लाइन्स में से आइटम टेबल की रो (Line Items) पहचानकर बाहर निकालता है।
    चाहे इनवॉइस 1 पेज की हो या 10 पेजों में फैली हो!
    """
    parsed_item_rows = []
    
    for line in pdf_lines:
        line_str = line.strip()
        
        # 🎯 कंडीशन: अगर लाइन 8-डिजिट RITC / HS Code से शुरू हो रही है (उदा: 63026090)
        if re.match(r'^\d{8}\b', line_str):
            parts = [p.strip() for p in line_str.split() if p.strip()]
            # टेबल की रो में कम से कम 4-5 कॉलम्स होने चाहिए
            if len(parts) >= 4:
                parsed_item_rows.append(parts)
                
    return parsed_item_rows


def map_items_to_excel(ws, parsed_item_rows, default_invoice_no="INV"):
    """
    यह फ़ंक्शन एक्सट्रैक्ट किए गए डेटा को Excel शीट के F कॉलम से Y कॉलम तक लिखता है।
    """
    if not parsed_item_rows:
        return ws
        
    start_excel_row = 2  # Excel में Row 2 से टेबल लिखना शुरू करेंगे
    
    for idx, item in enumerate(parsed_item_rows):
        curr_row = start_excel_row + idx
        
        # 1. Auto Counters & Reference Fields
        ws[f"F{curr_row}"] = idx + 1                                       # SR. NO.
        ws[f"G{curr_row}"] = idx + 1                                       # Inv. Sr. No.
        ws[f"H{curr_row}"] = ws["C2"].value if ws["C2"].value else default_invoice_no # Invoice No
        
        # 2. Extract Data Fields from Array Parts
        # उदा: ['63026090', 'Set', 'Towel', '133.272', '630201', '180.000', '5.08', '914.40', '87,279.48', '5.00', '4,363.97']
        hs_code = item[0]
        dbk_sr = ""
        
        # Drawback SR Identifier (6-10 डिजिट / अल्फान्यूमेरिक कोड)
        for p in item:
            if re.match(r'^\d{6,10}[A-Za-z]?$', p) and p != hs_code:
                dbk_sr = p
                
        # 3. Write Values to Exact Excel Columns (F to Y)
        ws[f"J{curr_row}"] = hs_code                                       # RITC (HS Code)
        ws[f"K{curr_row}"] = item[1] if len(item) > 1 else ""                 # Product Name
        ws[f"L{curr_row}"] = item[2] if len(item) > 2 and not item[2].replace('.', '', 1).isdigit() else item[1] # Description
        
        # Table Amount Columns (पीछे से पोजीशन ढूँढना)
        ws[f"O{curr_row}"] = item[-4] if len(item) >= 4 else ""                 # Goods Value (USD)
        ws[f"Q{curr_row}"] = dbk_sr                                       # DRAWBACK SR
        ws[f"U{curr_row}"] = item[-3] if len(item) >= 3 else ""                 # Taxable Value (INR)
        ws[f"V{curr_row}"] = item[-2] if len(item) >= 2 else ""                 # IGSTPer (%)
        ws[f"W{curr_row}"] = item[-1] if len(item) >= 1 else ""                 # IGST AMT
        
    return ws
