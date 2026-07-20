import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

def extract_custom_logic_value(raw_text, logic_str, keyword_found=""):
    """यूजर के लिखे कस्टम निर्देशों को प्रोसेस करने वाला स्मार्ट एआई लॉजिक"""
    if not logic_str:
        return raw_text.strip()
    
    logic_lower = logic_str.lower()
    
    # 1. ROSCTL / Fixed String match
    if "rosctl" in logic_lower or "write:yes" in logic_lower:
        if "rosctl" in raw_text.lower() or "under rosctl" in raw_text.lower():
            return "YES"
        return "NO"

    # 2. Bracket Extractor () -> (KGS) => KGS
    if "bracket" in logic_lower or "parentheses" in logic_lower or "()" in logic_lower:
        match = re.search(r'\(([^)]+)\)', raw_text)
        if match:
            return match.group(1).strip()

    # 3. Days / Payment terms -> DA/AP/DP/LC
    if "bl / awb date" in logic_lower or "da" in logic_lower:
        if "days" in raw_text.lower() or "bl" in raw_text.lower() or "awb" in raw_text.lower():
            return "DA"

    # 4. IGST / LUT Mode
    if "w/o paymenmt" in logic_lower or "lut" in logic_lower:
        if "w/o paymenmt" in raw_text.lower() or "letter of undertaking" in raw_text.lower() or "lut" in raw_text.lower():
            return "LUT"

    # 5. CART / CTN
    if "cart" in logic_lower or "ctn" in logic_lower:
        if "cart" in raw_text.lower() or "ctn" in raw_text.lower():
            return "CTN"

    # Default fallback
    return raw_text.strip()


