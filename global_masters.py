import streamlit as st
import requests
import json

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

def render_global_masters():
    st.header("🌍 Global Master Fields Manager")
    st.caption("यहाँ आप जो भी फ़ील्ड्स ऐड करेंगे, वे पूरे सॉफ्टवेयर के लिए एक 'मास्टर टेम्पलेट' बन जाएंगे।")
    
    # 🎯 भाई, यह रहा आपका वन-टाइम जादुई बटन जो वेल्सपन से 56 फ़ील्ड्स कॉपी करेगा
    st.subheader("⚡ One-Time Helper (मेहनत बचाओ)")
    if st.button("🔥 Copy All 56 Fields from WELSPUN to Master List", type="secondary"):
        db = st.session_state.get("shipper_database", {})
        
        # वेल्सपन का सही नाम ढूंढना (चाहे छोटे-बड़े अक्षर हों)
        welspun_key = None
        for k in db.keys():
            if "welspun" in k.lower():
                welspun_key = k
                break
                
        if welspun_key:
            welspun_fields = list(db[welspun_key].get("mapping_rules", {}).keys())
            if welspun_fields:
                # वर्तमान मास्टर लिस्ट में वेल्सपन के फ़ील्ड्स को मर्ज करना (डुप्लिकेट्स हटाकर)
                existing_masters = st.session_state.get("master_fields", [])
                for f in welspun_fields:
                    if f not in existing_masters:
                        existing_masters.append(f)
                        
                st.session_state["master_fields"] = existing_masters
                st.success(f"🎉 वेल्सपन से {len(welspun_fields)} फ़ील्ड्स सफलतापूर्वक यहाँ कॉपी हो गए हैं! नीचे दिए गए नीले बटन को दबाकर गूगल शीट में सेव कर दें।")
            else:
                st.error("वेल्सपन प्रोफाइल में कोई फ़ील्ड्स नहीं मिले।")
        else:
            st.error("डेटाबेस में वेल्सपन (WELSPUN) नाम का कोई शिपर नहीं मिला। कृपया नाम चेक करें।")
            
    st.write("---")

    # ➕ नया फ़ील्ड मास्टर में मैन्युअल जोड़ना
    st.subheader("➡️ नया फ़ील्ड जोड़ें")
    new_m_field = st.text_input("ग्लोबल मास्टर फ़ील्ड नाम लिखें (जैसे: Container Type):")
    if st.button("➕ Add to Master List"):
        if new_m_field.strip() == "":
            st.error("फ़ील्ड का नाम खाली नहीं हो सकता।")
        elif new_m_field.strip() in st.session_state["master_fields"]:
            st.warning("यह फ़ील्ड पहले से मास्टर लिस्ट में मौजूद है।")
        else:
            st.session_state["master_fields"].append(new_m_field.strip())
            st.success(f"'{new_m_field}' को लिस्ट में जोड़ दिया गया है।")
            st.rerun()
            
    st.write("---")
    st.subheader("📋 वर्तमान मास्टर फ़ील्ड्स लिस्ट")
    
    # लिस्ट दिखाना और डिलीट का ऑप्शन देना
    updated_master = []
    for field in list(st.session_state["master_fields"]):
        col_name, col_del = st.columns([8, 2])
        with col_name:
            st.write(f"🔹 {field}")
        with col_del:
            if st.button("🗑️", key=f"del_master_{field}"):
                st.session_state["master_fields"].remove(field)
                st.rerun()
                
    st.write("---")
    
    # 💾 गूगल शीट में परमानेंट लॉक करने का बटन
    if st.button("💾 Save Master Fields to Google Sheet", type="primary", use_container_width=True):
        payload = {
            "action": "save_master_fields",
            "fields": st.session_state["master_fields"]
        }
        with st.spinner("मास्टर फ़ील्ड्स गूगल शीट में सिंक हो रहे हैं..."):
            try:
                requests.post(WEB_APP_URL, data=json.dumps(payload))
                st.success("🎉 बधाई हो भाई! आपके 56+ फ़ील्ड्स हमेशा के लिए गूगल शीट में मास्टर टेम्पलेट बन चुके हैं!")
            except Exception as e:
                st.error(f"सिंक एरर: {str(e)}")
