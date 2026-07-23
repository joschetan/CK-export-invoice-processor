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
    
    clean_date = ""
    d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', str(default_invoice_date))
    if d_match:
        clean_date = d_match.group(0).replace(".", "/").replace("-", "/")
    elif default_invoice_date and not str(default_invoice_date).lower().startswith("inv"):
        clean_date = str(default_invoice_date)

    for item_idx, item in enumerate(parsed_items):
        item_sr_no = item_idx + 1
        
        # Standard Fixed System Columns (G, H, I, J, K)
        ws[f"G{curr_row}"] = inv_sr_no                    
        ws[f"H{curr_row}"] = overall_sr                   
        ws[f"I{curr_row}"] = item_sr_no                   
        ws[f"J{curr_row}"] = default_invoice_no           
        ws[f"K{curr_row}"] = clean_date                   
        
        # 🎯 FULLY CONTROLLED BY UI SETTINGS (Section 4 Dynamic Builder)
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
                r_val_lower = rule_val.lower()
                f_name_lower = field_name.lower()
                
                if "hs code" in r_val_lower or "ritc" in r_val_lower or "ritc" in f_name_lower or "hs" in r_val_lower:
                    ws[cell_ref] = item.get("hs_code", "")
                elif "description" in r_val_lower or "product" in r_val_lower or "description" in f_name_lower:
                    ws[cell_ref] = item.get("description", "")
                elif "qty" in r_val_lower or "quantity" in r_val_lower or "quantity" in f_name_lower:
                    val = item.get("quantity", "")
                    try: ws[cell_ref] = float(val.replace(",", ""))
                    except: ws[cell_ref] = val
                elif "rate" in r_val_lower or "rate" in f_name_lower:
                    val = item.get("rate", "")
                    try: ws[cell_ref] = float(val.replace(",", ""))
                    except: ws[cell_ref] = val
                elif "amount usd" in r_val_lower or "goods value" in r_val_lower or "amount" in r_val_lower or "goods" in f_name_lower or "usd" in r_val_lower:
                    val = item.get("amount_usd", "")
                    try: ws[cell_ref] = float(val.replace(",", ""))
                    except: ws[cell_ref] = val
                elif "taxable" in r_val_lower or "inr" in r_val_lower or "taxable" in f_name_lower:
                    val = item.get("amount_inr", "")
                    try: ws[cell_ref] = float(val.replace(",", ""))
                    except: ws[cell_ref] = val
                elif "igst %" in r_val_lower or "igst rate" in r_val_lower or "rate (%)" in f_name_lower:
                    val = item.get("igst_rate", "")
                    try: ws[cell_ref] = float(val.replace(",", ""))
                    except: ws[cell_ref] = val
                elif "igst amt" in r_val_lower or "igst amount" in r_val_lower or "amount (inr)" in f_name_lower:
                    val = item.get("igst_amt", "")
                    try: ws[cell_ref] = float(val.replace(",", ""))
                    except: ws[cell_ref] = val
                elif "dbk" in r_val_lower or "drawback" in r_val_lower or "dbk" in f_name_lower:
                    raw_dbk = item.get("dbk_sr", "")
                    if raw_dbk and not raw_dbk.endswith("B"):
                        ws[cell_ref] = f"{raw_dbk}B"
                    else:
                        ws[cell_ref] = raw_dbk
                elif "weight" in r_val_lower or "net wt" in r_val_lower or "wt" in f_name_lower:
                    val = item.get("net_weight", "")
                    try: ws[cell_ref] = float(val.replace(",", ""))
                    except: ws[cell_ref] = val
                else:
                    ws[cell_ref] = item.get("description", "")
                    
        curr_row += 1
        overall_sr += 1
        
    return ws, overall_sr, curr_row
