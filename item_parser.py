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
                    "raw_parts": parts,
                    "hs_code": parts[0]
                }
                
                # Extract all floating point/decimal numbers dynamically
                nums = re.findall(r'[\d,]+\.\d{2,3}', line_str)
                item_dict["nums"] = nums
                
                # Dynamic DBK Code Match (6-10 digits with optional letter suffix)
                dbk_match = re.search(r'\b\d{6}[A-Za-z]?\b|\b\d{10}[A-Za-z]?\b', line_str)
                item_dict["dbk_found"] = dbk_match.group(0) if dbk_match else ""

                # Universal Description Extraction (Text between HS Code and First Numeric Value)
                if len(nums) > 0:
                    first_num = nums[0]
                    start_pos = len(parts[0])
                    end_pos = line_str.find(first_num)
                    if end_pos > start_pos:
                        desc_text = line_str[start_pos:end_pos].strip()
                        if item_dict["dbk_found"]:
                            desc_text = desc_text.replace(item_dict["dbk_found"], "").strip()
                        item_dict["description_text"] = desc_text
                else:
                    item_dict["description_text"] = " ".join(parts[1:]) if len(parts) > 1 else ""
                        
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
    elif default_invoice_date and len(str(default_invoice_date)) >= 8 and not str(default_invoice_date).lower().startswith("inv"):
        clean_date = str(default_invoice_date)

    for item_idx, item in enumerate(parsed_items):
        item_sr_no = item_idx + 1
        
        # 🎯 STRICTLY SYSTEM COLUMNS ONLY (G, H, I, J)
        ws[f"G{curr_row}"] = inv_sr_no                    # G = Inv Sr No
        ws[f"H{curr_row}"] = item_sr_no                   # H = Item Sr No
        ws[f"I{curr_row}"] = default_invoice_no           # I = Invoice No
        ws[f"J{curr_row}"] = clean_date                   # J = Clean Date (DD/MM/YYYY)
        
        nums = item.get("nums", [])
        
        # 🎯 100% DYNAMIC UI MAPPING
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
                desc = item.get("description_text", "").upper()
                if "PCS" in desc or "PC" in desc:
                    ws[cell_ref] = "PCS"
                else:
                    ws[cell_ref] = rule_val if rule_val else "SET"
            elif rule_type == "PDF Row Item":
                r_val_lower = rule_val.lower().strip()
                f_name_lower = field_name.lower().strip()
                
                raw_val = ""
                
                # 🎯 FIXED PRIORITY: Check IGST % First BEFORE checking normal "rate"
                if "igst %" in r_val_lower or "igst rate" in f_name_lower or ("igst" in f_name_lower and "%" in f_name_lower) or ("igst" in f_name_lower and "rate" in f_name_lower):
                    raw_val = nums[5] if len(nums) > 5 else ""
                elif "igst amt" in r_val_lower or "igst amount" in f_name_lower or ("igst" in f_name_lower and "amt" in f_name_lower):
                    raw_val = nums[6] if len(nums) > 6 else ""
                elif "hs" in r_val_lower or "ritc" in f_name_lower or "hs code" in r_val_lower:
                    raw_val = item.get("hs_code", "")
                elif "description" in r_val_lower or "description" in f_name_lower:
                    raw_val = item.get("description_text", "")
                elif "dbk" in r_val_lower or "drawback" in f_name_lower or col_letter == "S":
                    raw_val = item.get("dbk_found", "")
                    if raw_val and not str(raw_val).endswith("B"):
                        raw_val = f"{raw_val}B"
                elif "weight" in r_val_lower or "net wt" in f_name_lower:
                    raw_val = nums[0] if len(nums) > 0 else ""
                elif "qty" in r_val_lower or "quantity" in f_name_lower:
                    raw_val = nums[1] if len(nums) > 1 else ""
                elif "rate" in r_val_lower or "rate" in f_name_lower:
                    raw_val = nums[2] if len(nums) > 2 else ""
                elif "amount usd" in r_val_lower or "goods value" in f_name_lower or "amount" in r_val_lower:
                    raw_val = nums[3] if len(nums) > 3 else ""
                elif "taxable" in r_val_lower or "taxable" in f_name_lower:
                    raw_val = nums[4] if len(nums) > 4 else ""
                
                try:
                    ws[cell_ref] = float(str(raw_val).replace(",", ""))
                except:
                    ws[cell_ref] = raw_val
                    
        curr_row += 1
        overall_sr += 1
        
    return ws, overall_sr, curr_row
