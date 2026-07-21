import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

def clean_extracted_value(text, pos, logic_str=""):
    """कीवर्ड के आगे से केवल सटीक डेटा निकालने वाला क्लीनर"""
    if not text:
        return ""
    
    text = text.strip()
    
    # 1. यदि कोई कस्टम लॉजिक/निर्देश दिया गया हो
    if logic_str and logic_str.strip() != "" and logic_str.lower() != "none":
        lg_lower = logic_str.lower()
        
        # ROSCTL
        if "rosctl" in lg_lower or "write:yes" in lg_lower:
            return "YES" if "rosctl" in text.lower() or "under rosctl" in text.lower() else "NO"
            
        # ब्रैकेट वाला लॉजिक () -> KGS
        if "bracket" in lg_lower or "parentheses" in lg_lower or "()" in lg_lower:
            match = re.search(r'\(([^)]+)\)', text)
            if match:
                return match.group(1).strip()
                
        # DA / Payment terms
        if "bl / awb date" in lg_lower or "da" in lg_lower:
            if "days" in text.lower() or "bl" in text.lower() or "awb" in text.lower():
                return "DA"
                
        # LUT Mode
        if "w/o paymenmt" in lg_lower or "lut" in lg_lower:
            if "w/o paymenmt" in text.lower() or "letter of undertaking" in text.lower() or "lut" in text.lower():
                return "LUT"
                
        # CTN / CART
        if "cart" in lg_lower or "ctn" in lg_lower:
            if "cart" in text.lower() or "ctn" in text.lower():
                return "CTN"

    # 2. डिफ़ॉल्ट क्लीनिंग (जब Logic = None हो)
    # Right (आगे): कीवर्ड के तुरंत बाद वाला पहला शब्द/नंबर ही उठाओ (बाकी पूरी लाइन छोड़ दो!)
    if pos == "Right (आगे)":
        # कोलोन या हाइफन के बाद का हिस्सा लो
        if ":" in text:
            text = text.split(":", 1)[1].strip()
        
        # स्पेस से स्प्लिट करके सिर्फ पहला वर्ड/नंबर पकड़ो
        parts = text.split()
        if parts:
            return parts[0].strip()
            
    # Below (नीचे): नीचे वाली लाइन का पहला वर्ड या साफ़ ब्लॉक
    elif pos == "Below (नीचे)":
        lines = text.split("\n")
        if lines:
            first_line = lines[0].strip()
            # अगर देश का नाम या कंटेनर नंबर है तो पूरा शब्द लो
            parts = first_line.split()
            if parts:
                return parts[0].strip()

    return text.strip()


