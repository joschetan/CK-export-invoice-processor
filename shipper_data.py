import streamlit as st
import requests
import json
import base64
import pdfplumber
import re

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

# 🎯 लाइव टेस्ट का जादुई पॉपअप (Dialog Box)
@st.dialog("⚡ Field Extraction Test Result")
def test_field_dialog(field_name, rule_data, test_pdf_bytes):
    st.markdown(f"### 🔍 Testing Field: **{field_name}**")
    st.caption("नीचे दिए गए रूल्स के आधार पर सैंपल पीडीएफ से लाइव डेटा निकाला जा रहा है:")
    
    # रूल्स की समरी दिखाना
    st.info(f"📌 **Keyword:** `{rule_data.get('keyword', 'N/A')}` | **Position:** `{rule_data.get('position', 'N/A')}` | **Match Mode:** `{rule_data.get('match_mode', 'N/A')}` | **Stop Kw:** `{rule_data.get('stop_kw', 'N/A')}` | **Filter:** `{rule_data.get('filter', 'N/A')}`")
    
    # 📑 सैंपल पीडीएफ को पार्स करना
    extracted_val = ""
    pdf_text = ""
    pdf_lines = []
    
    try:
        with pdfplumber.open(test_pdf_bytes) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pdf_text += t + "\n"
                    pdf_lines.extend(t.split("\n"))
                    
        kw = rule_data.get("keyword", "").strip()
        pos = rule_data.get("position", "Right (आगे)")
        mode = rule_data.get("match_mode", "Exact Word")
        stop_kw = rule_data.get("stop_kw", "").strip()
        flt = rule_data.get("filter", "None")
        lg = rule_data.get("logic", "").strip()
        
        raw_found = ""
        if kw:
            for idx, line in enumerate(pdf_lines):
                if kw.lower() in line.lower():
                    if pos == "Right (आगे)":
                        start_idx = line.lower().find(kw.lower()) + len(kw)
                        raw_found = line[start_idx:].strip()
                    elif pos == "Below (नीचे)":
                        if idx + 1 < len(pdf_lines):
                            raw_found = pdf_lines[idx + 1].strip()
                    break
        else:
            raw_found = pdf_text
            
        # 🧪 फ़िल्टर और स्टॉप कीवर्ड का टेस्ट
        if raw_found:
            # Stop Keyword Check
            if stop_kw and stop_kw.lower() in raw_found.lower():
                st_idx = raw_found.lower().find(stop_kw.lower())
                raw_found = raw_found[:st_idx].strip()
                
            # Filters
            if flt == "Numbers Only":
                nums = re.findall(r'[\d,.]+', raw_found)
                extracted_val = nums[0].strip() if nums else ""
            elif flt == "Letters Only":
                lets = re.findall(r'[a-zA-Z]+', raw_found)
                extracted_val = " ".join(lets).strip() if lets else ""
            elif flt == "Inside Brackets ()":
                match = re.search(r'\(([^)]+)\)', raw_found)
                extracted_val = match.group(1).strip() if match else raw_found
            elif mode == "Exact Word":
                if ":" in raw_found: raw_found = raw_found.split(":", 1)[1].strip()
                parts = raw_found.split()
                extracted_val = parts[0].strip() if parts else ""
            else:
                extracted_val = raw_found.strip()
                
            # Custom Logic
            if lg and lg != "None":
                if "cart" in lg.lower() or "ctn" in lg.lower():
                    if "cart" in extracted_val.lower() or "ctn" in extracted_val.lower(): extracted_val = "CTN"
                if "rosctl" in lg.lower():
                    extracted_val = "YES" if "rosctl" in pdf_text.lower() or "under rosctl" in pdf_text.lower() else "NO"
    except Exception as e:
        st.error(f"पार्सिंग एरर: {str(e)}")
        
    st.write("---")
    if extracted_val:
        st.success(f"🎯 **Extracted Output:** `{extracted_val}`")
    else:
        st.warning("⚠️ **Output is Blank!** (कीवर्ड या मैच मोड चेंज करके दोबारा ट्राई करें)")


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
    st.header("🏢 Add Shipper Name & Live-Test AI Mapping Builder")
    st.caption("सटीक डेटा एक्सट्रैक्शन और रो-बाय-रो लाइव टेस्ट इंजन।")
    
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
            
            # 📁 1. टेम्पलेट फ़ाइल अपलोड
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
            
            # 🧪 2. 🔥 लाइव टेस्टिंग के लिए सैंपल PDF अपलोडर (New Addition)
            st.subheader("🧪 2. Upload Sample PDF Invoice for Live Testing")
            sample_pdf = st.file_uploader("यहाँ कोई भी 1 सैंपल इनवॉइस PDF डालें (जिससे लाइव टेस्ट करना हो):", type=["pdf"], key=f"test_pdf_{selected_shipper}")
            if sample_pdf:
                st.session_state[f"sample_bytes_{selected_shipper}"] = sample_pdf.getvalue()
                st.info("💡 सैंपल PDF तैयार है! अब नीचे किसी भी रो के सामने '⚡ Test' बटन दबाकर लाइव रिजल्ट देखें।")
            st.write("---")
            
            # 🛠️ 3. 8-Column Rules Builder with Live Test
            col_title, col_sync, col_add = st.columns([5, 3, 2])
            with col_title:
                st.subheader("🛠️ 3. Advanced 8-Column Rules Builder")
            with col_sync:
                if st.button("🔄 Sync from Master Template", type="secondary", use_container_width=True):
                    current_rules = shipper_info.get("mapping_rules", {})
                    master_tpl = st.session_state.get("master_rules_template", {})
                    for mf, m_vals in master_tpl.items():
                        if mf not in current_rules:
                            current_rules[mf] = dict(m_vals)
                        else:
                            for key_attr in ["match_mode", "stop_kw", "filter"]:
                                if key_attr not in current_rules[mf] or not current_rules[mf][key_attr]:
                                    current_rules[mf][key_attr] = m_vals.get(key_attr, "None" if key_attr == "filter" else ("Exact Word" if key_attr == "match_mode" else ""))
                    shipper_info["mapping_rules"] = current_rules
                    st.success("🎉 मास्टर टेम्पलेट सिंक हो गया!")
                    st.rerun()
            with col_add:
                if st.button("➕ Add Field", type="secondary", use_container_width=True):
                    add_custom_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            # 8 हेडर कॉलम्स
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2.5, 1.5, 1, 1.8, 1.5, 1.5, 1.2])
            with c1: st.markdown("**1. Field Name**")
            with c2: st.markdown("**2. Keyword**")
            with c3: st.markdown("**3. Position**")
            with c4: st.markdown("**4. Cell**")
            with c5: st.markdown("**5. Match Mode**")
            with c6: st.markdown("**6. Stop Keyword**")
            with c7: st.markdown("**7. Filter/Logic**")
            with c8: st.markdown("**Action / Test**")
            st.write("---")
            
            test_pdf_data = st.session_state.get(f"sample_bytes_{selected_shipper}", None)
            
            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2.5, 1.5, 1, 1.8, 1.5, 1.5, 1.2])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c3: pos = st.selectbox(f"p_{field}", ["Right (आगे)", "Below (नीचे)", "Table Column"], index=0 if s_val.get("position") == "Right (आगे)" else (1 if s_val.get("position") == "Below (नीचे)" else 2), label_visibility="collapsed")
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                
                with c5:
                    m_opts = ["Exact Word", "Full Line", "Full Block", "Table Extraction"]
                    m_idx = m_opts.index(s_val.get("match_mode")) if s_val.get("match_mode") in m_opts else 0
                    m_mode = st.selectbox(f"mm_{field}", m_opts, index=m_idx, label_visibility="collapsed")
                    
                with c6:
                    stop_kw = st.text_input(f"sk_{field}", value=s_val.get("stop_kw", ""), placeholder="e.g. Date", label_visibility="collapsed")
                    
                with c7:
                    flt_opts = ["None", "Numbers Only", "Letters Only", "Inside Brackets ()", "Write Custom..."]
                    curr_flt = s_val.get("filter", "None")
                    f_idx = flt_opts.index(curr_flt) if curr_flt in flt_opts else (4 if curr_flt and curr_flt != "None" else 0)
                    sel_flt = st.selectbox(f"flt_{field}", flt_opts, index=f_idx, label_visibility="collapsed")
                    
                    if sel_flt == "Write Custom...":
                        cust_lg = st.text_input(f"lg_{field}", value=s_val.get("logic", ""), placeholder="कस्टम निर्देश...", label_visibility="collapsed")
                    else:
                        cust_lg = sel_flt
                        
                # 🎯 Action Column: टेस्ट बटन + डिलीट बटन
                with c8:
                    act_col1, act_col2 = st.columns([1, 1])
                    with act_col1:
                        # ⚡ LIVE TEST BUTTON
                        if st.button("⚡", key=f"tst_{field}", help="इस रो को लाइव पीडीएफ से टेस्ट करें"):
                            if test_pdf_data:
                                current_rule_data = {
                                    "keyword": ky, "position": pos, "cell": cl,
                                    "match_mode": m_mode, "stop_kw": stop_kw, "filter": sel_flt, "logic": cust_lg
                                }
                                test_field_dialog(field, current_rule_data, test_pdf_data)
                            else:
                                st.warning("पहले ऊपर 1 सैंपल PDF अपलोड करें!")
                    with act_col2:
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
