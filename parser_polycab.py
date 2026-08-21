import re

def format_date_ddmmyyyy(date_str):
    """
    विभिन्न डेट फॉर्मेट्स (उदा. 02-07-2026, 2026-07-02, 02-JUL-2026) को DD/MM/YYYY में कन्वर्ट करता है।
    """
    if not date_str:
        return ""

    date_str = str(date_str).strip()

    # 1. DD-MM-YYYY / DD/MM/YYYY / DD.MM.YYYY
    m1 = re.search(r'(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{4})', date_str)
    if m1:
        d, m, y = m1.groups()
        return f"{int(d):02d}/{int(m):02d}/{y}"

    # 2. YYYY-MM-DD / YYYY/MM/DD
    m2 = re.search(r'(\d{4})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})', date_str)
    if m2:
        y, m, d = m2.groups()
        return f"{int(d):02d}/{int(m):02d}/{y}"

    # 3. DD-MMM-YYYY (e.g. 02-JUL-2026, 2-Jul-26)
    months = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
        'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
    }
    m3 = re.search(r'(\d{1,2})[\s\/\-](' + '|'.join(months.keys()) + r')[\s\/\-](\d{2,4})', date_str, re.IGNORECASE)
    if m3:
        d, mon, y = m3.groups()
        mon_num = months[mon.upper()]
        if len(y) == 2:
            y = "20" + y
        return f"{int(d):02d}/{mon_num}/{y}"

    # 4. DD-MM-YY
    m4 = re.search(r'(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{2})', date_str)
    if m4:
        d, m, y = m4.groups()
        return f"{int(d):02d}/{int(m):02d}/20{y}"

    return date_str

def extract_invoice_details_from_text(pdf_text):
    """
    यदि मेन इनवॉइस फील्ड्स खाली हों तो PDF टेक्स्ट से Regex द्वारा Invoice No और Date ढूंढता है।
    """
    inv_no = ""
    inv_date = ""
    if not pdf_text:
        return inv_no, inv_date

    m_inv = re.search(r'INVOICE\s*(?:NO\.?|NUMBER)?\s*[:\.]?\s*([A-Z0-9]{8,20})', pdf_text, re.IGNORECASE)
    if m_inv:
        inv_no = m_inv.group(1).strip()

    m_date = re.search(r'(?:DTD\.?|DATE\s*[:\.]?)\s*(\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{2,4}|\d{1,2}[\s\/\-][A-Za-z]{3}[\s\/\-]\d{2,4})', pdf_text, re.IGNORECASE)
    if m_date:
        inv_date = m_date.group(1).strip()

    return inv_no, inv_date

def extract_polycab_items(pdf_lines, pdf_text=""):
    """
    Polycab के लिए डेडीकेटेड पार्सर लॉजिक।
    """
    parsed_items = []
    current_hs = "85446090"

    for line in pdf_lines:
        line_str = line.strip()

        if "85446090" in line_str:
            current_hs = "85446090"

        if "METER" in line_str or re.search(r'\d+\.\d{2}', line_str):
            nums = re.findall(r'[\d,]+\.\d{2,3}', line_str)
            if nums:
                item_data = {
                    "hs_code": current_hs,
                    "description_text": "ALUMINIUM CONDUCTOR COVERED WITH SEMI CONDUCTING COMPOUND XLPE INSULATED HDPE SHEATHED UNARMOURED CABLE",
                    "nums": nums,
                    "dbk_found": ""
                }
                parsed_items.append(item_data)

    if not parsed_items:
        parsed_items.append({
            "hs_code": "85446090",
            "description_text": "ELECTRICAL CABLES",
            "nums": ["0", "0", "0", "0", "0", "0", "0"],
            "dbk_found": ""
        })

    return parsed_items

def map_polycab_items_to_excel_dynamic(ws, parsed_items, resolved_item_rules, inv_sr_no=1, start_overall_sr=1, start_excel_row=2, default_invoice_no="", default_invoice_date="", pdf_text="", lut_kws="", paid_kws="", parser_rule=""):
    """
    एक्सल शीट में Polycab का डेटा डायनेमिकली भरने का फंक्शन।
    """
    current_row = start_excel_row
    overall_sr = start_overall_sr

    inv_no = default_invoice_no
    inv_date = default_invoice_date

    if not inv_no or not inv_date:
        ext_no, ext_date = extract_invoice_details_from_text(pdf_text)
        if not inv_no:
            inv_no = ext_no
        if not inv_date:
            inv_date = ext_date

    formatted_date = format_date_ddmmyyyy(inv_date)

    for idx, item in enumerate(parsed_items):
        item_sr = idx + 1

        # 1. सबसे पहले F, G, H, I, J में पक्का डेटा फिक्स करना
        ws[f"F{current_row}"] = overall_sr          # SR. NO.
        ws[f"G{current_row}"] = inv_sr_no           # Inv. Sr. No.[cite: 21]
        ws[f"H{current_row}"] = item_sr             # Item Sr. No.[cite: 21]
        ws[f"I{current_row}"] = inv_no if inv_no else "INV"  # Invoice No.[cite: 21]
        ws[f"J{current_row}"] = formatted_date      # Invoice Date (DD/MM/YYYY)[cite: 21]

        for field_name, rule_info in resolved_item_rules.items():
            col = rule_info.get("col", "K").upper()
            r_type = rule_info.get("type", "")
            r_val = rule_info.get("rule", "")

            # 🛑 Absolute Guard: कॉलम I और J पर किसी भी अन्य नियम को चलने ही न दें
            if col in ["I", "J"]:
                continue

            cell_target = f"{col}{current_row}"
            val_to_write = ""
            field_name_lower = field_name.lower()

            if "description" in field_name_lower:
                desc_raw = item.get("description_text", "")
                val_to_write = desc_raw.replace("DESCRIPTION", "DESCRIPTION\nOF GOODS")
            elif "hs" in field_name_lower or "ritc" in field_name_lower:
                val_to_write = item.get("hs_code", "85446090")
            elif r_type == "Constant Text":
                val_to_write = r_val
            else:
                nums = item.get("nums", [])
                if nums and len(nums) > 0:
                    val_to_write = nums[0]
                else:
                    val_to_write = r_val

            ws[cell_target] = val_to_write

        # 🛡️ Double Protection: लूप खत्म होने के बाद भी आखिरी बार सुनिश्चित करना कि कॉलम I और J ओवरराइट न हों
        ws[f"I{current_row}"] = inv_no if inv_no else "INV"
        ws[f"J{current_row}"] = formatted_date

        current_row += 1
        overall_sr += 1

    return ws, overall_sr, current_row
