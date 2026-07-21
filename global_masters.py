import streamlit as st
import requests
import json

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

@st.dialog("➕ Add New Global Master Field")
def add_master_field_dialog():
    new_master_name = st.text_input("Master Field Name:", placeholder="यहाँ नाम लिखें...")
    if st.button("Confirm & Add to Master", type="primary"):
        if new_master_name.strip() and new_master_name not in st.session_state["master_rules_template"]:
            st.session_state["master_rules_template"][new_master_name] = {
                "keyword": "", "position": "Right (आगे)", "cell": "",
                "match_mode": "Exact Word", "stop_kw": "", "filter": "None", "logic": "None"
            }
            st.success(f"🎉 मास्टर फ़ील्ड '{new_master_name}' जुड़ गया!")
            st.rerun()

def render_global_masters():
    st.header("🌍 Global Master Fields & 8-Column Rules Template")
    st.caption("परमानेंट 8-कॉलम मास्टर टेम्पलेट बोर्ड।")
    st.write("---")
    
    col_t, col_add = st.columns([8, 2])
    with col_t: st.subheader("🛠️ Master 8-Column Template Builder")
    with col_add:
        if st.button("➕ Add Master Row", type="secondary", use_container_width=True):
            add_master_field_dialog()
            
    current_masters = st.session_state.get("master_rules_template", {})
    updated_masters = {}
    
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
    
    for field in list(current_masters.keys()):
        s_val = current_masters[field]
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2.5, 1.5, 1, 2, 1.5, 1.5, 0.5])
        
        with c1: edited_name = st.text_input(f"m_f_{field}", value=field, label_visibility="collapsed")
        with c2: ky = st.text_input(f"m_k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
        with c3: pos = st.selectbox(f"m_p_{field}", ["Right (आगे)", "Below (नीचे)", "Table Column"], index=0 if s_val.get("position") == "Right (आगे)" else (1 if s_val.get("position") == "Below (नीचे)" else 2), label_visibility="collapsed")
        with c4: cl = st.text_input(f"m_c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
        
        with c5:
            m_opts = ["Exact Word", "Full Line", "Full Block", "Table Extraction"]
            m_idx = m_opts.index(s_val.get("match_mode")) if s_val.get("match_mode") in m_opts else 0
            m_mode = st.selectbox(f"m_mm_{field}", m_opts, index=m_idx, label_visibility="collapsed")
            
        with c6:
            stop_kw = st.text_input(f"m_sk_{field}", value=s_val.get("stop_kw", ""), placeholder="e.g. Date", label_visibility="collapsed")
            
        with c7:
            flt_opts = ["None", "Numbers Only", "Letters Only", "Inside Brackets ()", "Write Custom..."]
            curr_flt = s_val.get("filter", "None")
            f_idx = flt_opts.index(curr_flt) if curr_flt in flt_opts else (4 if curr_flt and curr_flt != "None" else 0)
            sel_flt = st.selectbox(f"m_flt_{field}", flt_opts, index=f_idx, label_visibility="collapsed")
            
            if sel_flt == "Write Custom...":
                cust_lg = st.text_input(f"m_lg_{field}", value=s_val.get("logic", ""), placeholder="कस्टम निर्देश...", label_visibility="collapsed")
            else:
                cust_lg = sel_flt
                
        with c8:
            if st.button("🗑️", key=f"m_del_{field}"):
                del st.session_state["master_rules_template"][field]
                st.rerun()
                
        updated_masters[edited_name] = {
            "keyword": ky, "position": pos, "cell": cl,
            "match_mode": m_mode, "stop_kw": stop_kw, "filter": sel_flt, "logic": cust_lg
        }
        
    st.write("---")
    if st.button("💾 Save Entire 8-Column Master Template to Google Sheet", type="primary", use_container_width=True):
        st.session_state["master_rules_template"] = updated_masters
        
        fields_payload = []
        for f_name, r_info in updated_masters.items():
            fields_payload.append({
                "field": f_name, "keyword": r_info.get("keyword", ""), "position": r_info.get("position", "Right (आगे)"),
                "cell": r_info.get("cell", ""), "match_mode": r_info.get("match_mode", "Exact Word"),
                "stop_kw": r_info.get("stop_kw", ""), "filter": r_info.get("filter", "None"), "logic": r_info.get("logic", "")
            })
            
        payload = {"action": "save_master_fields", "fields": fields_payload}
        try:
            requests.post(WEB_APP_URL, data=json.dumps(payload))
            st.success("🎉 8-कॉलम मास्टर टेम्पलेट गूगल शीट में लॉक हो गया है!")
        except Exception as e:
            st.error(f"सिंक एरर: {str(e)}")
