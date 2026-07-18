import streamlit as st
import openpyxl
from io import BytesIO

def render_processor():
    st.header("📤 Invoice Processing & Instant Download Zone")
    st.caption("यहाँ शिपर चुनकर इनवॉइस और उसके संबंधित डॉक्यूमेंट अपलोड करके डेटा प्रोसेस करें।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if not shippers_list:
        st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है। कृपया एडमिन पैनल में जाकर शिपर रजिस्टर करें।")
    else:
        # Search-cum-Dropdown बॉक्स
        selected_shipper = st.selectbox(
            "किस शिपर का इनवॉइस प्रोसेस करना है?", 
            shippers_list, 
            index=None, 
            placeholder="यहाँ शिपर का नाम टाइप या सेलेक्ट करें..."
        )
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            # 1. चेक करना कि क्या मुख्य एक्सेल फॉर्मेट अपलोडेड है
            if "Full Job Excel Format File" not in shipper_info.get("uploaded_files", {}):
                st.error(f"❌ त्रुटि: इस शिपर के लिए मुख्य 'Full Job Excel Format File' अपलोड नहीं है! कृपया पहले एडमिन सेटिंग्स में जाकर इसे अपलोड करें।")
            else:
                st.success(f"🔒 '{selected_shipper}' का प्रोफाइल लोड हो गया है।")
                
                # 2. इनवॉइस अपलोड करने का मुख्य बटन
                st.subheader("📄 1. Main Invoice File")
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF या Excel Invoice अपलोड करें", type=["pdf", "xlsx", "xls"], key="main_invoice")
                
                # 3. शिपर के अन्य आवश्यक डॉक्यूमेंट्स अपलोड करने के बटन्स (जो एडमिन ने सेट किए हैं)
                allowed_buttons = shipper_info.get("allowed_uploads", [])
                extra_docs = {}
                
                if len(allowed_buttons) > 1: # अगर 'Full Job Excel' के अलावा भी कोई डॉक्यूमेंट सेट है
                    st.write("---")
                    st.subheader("📁 2. Related Documents (Optional/Required as per profile)")
                    
                    for btn_name in allowed_buttons:
                        if btn_name != "Full Job Excel Format File": # मुख्य फ़ाइल को छोड़कर बाकी दिखाएं
                            ext_file = st.file_uploader(f"Upload: {btn_name}", type=["xlsx", "xls", "pdf"], key=f"proc_ext_{btn_name}")
                            if ext_file:
                                extra_docs[btn_name] = ext_file.getvalue()
                
                # 4. प्रोसेसिंग और डाउनलोड सेक्शन
                if invoice_file:
                    st.write("---")
                    if st.button("🚀 Process & Fill Data"):
                        st.info("डेटा एक्सट्रैक्शन चालू है...")
                        
                        # ओरिजिनल टेम्पलेट लोड करना
                        original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                        wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                        ws = wb.active
                        
                        # डमी मार्कर (असली कोडिंग लॉजिक यहाँ आएगा)
                        ws["A1"] = "PROCESSED BY LIVE SAVE CK AUTOMATION" 
                        
                        output = BytesIO()
                        wb.save(output)
                        
                        st.session_state["processed_file_ready"] = {
                            "filename": f"{selected_shipper}_Filled_Job.xlsx",
                            "data": output.getvalue()
                        }
                        st.success("🎉 डेटा सफलतापूर्वक भर दिया गया है!")
                    
                    if st.session_state["processed_file_ready"]:
                        st.download_button(
                            label="📥 प्रोसेस्ड एक्सेल फ़ाइल तुरंत डाउनलोड करें",
                            data=st.session_state["processed_file_ready"]["data"],
                            file_name=st.session_state["processed_file_ready"]["filename"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
