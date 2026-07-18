import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

# 🤖 डेटा एक्सट्रैक्शन का सुधरा हुआ और पक्का एआई इंजन
def extract_value_from_pdf(pdf_file, keyword, position, field_name=""):
    if not keyword:
        return ""
        
    try:
        full_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        full_text_clean = re.sub(r'\s+', ' ', full_text)
        keyword_clean = re.sub(r'\s+', ' ', keyword.strip())
        
        if keyword_clean not in full_text_clean:
            return ""
            
        # ➡️ पोजिशन: Right (आगे)
        if position == "Right (आगे)":
            pattern = re.escape(keyword_clean) + r'\s*[:\-]?\s*([^\n]+)'
            match = re.search(pattern, full_text)
            if match:
                val = match.group(1).strip().split(" ")[0]
                return val
                
        # ⬇️ पोजिशन: Below (नीचे) - तालिका (Table) के लिए विशेष स्मार्ट लॉजिक
        elif position == "Below (नीचे)":
            lines = full_text.split("\n")
            for i, line in enumerate(lines):
                if keyword.strip().lower() in line.lower():
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        parts = next_line.split()
                        
                        if len(parts) >= 3:
                            # वेल्सपन टेबल लॉजिक: [SrNo(1), ContainerNo(GAOU...), Size(40HC), ...]
                            if "container" in field_name.lower():
                                return parts[1] # दूसरे नंबर का बड़ा कोड (Container No) उठाएगा
                            elif "size" in field_name.lower() or "con size" in keyword.lower():
                                return parts[2] # तीसरे नंबर का कोड (Size) उठाएगा
                        
                        # अगर नॉर्मल टेक्स्ट है तो पूरी लाइन का पहला शब्द
                        return parts[0] if parts else ""
                        
    except Exception:
        return ""
    return ""

def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("यहाँ शिपर चुनें और इनवॉइस अपलोड करके डेटा प्रोसेस करें।")
    
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
                    
                    if st.button("🚀 Process & Read PDF Data", type="primary"):
                        st.info("इनवॉइस को स्कैन किया जा रहा है...")
                        
                        rules = shipper_info.get("mapping_rules", {})
                        extracted_data = {}
                        
                        for field, r_info in rules.items():
                            kw = r_info.get("keyword", "")
                            pos = r_info.get("position", "Right (आगे)")
                            
                            if kw:
                                invoice_file.seek(0)
                                # फ़ील्ड का नाम भी भेज रहे हैं ताकि नीचे वाला स्मार्ट लॉजिक काम कर सके
                                found_val = extract_value_from_pdf(invoice_file, kw, pos, field_name=field)
                                extracted_data[field] = found_val
                            else:
                                extracted_data[field] = ""
                                
                        st.session_state["extracted_live_data"] = extracted_data
                        st.session_state["process_done"] = True
                    
                    # 📝 लाइव समीक्षा स्क्रीन (Review & Verify) - एकदम साफ और शॉर्ट!
                    if st.session_state.get("process_done", False):
                        live_data = st.session_state.get("extracted_live_data", {})
                        rules = shipper_info.get("mapping_rules", {})
                        
                        final_verified_data = {}
                        has_visible_fields = False
                        
                        # पहले लूप चलाकर चेक करना कि क्या कुछ डेटा मिला भी है
                        for field, value in live_data.items():
                            if value and value.strip() != "":
                                if not has_visible_fields:
                                    st.subheader("📝 भाई, इनवॉइस से मिला हुआ डेटा चेक कर लो:")
                                    st.caption("जो डेटा नहीं मिला, उसे सिस्टम ने अपने आप बैकएंड में ब्लैंक (खाली) छोड़ दिया है ताकि आपका समय बचे।")
                                    has_visible_fields = True
                                
                                cell_info = rules.get(field, {}).get("cell", "Not Set")
                                final_verified_data[field] = st.text_input(
                                    f"📍 {field} (जाएगा Cell {cell_info} में)", 
                                    value=value, 
                                    key=f"live_{field}"
                                )
                            else:
                                # जो डेटा नहीं मिला, उसे स्क्रीन पर दिखाए बिना सीधे ब्लैंक सेट कर देना
                                final_verified_data[field] = ""
                        
                        if not has_visible_fields:
                            st.warning("⚠️ इस इनवॉइस से कोई भी मैचिंग डेटा नहीं मिल पाया। कृपया एडमिन पैनल में कीवर्ड्स चेक करें।")
                        
                        st.write("---")
                        
                        # 💾 फाइनल एक्सेल जनरेशन
                        if st.button("🔒 सब सही है, एक्सेल फाइल तैयार करो!"):
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            
                            if "INV" in wb.sheetnames:
                                ws = wb["INV"]
                            else:
                                ws = wb.active
                            
                            # स्क्रीन से वेरिफाइड (या ऑटो-ब्लैंक) डेटा को एक्सेल में लिखना
                            for field, final_val in final_verified_data.items():
                                target_cell = rules.get(field, {}).get("cell", "").strip()
                                if target_cell:
                                    ws[target_cell] = final_val
                            
                            output = BytesIO()
                            wb.save(output)
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": f"{selected_shipper}_Smart_Filled_Job.xlsx",
                                "data": output.getvalue()
                            }
                            st.success("🎉 आपकी एक्सेल शीट 'INV' सफलतापूर्वक भर दी गई है!")
                        
                        # डाउनलोड बटन
                        if st.session_state.get("processed_file_ready", None):
                            st.write("---")
                            st.download_button(
                                label="📥 भरी हुई एक्सेल फ़ाइल तुरंत डाउनलोड करें",
                                data=st.session_state["processed_file_ready"]["data"],
                                file_name=st.session_state["processed_file_ready"]["filename"],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
