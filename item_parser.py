import re

def extract_item_table_rows(pdf_lines):
    parsed_items = []
    
    for line in pdf_lines:
        line_str = line.strip()
        # 8-digit HS Code se shuru hone wali line pehchano
        if re.match(r'^\d{8}\b', line_str):
            parts = [p.strip() for p in line_str.split() if p.strip()]
            if len(parts) >= 3:
                item_dict = {
                    "hs_code": parts[0],
                    "raw_parts": parts
                }
                
                # Welspun Row Items Extraction (HS Code, Description, Net Wt, DBK, Qty, Rate, Amt USD, Amt INR, IGST %, IGST Amt)
                if len(parts) >= 8:
                    item_dict["description"] = parts[1]
                    item_dict["net_weight"] = parts[2]
                    item_dict["dbk_sr"] = parts[3]
                    item_dict["quantity"] = parts[4]
                    item_dict["rate"] = parts[5]
                    item_dict["amount_usd"] = parts[6]
                    item_dict["amount_inr"] = parts[7]
                    if len(parts) >= 9:
                        item_dict["igst_rate"] = parts[8]
                    if len(parts) >= 10:
                        item_dict["igst_amt"] = parts[9]
                else:
                    item_dict["description"] = parts[1] if len(parts) > 1 else ""
                    item_dict["quantity"] = parts[2] if len(parts) > 2 else ""
                    
                parsed_items.append(item_dict)
                
    return parsed_items

def map_items_to_excel_dynamic(ws, parsed_items, item_rules, inv_sr_no=1, start_overall_sr=1, start_excel_row=2, default_invoice_no="", default_invoice_date=""):
    curr_row = start_excel_row
    overall_sr = start_overall_sr
    
    # Clean Date Formatting (DD/MM/YYYY)
    clean_date = ""
    d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', str(default_invoice_date))
    if d_match:
        clean_date = d_match.group(0).replace(".", "/").replace("-", "/")
    elif default_invoice_date and not str(default_invoice_date).lower().startswith("inv"):
        clean_date = str(default_invoice_date)

    # Standard Dictionary Mapping for Rule Details
    value_map = {
        "hs code": "hs_code", "hs": "hs_code", "ritc": "hs_code",
        "description": "description",
        "net weight": "net_weight", "net wt": "net_weight", "weight": "net_weight",
        "dbk sr (+b suffix)": "dbk_sr", "dbk sr": "dbk_sr", "dbk": "dbk_sr", "drawback": "dbk_sr",
        "qty number": "quantity", "qty": "quantity", "quantity": "quantity",
        "rate": "rate",
        "amount usd": "amount_usd", "goods value": "amount_usd", "amount": "amount_usd",
        "taxable amt": "amount_inr", "taxable": "amount_inr", "amount inr": "amount_inr",
        "igst %": "igst_rate", "igst rate": "igst_rate",
        "igst amt": "igst_amt", "igst amount": "igst_amt"
    }

    for item_idx, item in enumerate(parsed_items):
        item_sr_no = item_idx + 1
        
        # 🎯 STRICTLY ONLY G, H, I, J ARE FILLED BY SYSTEM CODE:
        ws[f"G{curr_row}"] = inv_sr_no                    # G = Inv Sr No
        ws[f"H{curr_row}"] = item_sr_no                   # H = Item Sr No
        ws[f"I{curr_row}"] = default_invoice_no           # I = Invoice No
        ws[f"J{curr_row}"] = clean_date                   # J = Clean Date (DD/MM/YYYY)
        
        # 🎯 DIRECT UI MAPPING (Section 4 Dynamic Builder)
        for field_name, r_info in item_rules.items():
            col_letter = r_info.get("col", "").strip().upper()
            rule_type = r_info.get("type", "PDF Row Item")
            rule_val = r_info.get("rule", "").strip()
            
            if not col_letter:
                continue
                
            cell_ref = f"{col_letter}{curr_row}"
            
            if rule_type == "Constant Text":
                ws[cell_ref] = rule_val
            elif rule_type == "Excel Cell Reference":
                if rule_val and len(rule_val) >= 2 and rule_val[1].isdigit():
                    ws[cell_ref] = f"={rule_val}"
                else:
                    ws[cell_ref] = rule_val
            elif rule_type == "Smart Detection":
                desc = item.get("description", "").upper()
                if "PCS" in desc or "PC" in desc:
                    ws[cell_ref] = "PCS"
                else:
                    ws[cell_ref] = rule_val if rule_val else "SET"
            elif rule_type == "PDF Row Item":
                r_val_lower = rule_val.lower().strip()
                dict_key = value_map.get(r_val_lower, "")
                
                raw_val = item.get(dict_key, "") if dict_key else ""
                
                # 🎯 ONLY SPECIAL LOGIC: S Column / DBK SR '+B' Suffix
                if dict_key == "dbk_sr" or col_letter == "S":
                    if raw_val and not str(raw_val).endswith("B"):
                        ws[cell_ref] = f"{raw_val}B"
                    else:
                        ws[cell_ref] = raw_val
                else:
                    try:
                        ws[cell_ref] = float(str(raw_val).replace(",", ""))
                    except:
                        ws[cell_ref] = raw_val
                    
        curr_row += 1
        overall_sr += 1
        
    return ws, overall_sr, curr_row
