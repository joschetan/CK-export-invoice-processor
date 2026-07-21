import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

def apply_advanced_filters(raw_text, mode, stop_kw, flt, logic):
    if not raw_text: return ""
    text = raw_text.strip()
    
    # 1. Stop Keyword Delimiter Execution (e.g. Stop at 'Date')
    if stop_kw and stop_kw.strip():
        st_idx = text.lower().find(stop_kw.lower())
        if st_idx != -1:
            text = text[:st_idx].strip()
            
    # 2. Cleanup Filters
    if flt == "Numbers Only":
        nums = re.findall(r'[\d,.]+', text)
        return nums[0].strip() if nums else ""
    elif flt == "Letters Only":
        lets = re.findall(r'[a-zA-Z]+', text)
        return " ".join(lets).strip() if lets else ""
    elif flt == "Inside Brackets ()":
        match = re.search(r'\(([^)]+)\)', text)
        return match.group(1).strip() if match else text
        
    # 3. Match Modes
    if mode == "Exact Word":
        # अगर कोलोन है तो उसके बाद का पहला शब्द पकड़ो
        if ":" in text: text = text.split(":", 1)[1].strip()
        parts = text.split()
        return parts[0].strip() if parts else ""
    elif mode == "Full Line":
        if ":" in text: text = text.split(":", 1)[1].strip()
        return text.split("\n")[0].strip()
        
    # 4. Custom Logic Mapping (e.g., Cart means CTN)
    if logic and logic.strip() and logic != "None":
        lg_lower = logic.lower()
        if "cart" in lg_lower or "ctn" in lg_lower:
            if "cart" in text.lower() or "ctn" in text.lower(): return "CTN"
        if "rosctl" in lg_lower:
            return "YES" if "rosctl" in text.lower() or "under rosctl" in text.lower() else "NO"
            
    return text.strip()

def render_processor():
    st.header("📤 Invoice Processing Zone (8-Column Engine)")
    st.caption("8-कॉलम रूल्स के आधार पर 100% सटीक एक्सट्रैक्शन।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=None)
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if "Full Job Excel Format File" in shipper_info.get("uploaded_files", {}):
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF Invoice अपलोड करें", type=["pdf"])
                
                if invoice_file and st.button("🚀 Process & Generate Excel", type="primary"):
                    with st.spinner("8-कॉलम रूल्स के अनुसार डेटा स्कैन हो रहा है..."):
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
                        
                        # 🎯 1. 8-कॉलम सिंगल सेल रूल्स निष्कर्षण
                        for field, r_info in rules.items():
                            kw = r_info.get("keyword", "").strip()
                            pos = r_info.get("position", "Right (आगे)")
                            target_cell = r_info.get("cell", "").strip()
                            mode = r_info.get("match_mode", "Exact Word")
                            stop_kw = r_info.get("stop_kw", "").strip()
                            flt = r_info.get("filter", "None")
                            lg = r_info.get("logic", "").strip()
                            
                            if pos != "Table Column" and target_cell and len(target_cell) >= 2 and target_cell[1].isdigit():
                                found_val = ""
                                
                                if kw:
                                    for idx, line in enumerate(pdf_lines):
                                        if kw.lower() in line.lower():
                                            if pos == "Right (आगे)":
                                                start_idx = line.lower().find(kw.lower()) + len(kw)
                                                raw_text = line[start_idx:].strip()
                                                found_val = apply_advanced_filters(raw_text, mode, stop_kw, flt, lg)
                                            elif pos == "Below (नीचे)":
                                                if idx + 1 < len(pdf_lines):
                                                    raw_text = pdf_lines[idx + 1].strip()
                                                    if mode == "Full Block":
                                                        block_lines = [raw_text]
                                                        if idx + 2 < len(pdf_lines): block_lines.append(pdf_lines[idx + 2].strip())
                                                        raw_text = " ".join(block_lines)
                                                    found_val = apply_advanced_filters(raw_text, mode, stop_kw, flt, lg)
                                            break
                                else:
                                    found_val = apply_advanced_filters(pdf_text, mode, stop_kw, flt, lg)
                                    
                                ws[target_cell] = found_val
                                if "inv. no" in field.lower() or "invoice no" in field.lower():
                                    if found_val: invoice_number = found_val

                        # 🎯 2. टेबल कॉलम्स निष्कर्षण (Items & Container Grid)
                        parsed_item_rows = []
                        parsed_container_rows = []
                        
                        for line in pdf_lines:
                            line_str = line.strip()
                            if re.match(r'^6302\d{4}', line_str) or re.match(r'^\d{8}', line_str):
                                parts = [p.strip() for p in line_str.split() if p.strip()]
                                if len(parts) >= 4: parsed_item_rows.append(parts)
                            if re.search(r'[A-Z]{4}\d{7}', line_str):
                                parts = [p.strip() for p in line_str.split() if p.strip()]
                                parsed_container_rows.append(parts)

                        # आइटम ग्रिड राइट करना (Row 2)
                        if parsed_item_rows:
                            for idx, item in enumerate(parsed_item_rows):
                                curr_row = 2 + idx
                                for field, r_info in rules.items():
                                    col = r_info.get("cell", "").strip()
                                    pos = r_info.get("position", "")
                                    if pos == "Table Column" and len(col) == 1:
                                        val = ""
                                        if "ritc" in field.lower() or "hs code" in field.lower(): val = item[0] if len(item) > 0 else ""
                                        elif "product" in field.lower() or "description" in field.lower(): val = item[1] if len(item) > 1 else ""
                                        elif "qty" in field.lower(): val = item[2] if len(item) > 2 else ""
                                        elif "goods value" in field.lower(): val = item[-2] if len(item) > 4 else ""
                                        ws[f"{col}{curr_row}"] = val

                        # कंटेनर ग्रिड राइट करना (Row 20)
                        if parsed_container_rows:
                            for idx, con in enumerate(parsed_container_rows):
                                curr_row = 20 + idx
                                for part in con:
                                    if re.match(r'^[A-Z]{4}\d{7}$', part): ws[f"B{curr_row}"] = part
                                    elif "40HC" in part or "20FT" in part or "40FT" in part: ws[f"C{curr_row}"] = part
                                    elif re.match(r'^[A-Z0-9]{7,12}$', part) and not part.isdigit(): ws[f"E{curr_row}"] = part

                        output = BytesIO()
                        wb.save(output)
                        
                        short_shipper = selected_shipper.split(" ")[0].lower()
                        clean_inv = re.sub(r'[\\/*?:"<>|]', "", invoice_number)
                        final_filename = f"{clean_inv}_{short_shipper}.xlsx"
                        
                        st.session_state["processed_file_ready"] = {"filename": final_filename, "data": output.getvalue()}
                        st.success(f"🎉 8-कॉलम इंजन से फ़ाइल '{final_filename}' सफलतापुर्वक तैयार है!")
                
                if st.session_state.get("processed_file_ready", None):
                    st.download_button(
                        label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                        data=st.session_state["processed_file_ready"]["data"],
                        file_name=st.session_state["processed_file_ready"]["filename"],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.session_state["processed_file_ready"] = None
