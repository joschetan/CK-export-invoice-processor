import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("यहाँ शिपर चुनें, पीडीएफ अपलोड करें और मल्टी-पेज टेबल डेटा सीधे एक्सेल में डाउनलोड करें।")
    
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
                        with st.spinner("सभी पेजों से टेबल ग्रिड और हेडर साफ़ किए जा रहे हैं..."):
                            rules = shipper_info.get("mapping_rules", {})
                            
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            ws = wb["INV"] if "INV" in wb.sheetnames else wb.active
                            
                            pdf_text = ""
                            pdf_tables = []
                            
                            # 📑 मल्टी-पेज रीडिंग लूप
                            with pdfplumber.open(invoice_file) as pdf:
                                for page in pdf.pages:
                                    t = page.extract_text()
                                    if t: pdf_text += t + "\n"
                                    
                                    extracted_tbls = page.extract_tables()
                                    if extracted_tbls:
                                        pdf_tables.extend(extracted_tbls)
                            
                            invoice_number = "INV"
                            
                            # 1. सिंगल फ़ील्ड्स प्रोसेस करना
                            for field, r_info in rules.items():
                                kw = r_info.get("keyword", "").strip()
                                pos = r_info.get("position", "Right (आगे)")
                                target_cell = r_info.get("cell", "").strip()
                                lg = r_info.get("logic", "").strip()
                                
                                if "table_item" not in lg.lower() and kw and target_cell and len(target_cell) > 1:
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

                            # 2. 🚀 मल्टी-पेज क्लीन टेबल लूप
                            start_row = 2 
                            actual_item_rows = []
                            
                            for tbl in pdf_tables:
                                for row in tbl:
                                    if row:
                                        # क्लीनर फ़िल्टर: सिर्फ वही रो उठाएगा जिसमें असली कोड/नंबर हो (टेबल के हेडर टेक्स्ट को छोड़ देगा)
                                        row_cells_str = " ".join([str(c).strip() for c in row if c])
                                        
                                        # अगर रो में 6 से 8 अंकों का RITC/HS Code मौजूद है (जैसे 63026090)
                                        if any(str(cell).strip().isdigit() and len(str(cell).strip()) >= 6 for cell in row if cell):
                                            # डबल हेडर प्रोटेक्शन: अगर रो में गलती से 'HS Code' शब्द लिखा हो तो उसे हटाओ
                                            if "hs code" not in row_cells_str.lower() and "description" not in row_cells_str.lower():
                                                actual_item_rows.append([str(c).strip() if c else "" for c in row])
                            
                            # एक्सेल में सिंक करना
                            if actual_item_rows:
                                for item_idx, item_row in enumerate(actual_item_rows):
                                    current_excel_row = start_row + item_idx
                                    
                                    for field, r_info in rules.items():
                                        target_col = r_info.get("cell", "").strip()
                                        lg = r_info.get("logic", "").strip()
                                        
                                        if "table_item" in lg.lower() and target_col and len(target_col) == 1:
                                            val_to_write = ""
                                            if "ritc" in field.lower() or "hs code" in field.lower(): val_to_write = item_row[0]
                                            elif "product" in field.lower() or "description" in field.lower(): val_to_write = item_row[1]
                                            elif "net wt" in field.lower() or "gross wt" in field.lower(): val_to_write = item_row[2]
                                            elif "dbk" in field.lower(): val_to_write = item_row[3]
                                            elif "qty" in field.lower() or "quantity" in field.lower(): val_to_write = item_row[4]
                                            
                                            ws[f"{target_col}{current_excel_row}"] = val_to_write
                            
                            output = BytesIO()
                            wb.save(output)
                            
                            short_shipper = selected_shipper.split(" ")[0].lower()
                            clean_inv = re.sub(r'[\\/*?:"<>|]', "", invoice_number)
                            final_filename = f"{clean_inv}_{short_shipper}.xlsx"
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": final_filename,
                                "data": output.getvalue()
                            }
                            st.success(f"🎉 सभी पेजों से कुल {len(actual_item_rows)} आइटम्स सफलतापुर्वक एक्सेल में राइट कर दिए गए हैं!")
                    
                    if st.session_state.get("processed_file_ready", None):
                        st.write("")
                        st.download_button(
                            label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                            data=st.session_state["processed_file_ready"]["data"],
                            file_name=st.session_state["processed_file_ready"]["filename"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.session_state["processed_file_ready"] = None
