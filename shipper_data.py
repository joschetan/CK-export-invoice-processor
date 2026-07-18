import streamlit as st

def render_shipper_data():
    st.header("🏢 Shipper Upload Controls Setup")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if not shippers_list:
        st.warning("⚠️ पहले '2. Add Master Data' में जाकर शिपर का नाम रजिस्टर करें।")
    else:
        selected_shipper = st.selectbox("शिपर का नाम चुनें या सर्च करें:", shippers_list, index=None, placeholder="यहाँ शिपर का नाम टाइप या सेलेक्ट करें...")
        
        if selected_shipper:
            st.write(f"### ⚙️ कॉन्फ़िगर करें: **{selected_shipper}**")
            st.info("इस शिपर के लिए कौन-कौन से अपलोड ऑप्शंस एक्टिव करने हैं? टिक करें:")
            
            selected_uploads = []
            current_allowed = st.session_state["shipper_database"][selected_shipper].get("allowed_uploads", [])
            
            for t in st.session_state["master_types"]:
                is_checked = t in current_allowed
                if st.checkbox(t, value=is_checked, key=f"chk_{selected_shipper}_{t}"):
                    selected_uploads.append(t)
            
            if st.button("🔒 सेव शिपर कॉन्फ़िगरेशन"):
                st.session_state["shipper_database"][selected_shipper]["allowed_uploads"] = selected_uploads
                st.success(f"✅ '{selected_shipper}' के लिए अपलोड ऑप्शंस अपडेट कर दिए गए हैं!")

            allowed_buttons = st.session_state["shipper_database"][selected_shipper].get("allowed_uploads", [])
            if allowed_buttons:
                st.write("---")
                st.subheader("📁 आवश्यक फ़ाइलें अपलोड करें")
                
                for btn_name in allowed_buttons:
                    # फाइल पहले से है या नहीं चेक करना
                    has_file = btn_name in st.session_state["shipper_database"][selected_shipper]["uploaded_files"]
                    
                    if has_file:
                        st.success(f"✅ {btn_name} अपलोडेड है।")
                        if st.button(f"🗑️ Delete & Replace", key=f"del_ship_file_{selected_shipper}_{btn_name}"):
                            del st.session_state["shipper_database"][selected_shipper]["uploaded_files"][btn_name]
                            st.rerun()
                    else:
                        f_upload = st.file_uploader(f"➡️ Upload: {btn_name}", type=["xlsx", "xls", "pdf"], key=f"upload_{selected_shipper}_{btn_name}")
                        if f_upload:
                            st.session_state["shipper_database"][selected_shipper]["uploaded_files"][btn_name] = f_upload.getvalue()
                            st.success(f"{btn_name} सेव्ड।")
                            st.rerun()
