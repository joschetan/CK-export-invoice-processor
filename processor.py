import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

# 🤖 डेटा एक्सट्रैक्शन एआई इंजन
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
                
        # ⬇️ पोजिशन: Below (नीचे) - तालिका (Table) के लिए स्मार्ट लॉजिक
        elif position == "Below (नीचे)":
            lines = full_text.split("\n")
            for i, line in enumerate(lines):
                if keyword.strip().lower() in line.lower():
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        parts = next_line.split()
                        
                        if len(parts) >= 3:
                            # वेल्सपन टेबल लॉजिक: Container No और Size निकालना
                            if "container" in field_name.lower():
                                return parts[1]
                            elif "size" in field_name.lower() or "con size" in keyword.lower():
                                return parts[2]
                        
                        return parts[0] if parts else ""
                        
    except Exception:
        return ""
    return ""

def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("यहाँ शिपर चुनें, पीडीएफ अपलोड करें और सीधे एक्सेल डाउनलोड करें।")
    
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
                    
                    # 🚀 प्रोसेस और डायरेक्ट डाउनलोड ट्रिगर
                    if st.button("🚀 Process & Generate Excel", type="primary"):
                        with st.spinner("पीडीएफ स्कैन करके एक्सेल शीट तैयार की जा रही है..."):
                            rules = shipper_info.get("mapping_rules", {})
                            
                            # 1. ओरिजिनल टेम्पलेट लोड करना
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            
                            if "INV" in wb.sheetnames:
                                ws = wb["INV"]
                            else:
                                ws = wb.active
                            
                            # 2. बैकएंड में ही पीडीएफ पढ़ना और सीधे एक्सेल की Cells में लिखना
                            for field, r_info in rules.items():
                                kw = r_info.get("keyword", "")
                                pos = r_info.get("position", "Right (आगे)")
                                target_cell = r_info.get("cell", "").strip()
                                
                                if kw and target_cell:
                                    invoice_file.seek(0)
                                    found_val = extract_value_from_pdf(invoice_file, kw, pos, field_name=field)
                                    ws[target_cell] = found_val
                            
                            # 3. फाइल को मेमोरी में सेव करना
                            output = BytesIO()
                            wb.save(output)
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": f"{selected_shipper}_Smart_Filled_Job.xlsx",
                                "data": output.getvalue()
                            }
                            st.success("🎉 एक्सेल फ़ाइल सफलतापूर्वक तैयार हो गई है!")
                    
                    # 📥 सीधा डाउनलोड बटन (बिना किसी रीव्यू स्क्रीन के)
                    if st.session_state.get("processed_file_ready", None):
                        st.write("")
                        st.download_button(
                            label="📥 भरी हुई एक्सेल फ़ाइल तुरंत डाउनलोड करें",
                            data=st.session_state["processed_file_ready"]["data"],
                            file_name=st.session_state["processed_file_ready"]["filename"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        # डाउनलोड बटन दिखाने के बाद स्टेट क्लियर करें ताकि अगली फ़ाइल पर पुराना डेटा न दिखे
                        st.session_state["processed_file_ready"] = None
