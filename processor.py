import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

# 📑 पीडीएफ से डेटा ढूंढने का जादुई फंक्शन (AI Engine)
def extract_value_from_pdf(pdf_file, keyword, position):
    if not keyword:
        return ""
        
    try:
        full_text = ""
        # पूरी पीडीएफ का टेक्स्ट एक साथ जोड़ना
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        # इनवॉइस में कभी-कभी एक से ज़्यादा स्पेस होते हैं, उन्हें साफ़ करना
        full_text_clean = re.sub(r'\s+', ' ', full_text)
        keyword_clean = re.sub(r'\s+', ' ', keyword.strip())
        
        if keyword_clean not in full_text_clean:
            return ""
            
        # पोजिशन के हिसाब से डेटा निकालना
        if position == "Right (आगे)":
            # कीवर्ड के ठीक आगे वाला हिस्सा ढूंढना
            pattern = re.escape(keyword_clean) + r'\s*[:\-]?\s*([^\n]+)'
            match = re.search(pattern, full_text)
            if match:
                # सिर्फ पहला शब्द या वैल्यू उठाना (जैसे MUNDRA या USA)
                val = match.group(1).strip().split(" ")[0]
                return val
                
        elif position == "Below (नीचे)":
            # लाइनों को अलग-अलग करके देखना कि कीवर्ड के नीचे वाली लाइन में क्या है
            lines = full_text.split("\n")
            for i, line in enumerate(lines):
                if keyword.strip().lower() in line.lower():
                    if i + 1 < len(lines):
                        # नीचे वाली लाइन का पहला हिस्सा उठाना
                        return lines[i+1].strip().split(" ")[0]
                        
    except Exception as e:
        return f"Error: {str(e)}"
    return ""

def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("यहाँ शिपर चुनें और इनवॉइस अपलोड करके डेटा प्रोसेस करें।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if not shippers_list:
        st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है। कृपया एडमिन पैनल में जाकर शिपर रजिस्टर करें।")
    else:
        # शिपर सेलेक्ट बॉक्स (जैसे ही यूजर 'WELSPUN GLOBAL BRANDS LIMITED' चुनेगा)
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=None, placeholder="यहाँ शिपर का नाम चुनें...")
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if "Full Job Excel Format File" not in shipper_info.get("uploaded_files", {}):
                st.error(f"❌ त्रुटि: इस शिपर के लिए मुख्य 'Full Job Excel Format File' अपलोड नहीं है!")
            else:
                st.success(f"🔒 '{selected_shipper}' का प्रोफाइल और AI रूल्स लोड हो गए हैं।")
                
                # इनवॉइस अपलोड करने का बॉक्स
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF Invoice अपलोड करें", type=["pdf"])
                
                if invoice_file:
                    st.write("---")
                    
                    # 🚀 बटन दबाते ही असली पीडीएफ स्कैनिंग शुरू होगी
                    if st.button("🚀 Process & Read PDF Data", type="primary"):
                        st.info("आपके द्वारा बनाए गए नियमों के आधार पर PDF इनवॉइस को स्कैन किया जा रहा है...")
                        
                        rules = shipper_info.get("mapping_rules", {})
                        extracted_data = {}
                        
                        # एक-एक नियम पर लूप चलाकर पीडीएफ से लाइव वैल्यू निकालना
                        for field, r_info in rules.items():
                            kw = r_info.get("keyword", "")
                            pos = r_info.get("position", "Right (आगे)")
                            
                            if kw:
                                # इनवॉइस फ़ाइल को दोबारा शुरुआत से पढ़ने के लिए पॉइंटर सेट करना
                                invoice_file.seek(0)
                                found_val = extract_value_from_pdf(invoice_file, kw, pos)
                                extracted_data[field] = found_val
                            else:
                                extracted_data[field] = ""
                                
                        st.session_state["extracted_live_data"] = extracted_data
                        st.session_state["process_done"] = True
                    
                    # 📝 लाइव समीक्षा स्क्रीन (Review & Verify Screen)
                    if st.session_state.get("process_done", False):
                        st.subheader("📝 भाई, इनवॉइस से निकाला गया डेटा एक बार चेक कर लो:")
                        st.caption("आप चाहें तो किसी भी वैल्यू को यहीं हाथ से एडिट करके बदल भी सकते हैं।")
                        
                        live_data = st.session_state.get("extracted_live_data", {})
                        rules = shipper_info.get("mapping_rules", {})
                        
                        final_verified_data = {}
                        
                        # स्क्रीन पर बक्से बनाना जहाँ डेटा दिखाई दे
                        for field, value in live_data.items():
                            cell_info = rules.get(field, {}).get("cell", "Not Set")
                            if cell_info and cell_info != "Not Set":
                                final_verified_data[field] = st.text_input(
                                    f"📍 {field} (जाएगा Cell {cell_info} में)", 
                                    value=value, 
                                    key=f"live_{field}"
                                )
                        
                        st.write("---")
                        
                        # 💾 फाइनल एक्सेल जनरेशन बटन
                        if st.button("🔒 सब सही है, एक्सेल फाइल तैयार करो!"):
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            
                            # आपकी रिक्वायरमेंट के अनुसार 'INV' शीट को सेलेक्ट करना
                            if "INV" in wb.sheetnames:
                                ws = wb["INV"]
                            else:
                                ws = wb.active
                            
                            # एक्सेल शीट के सही खानों (Cells) में डेटा लिखना
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
                        
                        # डाउनलोड बटन दिखाना
                        if st.session_state.get("processed_file_ready", None):
                            st.write("---")
                            st.download_button(
                                label="📥 भरी हुई एक्सेल फ़ाइल तुरंत डाउनलोड करें",
                                data=st.session_state["processed_file_ready"]["data"],
                                file_name=st.session_state["processed_file_ready"]["filename"],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