def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("रूल्स बिल्डर के आधार पर सटीक सिंगल डेटा और टेबल एक्सट्रैक्शन।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if not shippers_list:
        st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है।")
    else:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=None, placeholder="यहाँ शिपर का नाम चुनें...")
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if "Full Job Excel Format File" not in shipper_info.get("uploaded_files", {}):
                st.error(f"❌ त्रुटि: इस शिपर के लिए 'Full Job Excel Format File' अपलोड नहीं है!")
            else:
                st.success(f"🔒 '{selected_shipper}' का प्रोफाइल और AI रूल्स लोड हो गए हैं।")
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF Invoice अपलोड करें", type=["pdf"])
                
                if invoice_file:
                    st.write("---")
                    
                    if st.button("🚀 Process & Generate Excel", type="primary"):
                        with st.spinner("पीडीएफ से रूल्स के अनुसार सटीक डेटा निकाला जा रहा है..."):
                            rules = shipper_info.get("mapping_rules", {})
                            
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            ws = wb["INV"] if "INV" in wb.sheetnames else wb.active
                            
                            pdf_text = ""
                            pdf_lines = []
                            pdf_tables = []
                            
                            with pdfplumber.open(invoice_file) as pdf:
                                for page in pdf.pages:
                                    t = page.extract_text()
                                    if t:
                                        pdf_text += t + "\n"
                                        pdf_lines.extend(t.split("\n"))
                                    tbls = page.extract_tables()
                                    if tbls:
                                        pdf_tables.extend(tbls)
                            
                            invoice_number = "INV"
                            
                            # 1. 🎯 सिंगल सेल रूल्स प्रोसेस करना (B2, B9, B3 आदि)
                            for field, r_info in rules.items():
                                kw = r_info.get("keyword", "").strip()
                                pos = r_info.get("position", "Right (आगे)")
                                target_cell = r_info.get("cell", "").strip()
                                lg = r_info.get("logic", "").strip()
                                
                                # केवल वही जो टेबल आइटम नहीं हैं और जिनका सेल नंबर फिक्स है (जैसे B9, D2)
                                if "table_item" not in lg.lower() and target_cell and len(target_cell) >= 2 and target_cell[1].isdigit():
                                    found_val = ""
                                    
                                    if kw:
                                        for idx, line in enumerate(pdf_lines):
                                            if kw.lower() in line.lower():
                                                if pos == "Right (आगे)":
                                                    # कीवर्ड के आगे वाला हिस्सा
                                                    start_idx = line.lower().find(kw.lower()) + len(kw)
                                                    raw_after = line[start_idx:].strip()
                                                    found_val = clean_extracted_value(raw_after, pos, lg)
                                                    
                                                elif pos == "Below (नीचे)":
                                                    # नीचे वाली लाइन
                                                    if idx + 1 < len(pdf_lines):
                                                        raw_below = pdf_lines[idx + 1].strip()
                                                        found_val = clean_extracted_value(raw_below, pos, lg)
                                                break
                                    elif lg:
                                        # बिना कीवर्ड वाले फ़ील्ड्स (जैसे ROSCTL)
                                        found_val = clean_extracted_value(pdf_text, pos, lg)
                                        
                                    # अगर खाली है और डिस्काउंट/डिडक्शन है तो 0 लिखें
                                    if not found_val and ("deduction" in field.lower() or "discount" in field.lower()):
                                        found_val = "0"
                                        
                                    ws[target_cell] = found_val
                                    
                                    if "inv. no" in field.lower() or "invoice no" in field.lower():
                                        if found_val: invoice_number = found_val

                            # 2. 🚀 टेबल आइटम्स एक्सट्रैक्शन
                            item_start_row = 2
                            parsed_item_rows = []
                            
                            for line in pdf_lines:
                                line_str = line.strip()
                                # HS Code से शुरू होने वाली लाइन
                                if re.match(r'^6302\d{4}', line_str) or re.match(r'^\d{8}', line_str):
                                    parts = [p.strip() for p in line_str.split() if p.strip()]
                                    if len(parts) >= 4:
                                        parsed_item_rows.append(parts)

                            if parsed_item_rows:
                                for idx, item in enumerate(parsed_item_rows):
                                    curr_row = item_start_row + idx
                                    for field, r_info in rules.items():
                                        col = r_info.get("cell", "").strip()
                                        lg = r_info.get("logic", "").strip()
                                        
                                        if "table_item" in lg.lower() and len(col) == 1:
                                            val = ""
                                            if "ritc" in field.lower() or "hs code" in field.lower(): val = item[0] if len(item) > 0 else ""
                                            elif "product" in field.lower() or "description" in field.lower(): val = item[1] if len(item) > 1 else ""
                                            elif "qty" in field.lower(): val = item[2] if len(item) > 2 else ""
                                            elif "goods value" in field.lower() or "amount" in field.lower(): val = item[-2] if len(item) > 4 else ""
                                            
                                            ws[f"{col}{curr_row}"] = val

                            # 3. फ़ाइल जनरेट करना
                            output = BytesIO()
                            wb.save(output)
                            
                            short_shipper = selected_shipper.split(" ")[0].lower()
                            clean_inv = re.sub(r'[\\/*?:"<>|]', "", invoice_number)
                            final_filename = f"{clean_inv}_{short_shipper}.xlsx"
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": final_filename,
                                "data": output.getvalue()
                            }
                            st.success(f"🎉 इनवॉइस '{final_filename}' सटीक डेटा के साथ जनरेट हो गया है!")
                    
                    if st.session_state.get("processed_file_ready", None):
                        st.write("")
                        st.download_button(
                            label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                            data=st.session_state["processed_file_ready"]["data"],
                            file_name=st.session_state["processed_file_ready"]["filename"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.session_state["processed_file_ready"] = None
