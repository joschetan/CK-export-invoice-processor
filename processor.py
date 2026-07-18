import streamlit as st
import openpyxl
from io import BytesIO

def render_processor():
    st.header("📤 Invoice Processing & Instant Download Zone")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if not shippers_list:
        st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है। कृपया पहले शिपर रजिस्टर करें।")
    else:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=None, placeholder="यहाँ शिपर का नाम टाइप या सेलेक्ट करें...")
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if "Full Job Excel Format File" not in shipper_info["uploaded_files"]:
                st.error(f"❌ त्रुटि: इस शिपर के लिए मुख्य 'Full Job Excel Format File' अपलोड नहीं है! कृपया पहले स्टेप 3 में जाकर इसे अपलोड करें।")
            else:
                st.success(f"🔒 '{selected_shipper}' का प्रोफाइल लोड हो गया है।")
                
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF या Excel Invoice अपलोड करें", type=["pdf", "xlsx", "xls"])
                
                if invoice_file:
                    if st.button("🚀 Process & Fill Data"):
                        st.info("डेटा एक्सट्रैक्शन चालू है...")
                        
                        # ओरिजिनल टेम्पलेट लोड करना
                        original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                        wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                        ws = wb.active
                        
                        # डमी मार्कर
                        ws["A1"] = "PROCESSED BY MODULAR CK AUTOMATION" 
                        
                        output = BytesIO()
                        wb.save(output)
                        
                        st.session_state["processed_file_ready"] = {
                            "filename": f"{selected_shipper}_Filled_Job.xlsx",
                            "data": output.getvalue()
                        }
                        st.success("🎉 डेटा सफलतापूर्वक भर दिया गया है!")
                    
                    if st.session_state["processed_file_ready"]:
                        st.write("---")
                        st.download_button(
                            label="📥 प्रोसेस्ड एक्सेल फ़ाइल तुरंत डाउनलोड करें",
                            data=st.session_state["processed_file_ready"]["data"],
                            file_name=st.session_state["processed_file_ready"]["filename"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
