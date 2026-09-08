import re

def extract_mrl_items(pdf_lines, pdf_text=""):
    """
    MRL Tyres Limited के लिए डेडीकेटेड पार्सर रूल।
    यह इनवॉइस की लाइनों से आइटम और डेटा एक्सट्रेक्ट करेगा।
    """
    parsed_items = []
    
    # बेसिक फॉलबैक स्ट्रक्चर ताकि ऐप क्रैश न हो
    current_hs = "4011" # टायर्स/रबर के लिए स्टैंडर्ड HSN कोड (जरूरत पड़ने पर बदल सकते हैं)
    
    for line in pdf_lines:
        line_str = line.strip()
        
        # यहाँ आप MRL इनवॉइस के हिसाब से कीवर्ड मैचिंग या regex लिख सकते हैं
        if re.search(r'\d+\.\d{2}', line_str):
            nums = re.findall(r'[\d,]+\.\d{2,3}', line_str)
            if nums:
                item_data = {
                    "hs_code": current_hs,
                    "description_text": "AUTOMOTIVE TYRES / RUMBER PRODUCTS",
                    "nums": nums,
                    "dbk_found": ""
                }
                parsed_items.append(item_data)

    # यदि सीधे लाइनें न मिलें तो सेफ डमी स्ट्रक्चर
    if not parsed_items:
        parsed_items.append({
            "hs_code": current_hs,
            "description_text": "MRL TYRES PRODUCT",
            "nums": ["0", "0", "0", "0", "0"],
            "dbk_found": ""
        })

    return parsed_items

def map_mrl_items_to_excel_dynamic(ws, parsed_items, resolved_item_rules, inv_sr_no=1, start_overall_sr=1, start_excel_row=2, default_invoice_no="", default_invoice_date="", pdf_text="", lut_kws="", paid_kws="", parser_rule=""):
    """
    एक्सल शीट में MRL Tyres का डेटा डायनेमिकली भरने का फंक्शन।
    """
    current_row = start_excel_row
    overall_sr = start_overall_sr
    
    for idx, item in enumerate(parsed_items):
        item_sr = idx + 1
        
        # स्टैंडर्ड कॉलम मैपिंग (F, G, H, I, J...)
        ws[f"F{current_row}"] = overall_sr       # SR. NO.
        ws[f"G{current_row}"] = inv_sr_no        # Inv. Sr. No.
        ws[f"H{current_row}"] = item_sr          # Item Sr. No.
        ws[f"I{current_row}"] = default_invoice_no   # Invoice No.
        ws[f"J{current_row}"] = default_invoice_date # Invoice Date
        
        # डायनेमिक आइटम रूल्स प्रोसेस करना
        for field_name, rule_info in resolved_item_rules.items():
            col = rule_info.get("col", "K").upper()
            r_type = rule_info.get("type", "")
            r_val = rule_info.get("rule", "")
            
            cell_target = f"{col}{current_row}"
            val_to_write = ""
            
            if "description" in field_name.lower():
                val_to_write = item.get("description_text", "")
            elif "hs" in field_name.lower() or "ritc" in field_name.lower():
                val_to_write = item.get("hs_code", "4011")
            elif r_type == "Constant Text":
                val_to_write = r_val
            else:
                nums = item.get("nums", [])
                if nums and len(nums) > 0:
                    val_to_write = nums[0]
                else:
                    val_to_write = r_val

            ws[cell_target] = val_to_write

        current_row += 1
        overall_sr += 1

    return ws, overall_sr, current_row
