import streamlit as st
import requests
import json

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

# ➕ मास्टर में नया फ़ील्ड जोड़ने वाला मॉडर्न पॉपअप (Dialog)
@st.dialog("➕ Add New Global Master Field")
def add_master_field_dialog():
    st.write("यहाँ जो नाम आप डालेंगे, वह मास्टर टेम्पलेट बोर्ड में एक नई डिफ़ॉल्ट रो के रूप में जुड़ जाएगा।")
    new_master_name = st.text_input("Master Field Name (जैसे: Container Weight, Seal Type):", placeholder="यहाँ नाम लिखें...")
    
    if st.button("Confirm & Add to Master", type="primary"):
        if new_master_name.strip() == "":
            st.error("फ़ील्ड का नाम खाली नहीं हो सकता!")
        elif new_master_name in st.session_state["master_rules_template"]:
            st.warning("यह फ़ील्ड मास्टर में पहले से मौजूद है!")
        else:
            # मास्टर टेम्पलेट डिक्शनरी में नया खाली स्ट्रक्चर जोड़ना
            st.session_state["master_rules_template"][new_master_name] = {
                "keyword": "",
                "position": "Right (आगे)",
                "cell": "",
                "logic": ""
            }
            st.success(f"🎉 मास्टर फ़ील्ड '{new_master_name}' जुड़ गया!")
            st.rerun()

def render_global_masters():
    st.header("🌍 Global Master Fields & Rules Template")
    st.caption("यहाँ आप जो भी रूल्स और सेल नंबर सेट करेंगे, वह पूरे सॉफ्टवेयर के लिए परमानेंट 'मास्टर टेम्पलेट बोर्ड' बन जाएगा।")
    st.write("---")
    
    # 🛠️ मास्टर रूल्स बिल्डर लेआउट
    col_t, col_add = st.columns([8, 2])
    with col_t:
        st.subheader("🛠️ Master Rules Template Builder")
    with col_add:
        # 🎯 पॉपअप खोलने वाला प्लस बटन
        if st.button("➕ Add Master Row", type="secondary", use_container_width=True):
            add_master_field_dialog()
            
    current_masters = st.session_state.get("master_rules_template", {})
    updated_masters = {}
    
    # हेडर कॉलम्स
    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
    with h_col1: st.markdown("**Field Name**")
    with h_col2: st.markdown("**Default Keyword**")
    with h_col3: st.markdown("**Default Position**")
    with h_col4: st.markdown("**Default Cell**")
    with h_col5: st.markdown("**Custom AI Logic**")
    with h_col6: st.markdown("**Action**")
    st.write("---")
    
    # डायनामिक रोज़ रेंडरिंग
    for field in list(current_masters.keys()):
        saved_val = current_masters[field]
        col1, col2, col3, col4, col5, col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
        
        with col1: edited_name = st.text_input(f"m_fl_{field}", value=field, label_visibility="collapsed")
        with col2: ky = st.text_input(f"m_ky_{field}", value=saved_val.get("keyword", ""), label_visibility="collapsed")
        with col3: pos = st.selectbox(f"m_pos_{field}", ["Right (आगे)", "Below (नीचे)"], index=0 if saved_val.get("position", "Right (आगे)") == "Right (आगे)" else 1, label_visibility="collapsed")
        with col4: cl = st.text_input(f"m_cl_{field}", value=saved_val.get("cell", ""), label_visibility="collapsed")
        with col5: lg = st.text_input(f"m_lg_{field}", value=saved_val.get("logic", ""), placeholder="जैसे: 4 alpha + 7 numbers", label_visibility="collapsed")
        with col6:
            # 🗑️ मास्टर रो डिलीट बटन
            if st.button("🗑️", key=f"m_del_{field}"):
                del st.session_state["master_rules_template"][field]
                st.toast(f"❌ '{field}' मास्टर से हटा दिया गया।")
                st.rerun()
                
        updated_masters[edited_name] = {"keyword": ky, "position": pos, "cell": cl, "logic": lg}
        
    st.write("---")
    if st.button("💾 Save Entire Master Template Board to Google Sheet", type="primary", use_container_width=True):
        st.session_state["master_rules_template"] = updated_masters
        
        fields_payload = []
        for f_name, r_info in updated_masters.items():
            fields_payload.append({
                "field": f_name,
                "keyword": r_info.get("keyword", ""),
                "position": r_info.get("position", "Right (आगे)"),
                "cell": r_info.get("cell", ""),
                "logic": r_info.get("logic", "")
            })
            
        payload = {"action": "save_master_fields", "fields": fields_payload}
        with st.spinner("मास्टर बोर्ड गूगल शीट में सुरक्षित किया जा रहा है..."):
            try:
                requests.post(WEB_APP_URL, data=json.dumps(payload))
                st.success("🎉 बधाई हो भाई! पूरा का पूरा मास्टर टेम्पलेट बोर्ड गूगल शीट में लॉक हो गया है!")
            except Exception as e:
                st.error(f"सिंक एरर: {str(e)}")