def render_processor():
    st.header("📤 Invoice Processing Zone (Advanced Smart Parser)")
    st.caption("यहाँ इनवॉइस अपलोड करें — स्मार्ट AI पार्सर ब्रैकेट, ब्लॉक्स और टेबल डेटा को सही से मैप करेगा।")
    
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
                        with st.spinner("पीडीएफ से स्मार्ट डेटा एक्सट्रैक्ट किया जा रहा है..."):
                            rules = shipper_info.get("mapping_rules", {})
                            
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            ws = wb["INV"] if "INV" in wb.sheetnames else wb.active
                            
                            pdf_text = ""
                            pdf_lines = []
                            pdf_tables = []
                            
                            # 📑 1. पूरे PDF को रीड करना
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
                            
                            # 2. 🎯 सिंगल ब्लॉक/कीवर्ड फ़ील्ड्स निष्कर्षण (Extraction)
                            for field, r_info in rules.items():
                                kw = r_info.get("keyword", "").strip()
                                pos = r_info.get("position", "Right (आगे)")
                                target_cell = r_info.get("cell", "").strip()
                                lg = r_info.get("logic", "").strip()
                                
                                # केवल सिंगल सेल वाले फ़ील्ड्स (जैसे B2, B3, D2)
                                if "table_item" not in lg.lower() and target_cell and len(target_cell) >= 2 and target_cell[1].isdigit():
                                    found_val = ""
                                    
                                    # अगर कीवर्ड खाली है पर कस्टम लॉजिक लिखा है (जैसे ROSCTL)
                                    if not kw and lg:
                                        found_val = extract_custom_logic_value(pdf_text, lg)
                                    elif kw:
                                        # पूरे टेक्स्ट में कीवर्ड ढूंढना
                                        for idx, line in enumerate(pdf_lines):
                                            if kw.lower() in line.lower():
                                                if pos == "Right (आगे)":
                                                    parts = line.split(":", 1)
                                                    if len(parts) > 1 and parts[1].strip():
                                                        found_val = parts[1].strip()
                                                    else:
                                                        # अगर कोलोन नहीं है तो आगे का टेक्स्ट उठाओ
                                                        found_val = line.lower().replace(kw.lower(), "").strip()
                                                
                                                elif pos == "Below (नीचे)":
                                                    # नीचे की 1 या 2 लाइन्स को कैप्चर करना (Address Block के लिए)
                                                    block_lines = []
                                                    for offset in range(1, 3):
                                                        if idx + offset < len(pdf_lines):
                                                            nxt = pdf_lines[idx + offset].strip()
                                                            if nxt and not any(k in nxt.lower() for k in ["port", "pre-carriage", "vessel", "date"]):
                                                                block_lines.append(nxt)
                                                    found_val = " ".join(block_lines) if block_lines else ""
                                                break
                                                
                                        # कस्टम लॉजिक फ़िल्टर लगाना
                                        if lg:
                                            found_val = extract_custom_logic_value(found_val if found_val else pdf_text, lg, kw)
                                    
                                    # डिफ़ॉल्ट 0 लॉजिक (अगर कुछ न मिले)
                                    if not found_val and ("deduction" in field.lower() or "discount" in field.lower()):
                                        found_val = "0"
                                        
                                    ws[target_cell] = found_val
                                    
                                    if "inv. no" in field.lower() or "invoice no" in field.lower():
                                        if found_val: invoice_number = found_val

                            # 3. 🚀 टेबल डेटा एक्सट्रैक्शन (1 or 100+ Items + Container Table)
                            # आइटम्स टेबल (J2 से चालू)
                            item_start_row = 2
                            container_start_row = 20
                            
                            parsed_item_rows = []
                            parsed_container_rows = []
                            
                            # पीडीएफ की सभी लाइनों से साफ़ टेबल पंक्तियाँ पहचानना
                            for line in pdf_lines:
                                line_str = line.strip()
                                # अगर लाइन HS Code (63026090) से शुरू होती है
                                if re.match(r'^6302\d{4}', line_str) or re.match(r'^\d{8}', line_str):
                                    parts = [p.strip() for p in line_str.split() if p.strip()]
                                    if len(parts) >= 4:
                                        parsed_item_rows.append(parts)
                                
                                # कंटेनर टेबल लाइन पहचानना (जैसे GAOU7179835 या HLBU3075456)
                                if re.search(r'[A-Z]{4}\d{7}', line_str):
                                    parts = [p.strip() for p in line_str.split() if p.strip()]
                                    parsed_container_rows.append(parts)

                            # आइटम्स एक्सेल में लिखना
                            if parsed_item_rows:
                                for idx, item in enumerate(parsed_item_rows):
                                    curr_row = item_start_row + idx
                                    # रूल्स के अनुसार कॉलम मैपिंग
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

                            # कंटेनर जानकारी लिखना
                            if parsed_container_rows:
                                for idx, con in enumerate(parsed_container_rows):
                                    curr_row = container_start_row + idx
                                    # कंटेनर नंबर, साइज़ और सील
                                    for part in con:
                                        if re.match(r'^[A-Z]{4}\d{7}$', part):
                                            ws[f"B{curr_row}"] = part # Container No
                                        elif "40HC" in part or "20FT" in part or "40FT" in part:
                                            ws[f"C{curr_row}"] = part # Size
                                        elif re.match(r'^[A-Z0-9]{7,12}$', part) and not part.isdigit():
                                            ws[f"E{curr_row}"] = part # Seal ID

                            # 4. फ़ाइल सेव करना
                            output = BytesIO()
                            wb.save(output)
                            
                            short_shipper = selected_shipper.split(" ")[0].lower()
                            clean_inv = re.sub(r'[\\/*?:"<>|]', "", invoice_number)
                            final_filename = f"{clean_inv}_{short_shipper}.xlsx"
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": final_filename,
                                "data": output.getvalue()
                            }
                            st.success(f"🎉 इनवॉइस '{final_filename}' सफलतापूर्वक प्रोसेस हो गया है!")
                    
                    if st.session_state.get("processed_file_ready", None):
                        st.write("")
                        st.download_button(
                            label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                            data=st.session_state["processed_file_ready"]["data"],
                            file_name=st.session_state["processed_file_ready"]["filename"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.session_state["processed_file_ready"] = None
