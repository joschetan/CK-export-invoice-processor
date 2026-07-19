import streamlit as st
import requests
import json

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

def render_global_masters():
    st.header("🌍 Global Master Fields & Rules Template")
    st.caption("यहाँ आप जो भी रूल्स और सेल नंबर सेट करेंगे, वह पूरे सॉफ्टवेयर के लिए परमानेंट 'मास्टर टेम्पलेट बोर्ड' बन जाएगा।")
    
    # ⚡ वेल्सपन से पूरे ५६ रूल्स (डेटा सहित) खींचने का वन-टाइम महा-बटन
    st.subheader("⚡ One-Time Helper (मेहनत बचाओ)")
    if st.button("🔥 Copy All 56 Fields WITH Rules from WELSPUN to Master Board", type="secondary"):
        db = st.session_state.get("shipper_database", {})
        welspun_key = None
        for k in db.keys():
            if "welspun" in k.lower():
                welspun_key = k
                break
                
        if welspun_key:
            welspun_rules = db[welspun_key].get("mapping_rules", {})
            if welspun_rules:
                # सीधे पूरे रूल्स ब्लॉक (कीवर्ड, सेल सहित) को मास्टर टेम्पलेट में कॉपी करना
                st.session_state["master_rules_template"] = dict(welspun_rules)
                st.success(f"🎉 वेल्सपन के सभी {len(welspun_rules)} फ़ील्ड्स उनके कीवर्ड्स और सेल नंबर के साथ यहाँ मास्टर में लोड हो गए हैं! नीचे लिस्ट देखें और नीले बटन से सेव करें।")
                st.rerun()
            else:
                st.error("वेल्सपन प्रोफाइल में कोई रूल्स नहीं मिले।")
        else:
            st.error("डेटाबेस में वेल्सपन शिपर नहीं मिला।")
            
    st.write("---")
    
    # 🛠️ मास्टर रूल्स बिल्डर लेआउट (हूबहू आपकी पसंद का 2nd स्क्रीनशॉट लेआउट)
    st.subheader("🛠️ Master Rules Template Builder")
    
    col_t, col_add = st.columns([8, 2])
    with col_add:
        if st.button("➕ Add Master Row", use_container_width=True):
            st.session_state["master_rules_template"]["New Field"] = {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""}
            st.rerun()
            
    current_masters = st.session_state.get("master_rules_template", {})
    updated_masters = {}
    
    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
    with h_col1: st.markdown("**Field Name**")
    with h_col2: st.markdown("**Default Keyword**")
    with h_col3: st.markdown("**Default Position**")
    with h_col4: st.markdown("**Default Cell**")
    with h_col5: st.markdown("**Custom AI Logic**")
    st.write("---")
    
    for field in list(current_masters.keys()):
        saved_val = current_masters[field]
        col1, col2, col3, col4, col5, col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
        
        with col1: edited_name = st.text_input(f"m_fl_{field}", value=field, label_visibility="collapsed")
        with col2: ky = st.text_input(f"m_ky_{field}", value=saved_val.get("keyword", ""), label_visibility="collapsed")
        with col3: pos = st.selectbox(f"m_pos_{field}", ["Right (आगे)", "Below (नीचे)"], index=0 if saved_val.get("position", "Right (आगे)") == "Right (आगे)" else 1, label_visibility="collapsed")
        with col4: cl = st.text_input(f"m_cl_{field}", value=saved_val.get("cell", ""), label_visibility="collapsed")
        with col5: lg = st.text_input(f"m_lg_{field}", value=saved_val.get("logic", ""), placeholder="जैसे: 4 alpha + 7 numbers", label_visibility="collapsed")
        with col6:
            if st.button("🗑️", key=f"m_del_{field}"):
                del st.session_state["master_rules_template"][field]
                st.rerun()
                
        updated_masters[edited_name] = {"keyword": ky, "position": pos, "cell": cl, "logic": lg}
        
    st.write("---")
    if st.button("💾 Save Entire Master Template Board to Google Sheet", type="primary", use_container_width=True):
        st.session_state["master_rules_template"] = updated_masters
        
        # पेलोड तैयार करना
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
        try:
            requests.post(WEB_APP_URL, data=json.dumps(payload))
            st.success("🎉 बधाई हो भाई! पूरा का पूरा 5-कॉलम मास्टर बोर्ड रूल्स और सेल नंबर सहित गूगल शीट में लॉक हो गया है!")
        except Exception as e:
            st.error(f"सिंक एरर: {str(e)}")
