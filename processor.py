import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

# 🎯 हमारी नई सेफ मॉड्यूल इंपोर्ट करें
from item_parser import extract_item_table_rows, map_items_to_excel

def apply_strict_rule_filter(raw_text, mode, stop_kw, flt, logic, kw=""):
    if not raw_text: return ""
    text = raw_text.strip()
    
    if text.startswith(":"):
        text = text[1:].strip()
    
    if mode == "Word Position" or mode.startswith("Word "):
        w_num = 1
        if mode.startswith("Word ") and mode.split()[1].isdigit():
            w_num = int(mode.split()[1])
        elif stop_kw and stop_kw.strip().isdigit():
            w_num = int(stop_kw.strip())
        parts = text.split()
        text = parts[w_num - 1].strip() if len(parts) >= w_num else ""
    elif mode == "After Word" and stop_kw:
        if stop_kw.lower() in text.lower():
            start_idx = text.lower().find(stop_kw.lower()) + len(stop_kw)
            text = text[start_idx:].strip()
            if text.startswith(":"): text = text[1:].strip()
    elif mode == "Between Words":
        if kw and stop_kw and kw.lower() in text.lower() and stop_kw.lower() in text.lower():
            s_idx = text.lower().find(kw.lower()) + len(kw)
            e_idx = text.lower().find(stop_kw.lower(), s_idx)
            if e_idx != -1:
                text = text[s_idx:e_idx].strip()
    elif mode == "Skip 1st Word":
        parts = text.split(maxsplit=1)
        text = parts[1].strip() if len(parts) > 1 else text
    elif mode == "Exact Word":
        if text.startswith(":"): text = text[1:].strip()
        parts = text.split()
        text = parts[0].strip() if parts else ""
    elif mode == "Full Line":
        if text.startswith(":"): text = text[1:].strip()
        text = text.split("\n")[0].strip()

    if mode != "Word Position" and not mode.startswith("Word ") and mode not in ["Between Words", "After Word"] and stop_kw and stop_kw.strip() and stop_kw.lower() in text.lower():
        st_idx = text.lower().find(stop_kw.lower())
        text = text[:st_idx].strip()
        
    if flt == "Container Number (ISO Format)":
        cntr_match = re.search(r'\b[A-Za-z]{4}\s*\d{7}\b', text)
        if cntr_match:
            return cntr_match.group(0).replace(" ", "")
        cntr_match2 = re.search(r'\b[A-Za-z]{4}\d{6,8}\b', text)
        return cntr_match2.group(0) if cntr_match2 else text.strip()
    elif flt == "Container Size (20/40 Only)":
        size_match = re.search(r'\b(20|40)(?=\s*HC|\s*FT|\s*GP|\s*HQ|\b)', text, re.IGNORECASE)
        if size_match:
            return size_match.group(1)
        size_match2 = re.search(r'\b(20|40)\b', text)
        return size_match2.group(1) if size_match2 else ""
    elif flt == "Numbers Only":
        nums = re.findall(r'[\d,.]+', text)
        return nums[0].strip() if nums else ""
    elif flt == "Letters Only":
        lets = re.findall(r'[a-zA-Z]+', text)
        return " ".join(lets).strip() if lets else ""
    elif flt == "Inside Brackets ()":
        match = re.search(r'\(([^)]+)\)', text)
        return match.group(1).strip() if match else text
        
    if logic and logic.strip() and logic != "None":
        lg_lower = logic.lower()
        if "cart" in lg_lower or "ctn" in lg_lower:
            if "cart" in text.lower() or "ctn" in text.lower(): return "CTN"

    return text.strip()

def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("रूल्स के आधार पर 100% सटीक डेटा एक्सट्रैक्शन।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=None)
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if "Full Job Excel Format File" in shipper_info.get("uploaded_files", {}):
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF Invoice अपलोड करें", type=["pdf"])
                
                if invoice_file and st.button("🚀 Process & Generate Excel", type="primary"):
                    with st.spinner("रूल्स के अनुसार सटीक डेटा स्कैन हो रहा है..."):
                        rules = shipper_info.get("mapping_rules", {})
                        
                        original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                        wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                        ws = wb["INV"] if "INV" in wb.sheetnames else wb.active
                        
                        pdf_text = ""
                        pdf_lines = []
                        
                        with pdfplumber.open(invoice_file) as pdf:
                            for page in pdf.pages:
                                t = page.extract_text()
                                if t:
                                    pdf_text += t + "\n"
                                    pdf_lines.extend(t.split("\n"))
                        
                        invoice_number = "INV"
                        
                        # 🎯 1. Header Fields Mapping
                        for field, r_info in rules.items():
                            kw = r_info.get("keyword", "").strip()
                            pos = r_info.get("position", "Right (आगे)")
                            target_cell = r_info.get("cell", "").strip()
                            mode = r_info.get("match_mode", "Exact Word")
                            stop_kw = r_info.get("stop_kw", "").strip()
                            flt = r_info.get("filter", "None")
                            lg = r_info.get("logic", "").strip()
                            
                            if pos != "Table Column" and target_cell and len(target_cell) >= 2 and target_cell[1].isdigit():
                                raw_text = ""
                                if kw:
                                    for idx, line in enumerate(pdf_lines):
                                        if kw.lower() in line.lower():
                                            if pos == "Right (आगे)":
                                                start_idx = line.lower().find(kw.lower()) + len(kw)
                                                raw_text = line[start_idx:].strip()
                                                if raw_text.startswith(":"):
                                                    raw_text = raw_text[1:].strip()
                                                if raw_text:
                                                    break
                                            elif pos == "Below (नीचे)":
                                                if idx + 1 < len(pdf_lines):
                                                    raw_text = pdf_lines[idx + 1].strip()
                                                    if raw_text:
                                                        break
                                else:
                                    raw_text = pdf_text
                                    
                                found_val = apply_strict_rule_filter(raw_text, mode, stop_kw, flt, lg, kw)
                                ws[target_cell] = found_val
                                
                                if "inv. no" in field.lower() or "invoice no" in field.lower():
                                    if found_val: invoice_number = found_val

                        # 🎯 2. Item Table Mapping (Safe Module Calling)
                        parsed_items = extract_item_table_rows(pdf_lines)
                        ws = map_items_to_excel(ws, parsed_items, invoice_number)

                        output = BytesIO()
                        wb.save(output)
                        
                        short_shipper = selected_shipper.split(" ")[0].lower()
                        clean_inv = re.sub(r'[\\/*?:"<>|]', "", invoice_number)
                        final_filename = f"{clean_inv}_{short_shipper}.xlsx"
                        
                        st.session_state["processed_file_ready"] = {"filename": final_filename, "data": output.getvalue()}
                        st.success(f"🎉 फ़ाइल '{final_filename}' सफलतापुर्वक तैयार है!")
                
                if st.session_state.get("processed_file_ready", None):
                    st.download_button(
                        label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                        data=st.session_state["processed_file_ready"]["data"],
                        file_name=st.session_state["processed_file_ready"]["filename"],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.session_state["processed_file_ready"] = None
