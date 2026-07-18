import streamlit as st
import requests
import json
import base64

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

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
                "mapping_rules": {}
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
            
            # 🛠️ नो-कोड रूल्स बोर्ड (लॉजिक फ़िल्टर के साथ)
            st.subheader("🛠️ 2. AI Mapping Rules Builder")
            st.caption("नोट: यदि नया AI Logic कॉलम स्क्रीन पर न दिखे, तो कृपया एक बार ब्राउज़र रीफ्रेश कर लें।")
            
            default_fields = [
                "Port of Loading", "Final Dest. Country", "Final Dest. Port", "Inv. No.", "Inv. Dt.", 
                "Gross Wt.", "Net Wt.", "NO OF Cartons", "AD Code", "CONTAINER NO.", "Size"
            ]
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            # हेडर लेआउट सेट करना
            h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([2, 3, 2, 1, 2])
            with h_col1: st.markdown("**Field Name**")
            with h_col2: st.markdown("**Invoice Keyword**")
            with h_col3: st.markdown("**Data Position**")
            with h_col4: st.markdown("**Excel Cell**")
            with h_col5: st.markdown("**AI Logic (विशेष नियम)**")
            st.write("---")
            
            for field in default_fields:
                saved_val = current_rules.get(field, {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": "None"})
                
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 1, 2])
                
                with col1:
                    st.write(f"🔹 **{field}**")
                with col2:
                    ky = st.text_input(f"Keyword_{field}", value=saved_val.get("keyword", ""), label_visibility="collapsed")
                with col3:
                    pos = st.selectbox(f"Position_{field}", ["Right (आगे)", "Below (नीचे)"], index=0 if saved_val.get("position", "Right (आगे)") == "Right (आगे)" else 1, label_visibility="collapsed")
                with col4:
                    cl = st.text_input(f"Cell_{field}", value=saved_val.get("cell", ""), label_visibility="collapsed")
                with col5:
                    # पांचवां कॉलम - ड्रॉपडाउन लॉजिक
                    logic_options = ["None", "Container No (4 Alpha + 7 Num)", "Pure Numbers Only"]
                    saved_lg = saved_val.get("logic", "None")
                    if saved_lg not in logic_options:
                        saved_lg = "None"
                    lg = st.selectbox(f"Logic_{field}", logic_options, index=logic_options.index(saved_lg), label_visibility="collapsed")
                
                updated_rules[field] = {"keyword": ky, "position": pos, "cell": cl, "logic": lg}
                
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
                            "logic": r_info.get("logic", "None")
                        })
                
                payload = {"action": "save_rules", "rules": rules_payload}
                
                with st.spinner("डेटाबेस गूगल शीट में सिंक हो रहा है..."):
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps(payload))
                        st.success("🎉 बधाई हो भाई! लॉजिक रूल्स के साथ डेटा गूगल शीट में लॉक हो गया है!")
                    except Exception as e:
                        st.error(f"सिंक एरर: {str(e)}")
                st.rerun()
