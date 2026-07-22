import re

def extract_item_table_rows(pdf_lines):
    parsed_item_rows = []
    for line in pdf_lines:
        line_str = line.strip()
        # 8-digit HS Code / RITC matching
        if re.match(r'^\d{8}\b', line_str):
            parts = [p.strip() for p in line_str.split() if p.strip()]
            if len(parts) >= 4:
                parsed_item_rows.append(parts)
    return parsed_item_rows


def map_items_to_excel(ws, parsed_item_rows, inv_sr_no=1, start_overall_sr=1, start_excel_row=2, default_invoice_no="INV", default_invoice_date=""):
    if not parsed_item_rows:
        return ws, start_overall_sr, start_excel_row
        
    b19_status = ws["B19"].value if ws["B19"].value else ""
    current_overall_sr = start_overall_sr
    
    for idx, item in enumerate(parsed_item_rows):
        curr_row = start_excel_row + idx
        
        ws[f"F{curr_row}"] = current_overall_sr                           # SR. NO.
        ws[f"G{curr_row}"] = inv_sr_no                                     # Inv.Sr. No.
        ws[f"H{curr_row}"] = idx + 1                                       # Item. Sr. No.
        
        inv_no_val = ws["C2"].value if ws["C2"].value and str(ws["C2"].value).strip() != "" else default_invoice_no
        ws[f"I{curr_row}"] = inv_no_val                                    # Invoice No.
        
        raw_date = ws["D2"].value if ws["D2"].value else default_invoice_date
        clean_date = ""
        if raw_date:
            date_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', str(raw_date))
            clean_date = date_match.group(0).replace(".", "/").replace("-", "/") if date_match else str(raw_date)
            
        ws[f"J{curr_row}"] = clean_date                                    # Invoice Date
        
        hs_code = item[0]
        ws[f"K{curr_row}"] = hs_code                                       # RITC
        ws[f"L{curr_row}"] = ""                                            # Blank
        ws[f"M{curr_row}"] = ""                                            # Blank
        
        qty_val = ""
        dbk_sr = ""
        
        for p in item:
            clean_p = p.replace(",", "").strip()
            if re.match(r'^\d{6,10}[A-Za-z]?$', clean_p) and clean_p != hs_code:
                dbk_sr = clean_p
                
        if len(item) >= 6:
            for p in item[3:]:
                if re.match(r'^\d{1,3}(,\d{3})*(\.\d+)?$', p) and p != hs_code:
                    qty_val = p
                    break
                    
        ws[f"N{curr_row}"] = qty_val                                       # Qty
        ws[f"O{curr_row}"] = "SET"                                         # UNIT
        ws[f"P{curr_row}"] = item[-4] if len(item) >= 4 else ""             # Goods Value
        ws[f"Q{curr_row}"] = ""                                            # Blank
        
        if dbk_sr:
            dbk_sr_clean = dbk_sr.replace(" ", "").upper()
            if not dbk_sr_clean.endswith("B"):
                dbk_sr_clean += "B"
            ws[f"R{curr_row}"] = dbk_sr_clean                              # DBK SR (+B)
        else:
            ws[f"R{curr_row}"] = ""
            
        ws[f"S{curr_row}"] = ""                                            # Blank
        ws[f"T{curr_row}"] = ""                                            # Blank
        ws[f"U{curr_row}"] = b19_status                                    # IGST Status (from B19)
        ws[f"V{curr_row}"] = item[-3] if len(item) >= 3 else ""             # Taxable Value
        ws[f"W{curr_row}"] = item[-2] if len(item) >= 2 else ""             # IGSTPer
        ws[f"X{curr_row}"] = item[-1] if len(item) >= 1 else ""             # IGST AMT
        ws[f"Y{curr_row}"] = ""                                            # Blank
        ws[f"Z{curr_row}"] = ""                                            # Blank
        
        current_overall_sr += 1

    next_row = start_excel_row + len(parsed_item_rows)
    return ws, current_overall_sr, next_row
