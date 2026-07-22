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
            if len(parts) >= 3:
                parsed_item_rows.append(parts)
                
    return parsed_item_rows


def map_items_to_excel_dynamic(ws, parsed_item_rows, item_table_rules, inv_sr_no=1, start_overall_sr=1, start_excel_row=2, default_invoice_no="INV", default_invoice_date=""):
    """
    यह फ़ंक्शन डायनामिक UI रूल्स के हिसाब से Excel शीट के कॉलम्स में डेटा लिखता है।
    """
    if not parsed_item_rows:
        return ws, start_overall_sr, start_excel_row
        
    current_overall_sr = start_overall_sr
    
    for idx, item in enumerate(parsed_item_rows):
        curr_row = start_excel_row + idx
        
        # 🎯 Fixed Serial Number Columns (Standard Rules)
        ws[f"F{curr_row}"] = current_overall_sr                           # SR. NO. (Overall)
        ws[f"G{curr_row}"] = inv_sr_no                                     # Inv.Sr. No.
        ws[f"H{curr_row}"] = idx + 1                                       # Item. Sr. No.
        
        # Invoice No & Clean Date
        inv_no_val = ws["C2"].value if ws["C2"].value and str(ws["C2"].value).strip() != "" else default_invoice_no
        ws[f"I{curr_row}"] = inv_no_val                                    # Invoice No.
        
        raw_date = ws["D2"].value if ws["D2"].value else default_invoice_date
        clean_date = ""
        if raw_date:
            date_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', str(raw_date))
            clean_date = date_match.group(0).replace(".", "/").replace("-", "/") if date_match else str(raw_date)
            
        ws[f"J{curr_row}"] = clean_date                                    # Invoice Date (DD/MM/YYYY)
        
        # 🎯 DYNAMIC COLUMN MAPPING FROM UI RULES
        hs_code = item[0]
        desc_text = item[1] if len(item) > 1 else ""
        
        # Extract DBK Sr and Qty
        qty_val = ""
        dbk_sr = ""
        for p in item:
            clean_p = p.replace(",", "").strip()
            if re.match(r'^\d{6,10}[A-Za-z]?$', clean_p) and clean_p != hs_code:
                dbk_sr = clean_p
                
        if len(item) >= 5:
            for p in item[2:]:
                if re.match(r'^\d{1,3}(,\d{3})*(\.\d+)?$', p) and p != hs_code:
                    qty_val = p
                    break

        for field_name, rule_info in item_table_rules.items():
            col_letter = rule_info.get("col", "").strip().upper()
            rule_type = rule_info.get("type", "PDF Row Item")
            rule_detail = rule_info.get("rule", "").strip()
            
            if col_letter and len(col_letter) <= 2:
                target_cell = f"{col_letter}{curr_row}"
                val_to_write = ""
                
                if rule_type == "Constant Text":
                    val_to_write = rule_detail
                    
                elif rule_type == "Excel Cell Reference":
                    # 🎯 Excel Cell Reference Logic (e.g. B19, C2, E2)
                    cell_ref = rule_detail.upper().strip()
                    if cell_ref and len(cell_ref) >= 2 and cell_ref[1].isdigit():
                        c_val = ws[cell_ref].value
                        val_to_write = c_val if c_val is not None else ""
                    else:
                        val_to_write = ""
                    
                elif rule_type == "Smart Detection":
                    # 💡 Description of Goods में 'SET' या 'PCS' ढूंढना
                    full_item_str = " ".join(item).upper()
                    if "SET" in full_item_str or "SET" in desc_text.upper():
                        val_to_write = "SET"
                    elif "PCS" in full_item_str or "PIECE" in full_item_str or "PCS" in desc_text.upper():
                        val_to_write = "PCS"
                    elif rule_detail:
                        val_to_write = rule_detail
                    else:
                        val_to_write = "SET"
                        
                elif rule_type == "PDF Row Item":
                    f_lower = field_name.lower()
                    if "ritc" in f_lower or "hs code" in f_lower:
                        val_to_write = hs_code
                    elif "qty" in f_lower or "quantity" in f_lower:
                        val_to_write = qty_val
                    elif "goods value" in f_lower or "usd" in f_lower:
                        val_to_write = item[-4] if len(item) >= 4 else ""
                    elif "drawback" in f_lower or "dbk" in f_lower:
                        if dbk_sr:
                            dbk_clean = dbk_sr.replace(" ", "").upper()
                            if not dbk_clean.endswith("B"): dbk_clean += "B"
                            val_to_write = dbk_clean
                    elif "taxable" in f_lower:
                        val_to_write = item[-3] if len(item) >= 3 else ""
                    elif "igst rate" in f_lower or "igst %" in f_lower or "igstper" in f_lower:
                        val_to_write = item[-2] if len(item) >= 2 else ""
                    elif "igst amount" in f_lower or "igst amt" in f_lower:
                        val_to_write = item[-1] if len(item) >= 1 else ""
                        
                ws[target_cell] = val_to_write

        current_overall_sr += 1

    next_row = start_excel_row + len(parsed_item_rows)
    return ws, current_overall_sr, next_row
