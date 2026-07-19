import streamlit as st
import requests
import json
import base64

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

# ➕ नया फ़ील्ड जोड़ने वाला मॉडर्न पॉपअप (Dialog Window)
@st.dialog("➕ Add New Custom Field")
def add_custom_field_dialog(selected_shipper):
    st.write("आप जो भी नाम यहाँ डालेंगे, वह नीचे रूल्स बोर्ड में एक नई रो के रूप में जुड़ जाएगा।")
    new_field_name = st.text_input("New Field Name (जैसे: Notify Party, BL No):", placeholder="यहाँ नाम टाइप करें...")
    
    if st.button("Confirm & Add Row", type="primary"):
        if new_field_name.strip() == "":
            st.error("फ़ील्ड का नाम खाली नहीं हो सकता!")
        elif new_field_name in st.session_state["shipper_database"][selected_shipper]["mapping_rules"]:
            st.warning("यह फ़ील्ड नाम पहले से मौजूद है!")
        else:
            # बैकएंड डिक्शनरी में नया डिफ़ॉल्ट स्ट्रक्चर जोड़ना
            st.session_state["shipper_database"][selected_shipper]["mapping_rules"][new_field_name] = {
                "keyword": "",
                "position": "Right (आगे)",
                "cell": "",
                "logic": ""
            }
            st.success(f"🎉 फ़ील्ड '{new_field_name}' सफलतापुर्वक जुड़ गया!")
            st.rerun()

