import streamlit as st
import requests
import json
import base64

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

@st.dialog("➕ Add New Custom Field")
def add_custom_field_dialog(selected_shipper):
    st.write("यहाँ नया फ़ील्ड नाम दर्ज करें:")
    new_field_name = st.text_input("Field Name (जैसे: Port of Loading, Size):", placeholder="यहाँ नाम लिखें...")
    
    if st.button("Confirm & Add Row", type="primary"):
        if new_field_name.strip() == "":
            st.error("फ़ील्ड का नाम खाली नहीं हो सकता!")
        elif new_field_name in st.session_state["shipper_database"][selected_shipper]["mapping_rules"]:
            st.warning("यह फ़ील्ड नाम पहले से मौजूद है!")
        else:
            st.session_state["shipper_database"][selected_shipper]["mapping_rules"][new_field_name] = {
                "keyword": "", "position": "Right (आगे)", "cell": "",
                "match_mode": "Exact Word", "stop_kw": "", "filter": "None", "logic": "None"
            }
            st.success(f"🎉 फ़ील्ड '{new_field_name}' जुड़ गया!")
            st.rerun()

def render_shipper_data():
    st.header("🏢 Add Shipper Name & 8-Column AI Mapping Builder")
    st.caption("सटीक डेटा एक्सट्रैक्शन के लिए अपग्रैडेड रूल्स इंजन।")
    
    new_shipper = st.text_input("नया शिपर / एक्सपोर्टर का नाम दर्ज करें:", placeholder="जैसे: WELSPUN GLOBAL BRANDS LIMITED")
    if st.button("➕ Add Shipper Name"):
        if new_shipper.strip() == "":
            st.error("कृपया शिपर का नाम खाली न छोड़ें।")
        elif new_shipper in st.session_state["shipper_database"]:
            st.warning(f"⚠️ '{new_shipper}' नाम पहले से मौजूद है।")
        else:
            initial_rules = dict(st.session_state.get("master_rules_template", {}))
            st.session_state["shipper_database"][new_shipper] = {
                "allowed_uploads": ["Full Job Excel Format File"], 
                "uploaded_files": {},
                "mapping_rules": initial_rules
            }
            st.success(f"🎉 शिपर '{new_shipper}' जुड़ गया!")
            st.rerun()

    st.write("---")
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None)
        
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            # 📁 1. टेम्पलेट अपलोड
            st.subheader("📁 1. टेम्पलेट फ़ाइल अपलोड")
            has_file = "Full Job Excel Format File" in shipper_info["uploaded_files"]
            if has_file:
                st.success("✅ Blank Full Job Excel Format File अपलोडेड है।")
                if st.button("🗑️ Delete & Replace Template", key=f"del_tpl_{selected_shipper}"):
                    del shipper_info["uploaded_files"]["Full Job Excel Format File"]
                    delete_payload = {"action": "delete_file", "shipper": selected_shipper}
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps(delete_payload))
                        st.toast("🔥 गूगल शीट से पुरानी फाइल साफ़ कर दी गई!")
                    except Exception:
                        pass
                    st.rerun()
            else:
                f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template) अपलोड करें", type=["xlsx", "xls"], key=f"tpl_{selected_shipper}")
                if f_upload:
                    file_bytes = f_upload.getvalue()
                    shipper_info["uploaded_files"]["Full Job Excel Format File"] = file_bytes
                    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
                    requests.post(WEB_APP_URL, data=json.dumps({"action": "save_file", "shipper": selected_shipper, "file_base64": file_b64}))
                    st.success("टेम्पलेट सेव हो गया!")
                    st.rerun()
                    
            st.write("---")
            
            # 🛠️ 2. 8-Column Rules Builder
            col_title, col_sync, col_add = st.columns([5, 3, 2])
            with col_title:
                st.subheader("🛠️ 2. Advanced 8-Column AI Rules Builder")
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
                    st.success(f"🎉 मास्टर से {added_count} नए रूल्स सिंक हो गए!")
                    st.rerun()
            with col_add:
                if st.button("➕ Add Field", type="secondary", use_container_width=True):
                    add_custom_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            # 8 हेडर कॉलम्स
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2.5, 1.5, 1, 2, 1.5, 1.5, 0.5])
            with c1: st.markdown("**1. Field Name**")
            with c2: st.markdown("**2. Keyword**")
            with c3: st.markdown("**3. Position**")
            with c4: st.markdown("**4. Cell**")
            with c5: st.markdown("**5. Match Mode**")
            with c6: st.markdown("**6. Stop Keyword**")
            with c7: st.markdown("**7. Filter/Logic**")
            with c8: st.markdown("**Act**")
            st.write("---")
            
            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2.5, 1.5, 1, 2, 1.5, 1.5, 0.5])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c3: pos = st.selectbox(f"p_{field}", ["Right (आगे)", "Below (नीचे)", "Table Column"], index=0 if s_val.get("position") == "Right (आगे)" else (1 if s_val.get("position") == "Below (नीचे)" else 2), label_visibility="collapsed")
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                
                # 5. Match Mode
                with c5:
                    m_opts = ["Exact Word", "Full Line", "Full Block", "Table Extraction"]
                    m_idx = m_opts.index(s_val.get("match_mode")) if s_val.get("match_mode") in m_opts else 0
                    m_mode = st.selectbox(f"mm_{field}", m_opts, index=m_idx, label_visibility="collapsed")
                    
                # 6. Stop Keyword
                with c6:
                    stop_kw = st.text_input(f"sk_{field}", value=s_val.get("stop_kw", ""), placeholder="e.g. Date", label_visibility="collapsed")
                    
                # 7. Cleanup Filter & Custom Logic
                with c7:
                    flt_opts = ["None", "Numbers Only", "Letters Only", "Inside Brackets ()", "Write Custom..."]
                    curr_flt = s_val.get("filter", "None")
                    f_idx = flt_opts.index(curr_flt) if curr_flt in flt_opts else (4 if curr_flt and curr_flt != "None" else 0)
                    sel_flt = st.selectbox(f"flt_{field}", flt_opts, index=f_idx, label_visibility="collapsed")
                    
                    if sel_flt == "Write Custom...":
                        cust_lg = st.text_input(f"lg_{field}", value=s_val.get("logic", ""), placeholder="कस्टम निर्देश टाइप करें...", label_visibility="collapsed")
                    else:
                        cust_lg = sel_flt
                        
                with c8:
                    if st.button("🗑️", key=f"del_{field}"):
                        del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field]
                        st.rerun()
                
                updated_rules[edited_name] = {
                    "keyword": ky, "position": pos, "cell": cl,
                    "match_mode": m_mode, "stop_kw": stop_kw, "filter": sel_flt, "logic": cust_lg
                }
                
            st.write("---")
            if st.button("💾 Save 8-Column AI Rules to Google Sheet", type="primary", use_container_width=True):
                st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules
                
                rules_payload = []
                for s_name, s_data in st.session_state["shipper_database"].items():
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({
                            "shipper": s_name, "field": f_name, "keyword": r_info.get("keyword", ""),
                            "position": r_info.get("position", "Right (आगे)"), "cell": r_info.get("cell", ""),
                            "match_mode": r_info.get("match_mode", "Exact Word"), "stop_kw": r_info.get("stop_kw", ""),
                            "filter": r_info.get("filter", "None"), "logic": r_info.get("logic", "")
                        })
                
                with st.spinner("8-कॉलम डेटाबेस गूगल शीट में सेव हो रहा है..."):
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps({"action": "save_rules", "rules": rules_payload}))
                        st.success("🎉 8-कॉलम रूल्स गूगल शीट में सुरक्षित सेव हो गए हैं!")
                    except Exception as e:
                        st.error(f"सिंक एरर: {str(e)}")
                st.rerun()
