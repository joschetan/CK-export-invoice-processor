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
            st.success(f"🎉 शिपर '{new_shipper}' जुड़ गया! मैपिंग रूल्स सेव करते ही यह गूगल शीट में चला जाएगा।")
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
                    
                    # फ़ाइल को बेस64 में कन्वर्ट करके गूगल शीट में भेजना
                    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
                    payload = {
                        "action": "save_file",
                        "shipper": selected_shipper,
                        "file_base64": file_b64
                    }
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps(payload))
                        st.success("टेम्पलेट फ़ाइल गूगल शीट में सुरक्षित सेव हो गई!")
                    except Exception:
                        st.warning("लोकल सेव हुआ, गूगल शीट सिंक में दिक्कत आई।")
                    st.rerun()
                    
            st.write("---")
            
            # 🛠️ नो-कोड रूल्स बोर्ड
            st.subheader("🛠️ 2. AI Mapping Rules Builder")
            
            default_fields = [
                "Port of Loading", "Final Dest. Country", "Final Dest. Port", "Inv. No.", "Inv. Dt.", 
                "Gross Wt.", "Net Wt.", "NO OF Cartons", "AD Code", "CONTAINER NO.", "Size"
            ]
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            for field in default_fields:
                saved_val = current_rules.get(field, {"keyword": "", "position": "Right (आगे)", "cell": ""})
                col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
                
                with col1:
                    st.text(f"🔹 {field}")
                with col2:
                    ky = st.text_input(f"Invoice Keyword", value=saved_val["keyword"], key=f"ky_{field}", placeholder="जैसे: Port of Loading :")
                with col3:
                    pos = st.selectbox(f"Data Position", ["Right (आगे)", "Below (नीचे)"], index=0 if saved_val["position"] == "Right (आगे)" else 1, key=f"pos_{field}")
                with col4:
                    cl = st.text_input(f"Excel Cell", value=saved_val["cell"], key=f"cl_{field}", placeholder="जैसे: B2")
                
                updated_rules[field] = {"keyword": ky, "position": pos, "cell": cl}
                
            if st.button("💾 Save AI Mapping Rules (गूगल शीट में सुरक्षित करें)", type="primary"):
                # लोकल सेशन अपडेट
                st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules
                
                # 📤 गूगल शीट API के लिए रूल्स एरे (Array) तैयार करना
                rules_payload = []
                # सभी शिप्स का पुराना डेटा भी रखना ताकि ओवरराइट न हो
                for s_name, s_data in st.session_state["shipper_database"].items():
                    s_rules = s_data.get("mapping_rules", {})
                    for f_name, r_info in s_rules.items():
                        rules_payload.append({
                            "shipper": s_name,
                            "field": f_name,
                            "keyword": r_info["keyword"],
                            "position": r_info["position"],
                            "cell": r_info["cell"]
                        })
                
                payload = {
                    "action": "save_rules",
                    "rules": rules_payload
                }
                
                with st.spinner("डेटाबेस गूगल शीट में सिंक हो रहा है..."):
                    try:
                        res = requests.post(WEB_APP_URL, data=json.dumps(payload))
                        st.success("🎉 बधाई हो भाई! सारा डेटा आपकी लाइव Google Sheet में हमेशा के लिए लॉक हो गया है!")
                    except Exception as e:
                        st.error(f"सिंक एरर: {str(e)}")
                st.rerun()