def render_shipper_data():
    st.header("🏢 Add Shipper Name & AI Mapping Builder")
    st.caption("डेटा सीधे आपकी गूगल शीट में सुरक्षित रूप से ट्रांसफर होगा।")
    
    # पार्ट A: नया शिपर रजिस्टर करना
    new_shipper = st.text_input("नया शिपर / एक्सपोर्टर का नाम दर्ज करें:", placeholder="जैसे: WELSPUN GLOBAL BRANDS LIMITED")
    if st.button("➕ Add Shipper Name"):
        if new_shipper.strip() == "":
            st.error("कृपया शिपर का नाम खाली न छोड़ें।")
        elif new_shipper in st.session_state["shipper_database"]:
            st.warning(f"⚠️ '{new_shipper}' नाम पहले से मौजूद है।")
        else:
            st.session_state["shipper_database"][new_shipper] = {
                "allowed_uploads": ["Full Job Excel Format File"], 
                "uploaded_files": {},
                "mapping_rules": {
                    # डिफ़ॉल्ट फ़ील्ड्स जो पहली बार में हमेशा दिखेंगे
                    "Port of Loading": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Final Dest. Country": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Final Dest. Port": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Inv. No.": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Inv. Dt.": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Gross Wt.": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Net Wt.": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "NO OF Cartons": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "AD Code": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "CONTAINER NO.": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Size": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                }
            }
            st.success(f"🎉 शिपर '{new_shipper}' जुड़ गया!")
            st.rerun()

    st.write("---")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None, placeholder="यहाँ शिपर का नाम चुनें...")
        
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            # 📁 टेम्पलेट फ़ाइल अपलोड
            st.subheader("📁 1. टेम्पलेट फ़ाइल अपलोड")
            has_file = "Full Job Excel Format File" in shipper_info["uploaded_files"]
            if has_file:
                st.success("✅ Blank Full Job Excel Format File अपलोडेड है।")
                if st.button("🗑️ Delete & Replace Template", key=f"del_tpl_{selected_shipper}"):
                    del shipper_info["uploaded_files"]["Full Job Excel Format File"]
                    st.rerun()
            else:
                f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template) अपलोड करें", type=["xlsx", "xls"], key=f"tpl_{selected_shipper}")
                if f_upload:
                    file_bytes = f_upload.getvalue()
                    shipper_info["uploaded_files"]["Full Job Excel Format File"] = file_bytes
                    
                    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
                    payload = {"action": "save_file", "shipper": selected_shipper, "file_base64": file_b64}
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps(payload))
                        st.success("टेम्पलेट फ़ाइल गूगल शीट में सुरक्षित सेव हो गई!")
                    except Exception:
                        st.warning("लोकल सेव हुआ, गूगल शीट सिंक में दिक्कत आई।")
                    st.rerun()
                    
            st.write("---")
            
            # 🛠️ नो-कोड रूल्स बोर्ड (लॉजिक फ़िल्टर और डिलीट बटन के साथ)
            col_title, col_btn = st.columns([8, 2])
            with col_title:
                st.subheader("🛠️ 2. AI Mapping Rules Builder")
            with col_btn:
                # 🎯 पॉपअप खोलने वाला शानदार प्लस बटन
                if st.button("➕ Add Field", type="secondary", use_container_width=True):
                    add_custom_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            
            # अगर किसी पुराने शिपर में गलती से रूल्स खाली हों
            if not current_rules:
                current_rules = {
                    "Port of Loading": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""},
                    "Inv. No.": {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""}
                }
            
            updated_rules = {}
            
            # हेडर लेआउट (चौड़ाई सेट की)
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
            with h_col1: st.markdown("**Field Name**")
            with h_col2: st.markdown("**Invoice Keyword**")
            with h_col3: st.markdown("**Data Position**")
            with h_col4: st.markdown("**Excel Cell**")
            with h_col5: st.markdown("**Custom AI Logic / Instructions**")
            with h_col6: st.markdown("**Action**")
            st.write("---")
            
            # डायनामिक लूप: जो भी डिक्शनरी में है, सबकी रो जनरेट होगी
            for field in list(current_rules.keys()):
                saved_val = current_rules[field]
                
                col1, col2, col3, col4, col5, col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
                
                with col1:
                    # एडिट का ऑप्शन सीधे इनपुट बॉक्स के रूप में दे दिया ताकि यूजर नाम यहीं बदल सके!
                    edited_field_name = st.text_input(f"field_label_{field}", value=field, label_visibility="collapsed")
                with col2:
                    ky = st.text_input(f"Keyword_{field}", value=saved_val.get("keyword", ""), label_visibility="collapsed")
                with col3:
                    pos = st.selectbox(f"Position_{field}", ["Right (आगे)", "Below (नीचे)"], index=0 if saved_val.get("position", "Right (आगे)") == "Right (आगे)" else 1, label_visibility="collapsed")
                with col4:
                    cl = st.text_input(f"Cell_{field}", value=saved_val.get("cell", ""), label_visibility="collapsed")
                with col5:
                    lg = st.text_input(f"Logic_{field}", value=saved_val.get("logic", ""), placeholder="जैसे: 4 alpha + 7 numbers", label_visibility="collapsed")
                with col6:
                    # 🗑️ डिलीट फ़ील्ड बटन
                    if st.button("🗑️", key=f"del_row_{field}", help="इस फ़ील्ड को हटाएं"):
                        del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field]
                        st.toast(f"❌ '{field}' फ़ील्ड हटा दिया गया। कृपया सेव बटन दबाएं!")
                        st.rerun()
                
                # बदले हुए या पुराने नाम के साथ डेटा स्ट्रक्चर तैयार करना
                updated_rules[edited_field_name] = {"keyword": ky, "position": pos, "cell": cl, "logic": lg}
                
            st.write("---")
            
            if st.button("💾 Save AI Mapping Rules (गूगल शीट में सुरक्षित करें)", type="primary"):
                st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules
                
                rules_payload = []
                for s_name, s_data in st.session_state["shipper_database"].items():
                    s_rules = s_data.get("mapping_rules", {})
                    for f_name, r_info in s_rules.items():
                        rules_payload.append({
                            "shipper": s_name,
                            "field": f_name,
                            "keyword": r_info.get("keyword", ""),
                            "position": r_info.get("position", "Right (आगे)"),
                            "cell": r_info.get("cell", ""),
                            "logic": r_info.get("logic", "")
                        })
                
                payload = {"action": "save_rules", "rules": rules_payload}
                
                with st.spinner("डेटाबेस गूगल शीट में सिंक हो रहा है..."):
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps(payload))
                        st.success("🎉 आपका पूरा कस्टम रूल्स बोर्ड गूगल शीट में सिंक हो गया है!")
                    except Exception as e:
                        st.error(f"सिंक एरर: {str(e)}")
                st.rerun()
