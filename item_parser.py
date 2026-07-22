import re

def extract_item_table_rows(pdf_lines):
    """
    यह फ़ंक्शन PDF की सभी लाइन्स में से आइटम टेबल की रो (Line Items) पहचानकर बाहर निकालता है।
    """
    parsed_item_rows = []
    
    for line in pdf_lines:
        line_str = line.strip()
        
        # 🎯 कंडीशन: अगर लाइन 8-डिजिट RITC / HS Code से शुरू हो रही है (उदा: 63026090)
        if re.match(r'^\d{8}\b', line_str):
            parts = [p.strip() for p in line_str.split() if p.strip()]
            if len(parts) >= 4:
                parsed_item_rows.append(parts)
                
    return parsed_item_rows


def map_items_to_excel(ws, parsed_item_rows, default_invoice_no="INV", default_invoice_date=""):
    """
    यह फ़ंक्शन एक्सट्रैक्ट किए गए डेटा को Excel शीट के F से Z कॉलम्स में रूल्स के अनुसार लिखता है।
    """
    if not parsed_item_rows:
        return ws
        
    start_excel_row = 2  # Row 2 से डेटा भरना शुरू करेंगे
    
    # B19 सेल से IGST Status (LUT / P) उठाना
    b19_status = ws["B19"].value if ws["B19"].value else ""
    
    for idx, item in enumerate(parsed_item_rows):
        curr_row = start_excel_row + idx
        
        # 🎯 Rule 1 & 2: Serial Numbers and Invoice Refs
        ws[f"F{curr_row}"] = idx + 1                                       # SR. NO. (1, 2, 3...)
        ws[f"G{curr_row}"] = 1                                             # Inv.Sr. No. (1st Invoice ke liye Always 1)
        ws[f"H{curr_row}"] = idx + 1                                       # Item. Sr. No. (1, 2, 3...)
        
        # 🎯 Rule 2 & 3: Invoice No and Clean Date (DD/MM/YYYY)
        inv_no_val = ws["C2"].value if ws["C2"].value and str(ws["C2"].value).strip() != "" else default_invoice_no
        ws[f"I{curr_row}"] = inv_no_val                                    # Invoice No.
        
        raw_date = ws["D2"].value if ws["D2"].value else default_invoice_date
        clean_date = ""
        if raw_date:
            date_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', str(raw_date))
            clean_date = date_match.group(0).replace(".", "/").replace("-", "/") if date_match else str(raw_date)
            
        ws[f"J{curr_row}"] = clean_date                                    # Invoice Date (DD/MM/YYYY)
        
        # 🎯 Rule 4: RITC, Product Name and Blank L/M
        hs_code = item[0]
        ws[f"K{curr_row}"] = hs_code                                       # RITC (HS Code)
        ws[f"L{curr_row}"] = ""                                            # Blank (बाद में समझेंगे)
        ws[f"M{curr_row}"] = ""                                            # Blank (बाद में समझेंगे)
        
        # 🎯 Rule 5 & 6: Qty and UNIT (Quantity SET)
        # Array Parts: ['63026090', 'Set', 'Towel', '133.272', '630201', '180.000', '5.08', '914.40', '87,279.48', '5.00', '4,363.97']
        qty_val = ""
        dbk_sr = ""
        
        # DBK Sr. & Qty Identifiers
        for p in item:
            clean_p = p.replace(",", "").strip()
            # DBK Sr (6-10 Digits / Alphanumeric)
            if re.match(r'^\d{6,10}[A-Za-z]?$', clean_p) and clean_p != hs_code:
                dbk_sr = clean_p
                
        # Qty is usually after DBK in PDF table
        if len(item) >= 6:
            # Finding Qty field (number with decimals)
            for p in item[3:]:
                if re.match(r'^\d{1,3}(,\d{3})*(\.\d+)?$', p) and p != hs_code:
                    qty_val = p
                    break
                    
        ws[f"N{curr_row}"] = qty_val                                       # Qty. (Quantity SET data)
        ws[f"O{curr_row}"] = "SET"                                         # UNIT (Always SET)
        
        # Goods Value (USD)
        ws[f"P{curr_row}"] = item[-4] if len(item) >= 4 else ""             # Goods Value
        ws[f"Q{curr_row}"] = ""                                            # SCHEME CODE (बाद में समझेंगे)
        
        # 🎯 Rule 8: Drawback SR with Compulsory 'B' and No Space
        if dbk_sr:
            dbk_sr_clean = dbk_sr.replace(" ", "").upper()
            if not dbk_sr_clean.endswith("B"):
                dbk_sr_clean += "B"
            ws[f"R{curr_row}"] = dbk_sr_clean                              # DRAWBACK SR
        else:
            ws[f"R{curr_row}"] = ""
            
        ws[f"S{curr_row}"] = ""                                            # Blank
        ws[f"T{curr_row}"] = ""                                            # Blank
        
        # 🎯 Rule 10: IGST Status from B19
        ws[f"U{curr_row}"] = b19_status                                    # IGST Status (LUT / P)
        
        # 🎯 Rule 11: Correct Tax Amounts
        ws[f"V{curr_row}"] = item[-3] if len(item) >= 3 else ""             # Taxable Value (INR)
        ws[f"W{curr_row}"] = item[-2] if len(item) >= 2 else ""             # IGSTPer (%)
        ws[f"X{curr_row}"] = item[-1] if len(item) >= 1 else ""             # IGST AMT
        
        ws[f"Y{curr_row}"] = ""                                            # Blank (बाद में समझेंगे)
        ws[f"Z{curr_row}"] = ""                                            # Blank (बाद में समझेंगे)
        
    return ws
