import streamlit as st

def render_shipper_data():
    st.header("🏢 Add Shipper Name & Configuration")
    st.caption("नया शिपर रजिस्टर करें और उसके लिए आवश्यक अपलोड बटन्स को टिक करके फाइलें अपलोड करें।")
    
    # पार्ट A: सिर्फ नया शिपर रजिस्टर करने का बॉक्स
    new_shipper = st.text_input("नया शिपर / एक्सपोर्टर का नाम दर्ज करें:", placeholder="जैसे: ABC Exports Pvt Ltd")
    if st.button("➕ Add Shipper Name"):
        if new_shipper.strip() == "":
            st.error("कृपया शिपर का नाम खाली न छोड़ें।")
        elif new_shipper in st.session_state["shipper_database"]:
            st.warning(f"⚠️ '{new_shipper}' नाम पहले से मौजूद है।")
        else:
            # नए शिपर का ब्लैंक स्ट्रक्चर बनाना
            st.session_state["shipper_database"][new_shipper] = {"allowed_uploads": [], "uploaded_files": {}}
            st.success(f"🎉 शिपर '{new_shipper}' सफलतापूर्वक जुड़ गया! अब नीचे ड्रॉपडाउन में उसे सेलेक्ट करके सेटिंग्स करें।")

    st.write("---")
    
    # पार्ट B: शिपर सेलेक्ट करके टिक लगाने और फाइल अपलोड करने का कंबाइंड सेक्शन
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None, placeholder="यहाँ शिपर का नाम चुनें या सर्च करें...")
        
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप: **{selected_shipper}**")
            
            selected_uploads = []
            current_allowed = st.session_state["shipper_database"][selected_shipper].get("allowed_uploads", [])
            
            # Manage Specific Upload Buttons में बनाए गए बटन्स को चेकबॉक्स के रूप में दिखाना
            for t in st.session_state["master_types"]:
                is_checked = t in current_allowed
                if st.checkbox(t, value=is_checked, key=f"chk_{selected_shipper}_{t}"):
                    selected_uploads.append(t)
            
            if st.button("🔒 सेव शिपर कॉन्फ़िगरेशन"):
                st.session_state["shipper_database"][selected_shipper]["allowed_uploads"] = selected_uploads
                st.success(f"✅ '{selected_shipper}' के अपलोड ऑप्शंस अपडेट हो गए!")
                st.rerun()

            # पार्ट C: जो ऑप्शंस टिक हैं, उनके लिए फाइल अपलोडर दिखाना
            allowed_buttons = st.session_state["shipper_database"][selected_shipper].get("allowed_uploads", [])
            if allowed_buttons:
                st.write("#### 📁 इस शिपर के लिए फ़ाइलें अपलोड करें:")
                for btn_name in allowed_buttons:
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
                            st.success(f"{btn_name} सफलतापूर्वक सेव हो गई।")
                            st.rerun()
