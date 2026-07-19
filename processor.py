import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("यहाँ शिपर चुनें, पीडीएफ अपलोड करें और सीधे 100+ आइटम्स सपोर्ट वाली एक्सेल डाउनलोड करें।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if not shippers_list:
        st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है।")
    else:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=None, placeholder="यहाँ शिपर का नाम चुनें...")
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if "Full Job Excel Format File" not in shipper_info.get("uploaded_files", {}):
                st.error(f"❌ त्रुटि: इस शिपर के लिए मुख्य 'Full Job Excel Format File' अपलोड नहीं है!")
            else:
                st.success(f"🔒 '{selected_shipper}' का प्रोफाइल और AI रूल्स लोड हो गए हैं।")
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF Invoice अपलोड करें", type=["pdf"])
                
                if invoice_file:
                    st.write("---")
                    
                    if st.button("🚀 Process & Generate Excel", type="primary"):
                        with st.spinner("पीडीएफ से 100+ आइटम्स और सिंगल डेटा स्कैन किया जा रहा है..."):
                            rules = shipper_info.get("mapping_rules", {})
                            
                            # 1. एक्सेल टेम्पलेट लोड करना
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            ws = wb["INV"] if "INV" in wb.sheetnames else wb.active
                            
                            # 2. पीडीएफ को पूरी तरह रीड करना (टेक्स्ट और टेबल्स दोनों)
                            pdf_text = ""
                            pdf_tables = []
                            
                            with pdfplumber.open(invoice_file) as pdf:
                                for page in pdf.pages:
                                    t = page.extract_text()
                                    if t: pdf_text += t + "\n"
                                    
                                    extracted_tbls = page.extract_tables()
                                    if extracted_tbls:
                                        pdf_tables.extend(extracted_tbls)
                            
                            invoice_number = "INV"
                            
                            # 3. पहले सिंगल एंट्री वाले फ़ील्ड्स (जैसे Inv No, Port) प्रोसेस करना
                            for field, r_info in rules.items():
                                kw = r_info.get("keyword", "").strip()
                                pos = r_info.get("position", "Right (आगे)")
                                target_cell = r_info.get("cell", "").strip()
                                lg = r_info.get("logic", "").strip()
                                
                                # अगर यह टेबल आइटम नहीं है (नॉर्मल सिंगल एंट्री है)
                                if "table_item" not in lg.lower() and kw and target_cell and len(target_cell) > 1:
                                    # सामान्य राइट/बिलो लॉजिक से सिंगल वैल्यू निकालना
                                    found_val = ""
                                    full_text_clean = re.sub(r'\s+', ' ', pdf_text)
                                    keyword_clean = re.sub(r'\s+', ' ', kw)
                                    
                                    if keyword_clean in full_text_clean:
                                        if pos == "Right (आगे)":
                                            pattern = re.escape(keyword_clean) + r'\s*[:\-]?\s*([^\n]+)'
                                            match = re.search(pattern, pdf_text)
                                            if match: found_val = match.group(1).strip().split(" ")[0]
                                        elif pos == "Below (नीचे)":
                                            lines = pdf_text.split("\n")
                                            for idx, line in enumerate(lines):
                                                if kw.lower() in line.lower() and idx + 1 < len(lines):
                                                    parts = lines[idx+1].strip().split()
                                                    if parts: found_val = parts[0]
                                    
                                    ws[target_cell] = found_val
                                    if "inv. no." in field.lower() or "invoice no" in field.lower():
                                        if found_val: invoice_number = found_val

                            # 4. 🚀 अब आया जादू: आइटम्स की पूरी टेबल (Multi-Row) को प्रोसेस करना
                            # हम मान कर चल रहे हैं कि डेटा Row 2 से लिखना शुरू करना है
                            start_row = 2 
                            
                            # पीडीएफ से निकाली गई सभी टेबल्स में से असली आइटम टेबल ढूंढना
                            actual_item_rows = []
                            for tbl in pdf_tables:
                                for row in tbl:
                                    # अगर रो में HS Code या आइटम का कोई हिंट मिले (जैसे 63026090)
                                    if row and any(str(cell).strip().isdigit() and len(str(cell).strip()) >= 6 for cell in row if cell):
                                        actual_item_rows.append([str(c).strip() if c else "" for c in row])
                            
                            if actual_item_rows:
                                # हर एक आइटम रो पर लूप चलाना
                                for item_idx, item_row in enumerate(actual_item_rows):
                                    current_excel_row = start_row + item_idx
                                    
                                    # हर फ़ील्ड के लिए चेक करना कि उसका कॉलम अक्षर क्या है
                                    for field, r_info in rules.items():
                                        target_col = r_info.get("cell", "").strip() # यहाँ सिर्फ 'J', 'K' आदि होगा
                                        lg = r_info.get("logic", "").strip()
                                        
                                        if "table_item" in lg.lower() and target_col and len(target_col) == 1:
                                            val_to_write = ""
                                            
                                            # इनवॉइस की टेबल पोजीशन मैपिंग
                                            if "ritc" in field.lower() or "hs code" in field.lower():
                                                val_to_write = item_row[0] # पहला कॉलम HS Code है
                                            elif "product" in field.lower() or "description" in field.lower():
                                                val_to_write = item_row[1] # दूसरा कॉलम Description
                                            elif "net wt" in field.lower() or "gross wt" in field.lower():
                                                val_to_write = item_row[2] # तीसरा कॉलम Weight
                                            elif "dbk" in field.lower():
                                                val_to_write = item_row[3] # चौथा कॉलम Drawback Sr
                                            elif "qty" in field.lower() or "quantity" in field.lower():
                                                val_to_write = item_row[4] # पांचवा कॉलम Quantity
                                            
                                            # सही एक्सेल सेल एड्रेस बनाना (जैसे J + 2 = J2, J + 3 = J3)
                                            cell_address = f"{target_col}{current_excel_row}"
                                            ws[cell_address] = val_to_write
                            
                            # 5. एक्सेल फ़ाइल को सेव और तैयार करना
                            output = BytesIO()
                            wb.save(output)
                            
                            short_shipper = selected_shipper.split(" ")[0].lower()
                            clean_inv = re.sub(r'[\\/*?:"<>|]', "", invoice_number)
                            final_filename = f"{clean_inv}_{short_shipper}.xlsx"
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": final_filename,
                                "data": output.getvalue()
                            }
                            st.success(f"🎉 100+ आइटम ग्रिड के साथ फ़ाइल '{final_filename}' तैयार है!")
                    
                    # डाउनलोड बटन
                    if st.session_state.get("processed_file_ready", None):
                        st.write("")
                        st.download_button(
                            label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                            data=st.session_state["processed_file_ready"]["data"],
                            file_name=st.session_state["processed_file_ready"]["filename"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.session_state["processed_file_ready"] = None
