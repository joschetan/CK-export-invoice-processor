import streamlit as st
import requests
import json
import base64

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

@st.dialog("➕ Add New Custom Field")
def add_custom_field_dialog(selected_shipper):
    new_field_name = st.text_input("Field Name:")
    if st.button("Confirm & Add Row", type="primary"):
        if new_field_name.strip() and new_field_name not in st.session_state["shipper_database"][selected_shipper]["mapping_rules"]:
            st.session_state["shipper_database"][selected_shipper]["mapping_rules"][new_field_name] = {"keyword": "", "position": "Right (आगे)", "cell": "", "logic": ""}
            st.rerun()

def render_shipper_data():
    st.header("🏢 Add Shipper Name & AI Mapping Builder")
    
    new_shipper = st.text_input("नया शिपर / एक्सपोर्टर का नाम दर्ज करें:")
    if st.button("➕ Add Shipper Name"):
        if new_shipper.strip() and new_shipper not in st.session_state["shipper_database"]:
            initial_rules = dict(st.session_state.get("master_rules_template", {}))
            st.session_state["shipper_database"][new_shipper] = {
                "allowed_uploads": ["Full Job Excel Format File"], 
                "uploaded_files": {},
                "mapping_rules": initial_rules
            }
            st.success(f"🎉 शिपर '{new_shipper}' जुड़ गया!")
            st.rerun()

    st.write("---")
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None)
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template)", type=["xlsx", "xls"])
            if f_upload and "Full Job Excel Format File" not in shipper_info["uploaded_files"]:
                shipper_info["uploaded_files"]["Full Job Excel Format File"] = f_upload.getvalue()
                file_b64 = base64.b64encode(f_upload.getvalue()).decode("utf-8")
                requests.post(WEB_APP_URL, data=json.dumps({"action": "save_file", "shipper": selected_shipper, "file_base64": file_b64}))
                st.rerun()
                    
            st.write("---")
            
            col_title, col_sync, col_add = st.columns([5, 3, 2])
            with col_title: st.subheader("🛠️ 2. AI Mapping Rules Builder")
            with col_sync:
                if st.button("🔄 Sync from Master Template", type="secondary", use_container_width=True):
                    current_rules = shipper_info.get("mapping_rules", {})
                    added_count = 0
                    master_tpl = st.session_state.get("master_rules_template", {})
                    for mf, m_vals in master_tpl.items():
                        if mf not in current_rules:
                            current_rules[mf] = dict(m_vals)
                            added_count += 1
                    shipper_info["mapping_rules"] = current_rules
                    st.success(f"🎉 मास्टर टेम्पलेट से {added_count} नए फ़ील्ड्स जोड़ दिए गए!")
                    st.rerun()
            with col_add:
                if st.button("➕ Add Field", type="secondary", use_container_width=True): add_custom_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
            with h_col1: st.markdown("**Field Name**")
            with h_col2: st.markdown("**Invoice Keyword**")
            with h_col3: st.markdown("**Data Position**")
            with h_col4: st.markdown("**Excel Cell**")
            with h_col5: st.markdown("**Custom AI Logic**")
            st.write("---")
            
            for field in list(current_rules.keys()):
                saved_val = current_rules[field]
                col1, col2, col3, col4, col5, col6 = st.columns([2.5, 3, 2, 1, 3, 0.7])
                
                with col1: edited_field_name = st.text_input(f"fl_{field}", value=field, label_visibility="collapsed")
                with col2: ky = st.text_input(f"ky_{field}", value=saved_val.get("keyword", ""), label_visibility="collapsed")
                with col3: pos = st.selectbox(f"pos_{field}", ["Right (आगे)", "Below (नीचे)"], index=0 if saved_val.get("position", "Right (आगे)") == "Right (आगे)" else 1, label_visibility="collapsed")
                with col4: cl = st.text_input(f"cl_{field}", value=saved_val.get("cell", ""), label_visibility="collapsed")
                
                # 🎯 हाइब्रिड लॉजिक इंजन (5th Column)
                with col5:
                    saved_lg = saved_val.get("logic", "")
                    preset_options = ["None", "Table_Item", "Container No (4 Alpha + 7 Num)", "Write Custom Instruction..."]
                    
                    # डिफ़ॉल्ट इंडेक्स सेट करना
                    current_idx = 0
                    if saved_lg == "Table_Item": current_idx = 1
                    elif saved_lg == "Container No (4 Alpha + 7 Num)": current_idx = 2
                    elif saved_lg and saved_lg not in ["None", "Table_Item", "Container No (4 Alpha + 7 Num)"]:
                        current_idx = 3 # यानी कस्टम लिखा हुआ डेटा है
                        
                    sel_lg = st.selectbox(f"sel_lg_{field}", preset_options, index=current_idx, label_visibility="collapsed")
                    
                    # अगर ड्रॉपडाउन में कस्टम निर्देश चुना है, तभी टेक्स्ट बॉक्स खुलेगा
                    if sel_lg == "Write Custom Instruction...":
                        lg = st.text_input(f"txt_lg_{field}", value=saved_lg if saved_lg not in preset_options else "", placeholder="जैसे: 2 digit country code", label_visibility="collapsed")
                    elif sel_lg == "None":
                        lg = ""
                    else:
                        lg = sel_lg
                
                with col6:
                    if st.button("🗑️", key=f"del_{field}"):
                        del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field]
                        st.rerun()
                
                updated_rules[edited_field_name] = {"keyword": ky, "position": pos, "cell": cl, "logic": lg}
                
            st.write("---")
            if st.button("💾 Save AI Mapping Rules (गूगल शीट में सुरक्षित करें)", type="primary"):
                st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules
                rules_payload = []
                for s_name, s_data in st.session_state["shipper_database"].items():
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({"shipper": s_name, "field": f_name, "keyword": r_info.get("keyword", ""), "position": r_info.get("position", "Right (आगे)"), "cell": r_info.get("cell", ""), "logic": r_info.get("logic", "")})
                
                with st.spinner("सिंक हो रहा है..."):
                    requests.post(WEB_APP_URL, data=json.dumps({"action": "save_rules", "rules": rules_payload}))
                    st.success("🎉 गूगल शीट में सुरक्षित सेव हो गया!")
                st.rerun()
