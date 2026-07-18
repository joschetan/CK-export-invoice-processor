import streamlit as st
import openpyxl
from io import BytesIO

def render_processor():
    st.header("📤 Invoice Processing Zone")
    st.caption("यहाँ शिपर चुनें और इनवॉइस अपलोड करके डेटा प्रोसेस करें।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if not shippers_list:
        st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है। कृपया एडमिन पैनल में जाकर शिपर रजिस्टर करें।")
    else:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=None, placeholder="यहाँ शिपर का नाम चुनें...")
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if "Full Job Excel Format File" not in shipper_info.get("uploaded_files", {}):
                st.error(f"❌ त्रुटि: इस शिपर के लिए मुख्य 'Full Job Excel Format File' अपलोड नहीं है! कृपया पहले एडमिन सेटिंग्स में जाकर इसे अपलोड करें।")
            else:
                st.success(f"🔒 '{selected_shipper}' का प्रोफाइल और AI रूल्स लोड हो गए हैं।")
                
                invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF या Excel Invoice अपलोड करें", type=["pdf", "xlsx", "xls"])
                
                if invoice_file:
                    st.write("---")
                    
                    # 🤖 एआई एक्सट्रैक्शन सिम्युलेटर (जब आप 'Process' दबाएंगे)
                    if st.button("🚀 Process & Read Data", type="primary"):
                        st.info("आपके द्वारा बनाए गए AI रूल्स के आधार पर PDF इनवॉइस को स्कैन किया जा रहा है...")
                        
                        # नियम लोड करना
                        rules = shipper_info.get("mapping_rules", {})
                        
                        # यह स्टोर करेगा कि पीडीएफ से क्या मिला (अभी हम सैंपल वैल्यू दिखा रहे हैं जिसे यूजर बदल सके)
                        extracted_data = {}
                        
                        # इनवॉइस का डमी टेक्स्ट रीडर (Welspun के इनवॉइस का डमी डेटा दिखाने के लिए)
                        # आगे हम इसमें pdfplumber जोड़ेंगे जो असली पीडीएफ पढ़ेगा
                        for field, r_info in rules.items():
                            if r_info["keyword"] and r_info["cell"]:
                                # उदाहरण के तौर पर Welspun का कुछ डेटा ऑटो-डिटेक्ट दिखाना
                                if "MUNDRA" in r_info["keyword"] or "Loading" in field:
                                    extracted_data[field] = "MUNDRA"
                                elif "Destination" in field or "Country" in field:
                                    extracted_data[field] = "USA"
                                else:
                                    extracted_data[field] = "DETECTED_VALUE"
                            else:
                                extracted_data[field] = ""
                                
                        st.session_state["extracted_live_data"] = extracted_data
                        st.session_state["process_done"] = True
                    
                    # 📝 लाइव समीक्षा स्क्रीन (Review & Verify Board) - बिल्कुल हिंदी में बात करेगा!
                    if st.session_state.get("process_done", False):
                        st.subheader("📝 भाई, इनवॉइस से निकाला गया डेटा एक बार चेक कर लो:")
                        st.caption("अगर कोई डेटा गलत बॉक्स में आ गया है या खाली है, तो आप उसे यहीं हाथ से ठीक कर सकते हैं।")
                        
                        live_data = st.session_state.get("extracted_live_data", {})
                        rules = shipper_info.get("mapping_rules", {})
                        
                        final_verified_data = {}
                        
                        # यूजर को एडिट करने का मौका देना
                        for field, value in live_data.items():
                            cell_info = rules.get(field, {}).get("cell", "Not Set")
                            if cell_info != "Not Set" and rules.get(field, {}).get("keyword", ""):
                                final_verified_data[field] = st.text_input(
                                    f"📍 {field} (यह एक्सेल की Cell {cell_info} में जाएगा)", 
                                    value=value, 
                                    key=f"live_{field}"
                                )
                        
                        st.write("---")
                        
                        # 💾 फाइनल एक्सेल जनरेशन बटन
                        if st.button("🔒 सब सही है, एक्सेल फाइल तैयार करो!"):
                            # ओरिजिनल टेम्पलेट लोड करना
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            
                            # आपकी रिक्वायरमेंट के अनुसार 'INV' शीट में डेटा लिखना
                            if "INV" in wb.sheetnames:
                                ws = wb["INV"]
                            else:
                                ws = wb.active # अगर INV शीट नहीं मिली तो एक्टिव शीट
                            
                            # आपके द्वारा स्क्रीन पर वेरिफाइड डेटा को सही सेल्स में लिखना
                            for field, final_val in final_verified_data.items():
                                target_cell = rules.get(field, {}).get("cell", "")
                                if target_cell:
                                    ws[target_cell] = final_val
                            
                            output = BytesIO()
                            wb.save(output)
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": f"{selected_shipper}_Smart_Filled_Job.xlsx",
                                "data": output.getvalue()
                            }
                            st.success("🎉 आपकी एक्सेल शीट 'INV' पूरी तरह से भर दी गई है!")
                        
                        # तुरंत डाउनलोड बटन
                        if st.session_state.get("processed_file_ready", None):
                            st.write("---")
                            st.download_button(
                                label="📥 तैयार की हुई एक्सेल फ़ाइल तुरंत डाउनलोड करें",
                                data=st.session_state["processed_file_ready"]["data"],
                                file_name=st.session_state["processed_file_ready"]["filename"],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
