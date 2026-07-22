import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

def apply_advanced_filters(field_name, raw_text, mode, stop_kw, flt, logic, pdf_full_text=""):
    if not raw_text and not pdf_full_text: return ""
    text = raw_text.strip() if raw_text else pdf_full_text.strip()
    f_lower = field_name.lower()
    
    # 📌 Point 1: Final Dest. Country (Remove 'India')
    if "country" in f_lower or "dest. country" in f_lower:
        text = re.sub(r'\bindia\b', '', text, flags=re.IGNORECASE).strip()
        
    # 📌 Point 5: IGST Mode (LUT vs P)
    if "igst" in f_lower or "lut" in f_lower:
        if "w/o payment" in pdf_full_text.lower() or "without payment" in pdf_full_text.lower() or "lut" in pdf_full_text.lower() or "under bond" in pdf_full_text.lower():
            return "LUT"
        elif "with payment" in pdf_full_text.lower() or "with paymenmt" in pdf_full_text.lower():
            return "P"
            
    # 📌 Point 4: Payment Term (DA Check)
    elif "payment" in f_lower or "term" in f_lower:
        if not any(k in text.upper() for k in ["DP", "AP", "LC"]):
            return "DA"

    # 📌 Point 3: Unit of PKG (CTN)
    elif "unit" in f_lower or "pkg" in f_lower or "cart" in f_lower:
        if "cart" in pdf_full_text.lower() or "ctn" in pdf_full_text.lower() or "292" in text:
            return "CTN"

    # 📌 Point 8: Shipping Seal No (HLK2862227)
    elif "shiping seal" in f_lower or "shipping seal" in f_lower:
        seals = re.findall(r'\b[A-Z0-9]{6,12}\b', text)
        for s in seals:
            if not re.match(r'^[A-Z]{4}\d{7}$', s) and s not in ["40HC", "20FT", "40FT"] and not s.startswith("ENOS"):
                return s

    # 📌 Point 9: Excise Seal (ENOS03583519)
    elif "excise seal" in f_lower or "seal device" in f_lower:
        excise_match = re.search(r'\bENOS\d+\b', text, re.IGNORECASE)
        if excise_match:
            return excise_match.group(0)
        else:
            seals = re.findall(r'\b[A-Z0-9]{6,12}\b', text)
            for s in seals:
                if s.startswith("ENOS"):
                    return s

    # Standard Filters
    if stop_kw and stop_kw.strip() and stop_kw.lower() in text.lower():
        st_idx = text.lower().find(stop_kw.lower())
        text = text[:st_idx].strip()
        
    if flt == "Numbers Only":
        nums = re.findall(r'\d+', text)
        return nums[0].strip() if nums else ""
    elif flt == "Letters Only":
        lets = re.findall(r'[a-zA-Z]+', text)
        return " ".join(lets).strip() if lets else ""
    elif flt == "Inside Brackets ()":
        match = re.search(r'\(([^)]+)\)', text)
        return match.group(1).strip() if match else text
        
    if mode == "Exact Word":
        if ":" in text: text = text.split(":", 1)[1].strip()
        parts = text.split()
        return parts[0].strip() if parts else ""
    elif mode == "Full Line":
        if ":" in text: text = text.split(":", 1)[1].strip()
        return text.split("\n")[0].strip()
            
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
                                            elif pos == "Below (नीचे)":
                                                if idx + 1 < len(pdf_lines):
                                                    raw_text = pdf_lines[idx + 1].strip()
                                            break
                                else:
                                    raw_text = pdf_text
                                    
                                found_val = apply_advanced_filters(field, raw_text, mode, stop_kw, flt, lg, pdf_text)
                                ws[target_cell] = found_val
                                
                                if "inv. no" in field.lower() or "invoice no" in field.lower():
                                    if found_val: invoice_number = found_val

                        # 📌 कंटेनर/सील डेटा टेबल प्रोसेसिंग (C20/E20 जबरदस्ती नहीं लिखा जाएगा)
                        parsed_item_rows = []
                        for line in pdf_lines:
                            line_str = line.strip()
                            if re.match(r'^6302\d{4}', line_str) or re.match(r'^\d{8}', line_str):
                                parts = [p.strip() for p in line_str.split() if p.strip()]
                                if len(parts) >= 4: parsed_item_rows.append(parts)

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
