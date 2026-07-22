import streamlit as st
import requests
import json
import base64
import pdfplumber
import re
import time
from io import BytesIO

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

def ensure_default_shipper():
    """यह पक्का करता है कि कम से कम WELSPUN शिपर हमेशा मौजूद रहे"""
    if "shipper_database" not in st.session_state:
        st.session_state["shipper_database"] = {}
        
    if "WELSPUN GLOBAL BRANDS LIMITED" not in st.session_state["shipper_database"]:
        initial_rules = dict(st.session_state.get("master_rules_template", {}))
        st.session_state["shipper_database"]["WELSPUN GLOBAL BRANDS LIMITED"] = {
            "allowed_uploads": ["Full Job Excel Format File"], 
            "uploaded_files": {},
            "mapping_rules": initial_rules
        }

def fetch_data_from_google_sheet():
    """गूगल शीट से सभी शिपर और उनके रूल्स ऑटोमैटिक लोड करने का फ़ंक्शन"""
    ensure_default_shipper()
    try:
        response = requests.get(f"{WEB_APP_URL}?action=get_data", timeout=15)
        if response.status_code == 200:
            data = response.json()
            rules_list = data.get("rules", []) if isinstance(data, dict) else data
            
            if isinstance(rules_list, list):
                for row in rules_list:
                    if isinstance(row, dict):
                        s_name = str(row.get("shipper", "")).strip()
                        f_name = str(row.get("field", "")).strip()
                        
                        if s_name and f_name:
                            if s_name not in st.session_state["shipper_database"]:
                                st.session_state["shipper_database"][s_name] = {
                                    "allowed_uploads": ["Full Job Excel Format File"],
                                    "uploaded_files": {},
                                    "mapping_rules": {}
                                }
                            
                            st.session_state["shipper_database"][s_name]["mapping_rules"][f_name] = {
                                "keyword": str(row.get("keyword", "")),
                                "position": str(row.get("position", "Right (आगे)")),
                                "cell": str(row.get("cell", "")),
                                "match_mode": str(row.get("match_mode", "Exact Word")),
                                "stop_kw": str(row.get("stop_kw", "")),
                                "filter": str(row.get("filter", "None")),
                                "logic": str(row.get("logic", "None"))
                            }
    except Exception:
        pass

@st.dialog("⚡ Field Extraction Test Result")
def test_field_dialog(field_name, rule_data, test_pdf_bytes):
    st.markdown(f"### 🔍 Testing Field: **{field_name}**")
    st.caption("नीचे दिए गए रूल्स के आधार पर सैंपल पीडीएफ से लाइव डेटा निकाला जा रहा है:")
    
    st.info(f"📌 **Keyword:** `{rule_data.get('keyword', 'N/A')}` | **Position:** `{rule_data.get('position', 'N/A')}` | **Match Mode:** `{rule_data.get('match_mode', 'N/A')}` | **Stop Kw:** `{rule_data.get('stop_kw', 'N/A')}` | **Filter:** `{rule_data.get('filter', 'N/A')}`")
    
    extracted_val = ""
    pdf_text = ""
    pdf_lines = []
    
    try:
        with pdfplumber.open(BytesIO(test_pdf_bytes)) as pdf:
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
                        if raw_found.startswith(":"):
                            raw_found = raw_found[1:].strip()
                        if raw_found:
                            break
                    elif pos == "Below (नीचे)" or pos == "Table Column":
                        if idx + 1 < len(pdf_lines):
                            raw_found = pdf_lines[idx + 1].strip()
                            if raw_found:
                                break
        else:
            raw_found = pdf_text
            
        if raw_found:
            if mode == "Word Position" or mode.startswith("Word "):
                w_num = 1
                if mode.startswith("Word ") and mode.split()[1].isdigit():
                    w_num = int(mode.split()[1])
                elif stop_kw and stop_kw.strip().isdigit():
                    w_num = int(stop_kw.strip())
                parts = raw_found.split()
                raw_found = parts[w_num - 1].strip() if len(parts) >= w_num else ""
            elif mode == "After Word" and stop_kw:
                if stop_kw.lower() in raw_found.lower():
                    start_idx = raw_found.lower().find(stop_kw.lower()) + len(stop_kw)
                    raw_found = raw_found[start_idx:].strip()
                    if raw_found.startswith(":"): raw_found = raw_found[1:].strip()
            elif mode == "Between Words":
                if kw and stop_kw and kw.lower() in raw_found.lower() and stop_kw.lower() in raw_found.lower():
                    s_idx = raw_found.lower().find(kw.lower()) + len(kw)
                    e_idx = raw_found.lower().find(stop_kw.lower(), s_idx)
                    if e_idx != -1:
                        raw_found = raw_found[s_idx:e_idx].strip()
            elif mode == "Skip 1st Word":
                parts = raw_found.split(maxsplit=1)
                raw_found = parts[1].strip() if len(parts) > 1 else raw_found
            elif mode == "Exact Word":
                if raw_found.startswith(":"): raw_found = raw_found[1:].strip()
                parts = raw_found.split()
                raw_found = parts[0].strip() if parts else ""
            elif mode == "Full Line":
                if raw_found.startswith(":"): raw_found = raw_found[1:].strip()
                raw_found = raw_found.split("\n")[0].strip()

            if mode != "Word Position" and not mode.startswith("Word ") and mode not in ["Between Words", "After Word"] and stop_kw and stop_kw.strip() and stop_kw.lower() in raw_found.lower():
                st_idx = raw_found.lower().find(stop_kw.lower())
                raw_found = raw_found[:st_idx].strip()

            if flt == "Container Number (ISO Format)":
                cntr_match = re.search(r'\b[A-Za-z]{4}\s*\d{7}\b', raw_found)
                if cntr_match:
                    extracted_val = cntr_match.group(0).replace(" ", "")
                else:
                    cntr_match2 = re.search(r'\b[A-Za-z]{4}\d{6,8}\b', raw_found)
                    extracted_val = cntr_match2.group(0) if cntr_match2 else raw_found.strip()
            elif flt == "Container Size (20/40 Only)":
                size_match = re.search(r'\b(20|40)(?=\s*HC|\s*FT|\s*GP|\s*HQ|\b)', raw_found, re.IGNORECASE)
                if size_match:
                    extracted_val = size_match.group(1)
                else:
                    size_match2 = re.search(r'\b(20|40)\b', raw_found)
                    extracted_val = size_match2.group(1) if size_match2 else ""
            elif flt == "Numbers Only":
                nums = re.findall(r'[\d,.]+', raw_found)
                extracted_val = nums[0].strip() if nums else ""
            elif flt == "Letters Only":
                lets = re.findall(r'[a-zA-Z]+', raw_found)
                extracted_val = " ".join(lets).strip() if lets else ""
            elif flt == "Inside Brackets ()":
                match = re.search(r'\(([^)]+)\)', raw_found)
                extracted_val = match.group(1).strip() if match else raw_found
            else:
                extracted_val = raw_found.strip()

            if lg and lg.strip() and lg != "None":
                if "cart" in lg.lower() or "ctn" in lg.lower():
                    if "cart" in extracted_val.lower() or "ctn" in extracted_val.lower(): extracted_val = "CTN"

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
    fetch_data_from_google_sheet()
    
    st.header("🏢 Add Shipper Name & Live-Test AI Mapping Builder")
    st.caption("सटीक डेटा एक्सट्रैक्शन और रो-बाय-रो लाइव टेस्ट इंजन।")
    
    c_ship_in, c_ship_btn = st.columns([4, 1])
    with c_ship_in:
        new_shipper = st.text_input("नया शिपर / एक्सपोर्टर का नाम दर्ज करें:", placeholder="जैसे: WELSPUN GLOBAL BRANDS LIMITED", label_visibility="collapsed")
    with c_ship_btn:
        if st.button("➕ Add Shipper", type="primary", use_container_width=True):
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
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=0)
        
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            current_rules = shipper_info.get("mapping_rules", {})
            
            st.subheader("📁 1. टेम्पलेट फ़ाइल अपलोड")
            has_file = "Full Job Excel Format File" in shipper_info.get("uploaded_files", {})
            if has_file:
                st.success("✅ Blank Full Job Excel Format File अपलोडेड है।")
                if st.button("🗑️ Delete & Replace Template", key=f"del_tpl_{selected_shipper}"):
                    del shipper_info["uploaded_files"]["Full Job Excel Format File"]
                    delete_payload = {"action": "delete_file", "shipper": selected_shipper}
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps(delete_payload), timeout=30)
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
                    requests.post(WEB_APP_URL, data=json.dumps({"action": "save_file", "shipper": selected_shipper, "file_base64": file_b64}), timeout=30)
                    st.success("टेम्पलेट सेव हो गया!")
                    st.rerun()
                    
            st.write("---")
            
            st.subheader("🧪 2. Upload Sample PDF Invoice for Live Testing")
            sample_pdf = st.file_uploader("यहाँ कोई भी 1 सैंपल इनवॉइस PDF डालें (जिससे लाइव टेस्ट करना हो):", type=["pdf"], key=f"test_pdf_{selected_shipper}")
            if sample_pdf:
                st.session_state[f"sample_bytes_{selected_shipper}"] = sample_pdf.getvalue()
                st.info("💡 सैंपल PDF तैयार है! अब नीचे '⚡ Test' बटन दबाकर लाइव रिजल्ट देखें।")
            st.write("---")
            
            col_title, col_sync, col_add = st.columns([5, 3, 2])
            with col_title:
                st.subheader("🛠️ 3. AI Mapping Rules Builder")
            with col_sync:
                if st.button("🔄 Reload Saved Rules from Sheet", type="secondary", use_container_width=True):
                    st.session_state["shipper_database"] = {}
                    fetch_data_from_google_sheet()
                    st.success("🎉 गूगल शीट से रूल्स लोड हो गए!")
                    st.rerun()
            with col_add:
                if st.button("➕ Add Field", type="secondary", use_container_width=True):
                    add_custom_field_dialog(selected_shipper)
            
            updated_rules = {}
            
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2.5, 1.5, 1, 1.8, 1.5, 1.5, 1.2])
            with c1: st.markdown("**1. Field Name**")
            with c2: st.markdown("**2. Keyword**")
            with c3: st.markdown("**3. Position**")
            with c4: st.markdown("**4. Cell**")
            with c5: st.markdown("**5. Match Mode**")
            with c6: st.markdown("**6. Stop / Word No.**")
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
                    m_opts = ["Exact Word", "Word Position", "Full Line", "Full Block", "After Word", "Between Words", "Skip 1st Word", "Table Extraction"]
                    saved_mm = s_val.get("match_mode", "Exact Word")
                    if saved_mm.startswith("Word "): saved_mm = "Word Position"
                    m_idx = m_opts.index(saved_mm) if saved_mm in m_opts else 0
                    m_mode = st.selectbox(f"mm_{field}", m_opts, index=m_idx, label_visibility="collapsed")
                    
                with c6:
                    placeholder_txt = "Word No. (e.g. 1, 5)" if m_mode == "Word Position" else "e.g. Date / End Word"
                    stop_kw = st.text_input(f"sk_{field}", value=s_val.get("stop_kw", ""), placeholder=placeholder_txt, label_visibility="collapsed")
                    
                with c7:
                    flt_opts = ["None", "Numbers Only", "Letters Only", "Container Number (ISO Format)", "Container Size (20/40 Only)", "Inside Brackets ()", "Write Custom..."]
                    saved_flt = s_val.get("filter", "None")
                    saved_lg = s_val.get("logic", "None")
                    
                    if saved_flt in flt_opts and saved_flt != "Write Custom...":
                        f_idx = flt_opts.index(saved_flt)
                    elif saved_lg and saved_lg != "None":
                        f_idx = 6
                    else:
                        f_idx = 0
                        
                    sel_flt = st.selectbox(f"flt_{field}", flt_opts, index=f_idx, label_visibility="collapsed")
                    
                    if sel_flt == "Write Custom...":
                        cust_lg = st.text_input(f"lg_{field}", value=saved_lg if saved_lg != "None" else "", placeholder="कस्टम निर्देश...", label_visibility="collapsed")
                        final_flt = "Write Custom..."
                    else:
                        cust_lg = "None"
                        final_flt = sel_flt
                        
                with c8:
                    act_col1, act_col2 = st.columns([1, 1])
                    with act_col1:
                        if st.button("⚡", key=f"tst_{field}", help="इस रो को लाइव पीडीएफ से टेस्ट करें"):
                            if test_pdf_data:
                                current_rule_data = {
                                    "keyword": ky, "position": pos, "cell": cl,
                                    "match_mode": m_mode, "stop_kw": stop_kw, "filter": final_flt, "logic": cust_lg
                                }
                                test_field_dialog(field, current_rule_data, test_pdf_data)
                            else:
                                st.warning("पहले '2. Upload Sample PDF' में 1 इनवॉइस डालें!")
                    with act_col2:
                        if st.button("🗑️", key=f"del_{field}"):
                            del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field]
                            st.rerun()
                
                updated_rules[edited_name] = {
                    "keyword": ky, "position": pos, "cell": cl,
                    "match_mode": m_mode, "stop_kw": stop_kw, "filter": final_flt, "logic": cust_lg
                }
                
            st.write("---")
            
            if st.button("💾 Save AI Mapping Rules to Google Sheet", type="primary", use_container_width=True):
                st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules
                
                rules_payload = []
                for s_name, s_data in st.session_state["shipper_database"].items():
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({
                            "shipper": s_name, "field": f_name, "keyword": r_info.get("keyword", ""),
                            "position": r_info.get("position", "Right (आगे)"), "cell": r_info.get("cell", ""),
                            "match_mode": r_info.get("match_mode", "Exact Word"), "stop_kw": r_info.get("stop_kw", ""),
                            "filter": r_info.get("filter", "None"), "logic": r_info.get("logic", "None")
                        })
                
                with st.spinner("⏳ गूगल शीट में सुरक्षित सिंक हो रहा है..."):
                    try:
                        response = requests.post(WEB_APP_URL, data=json.dumps({"action": "save_rules", "rules": rules_payload}), timeout=30)
                        
                        if response.status_code == 200:
                            st.success("🎉 सफलता! आपके सभी रूल्स गूगल शीट में सुरक्षित लॉक्ड हो गए हैं!")
                            st.balloons()
                            time.sleep(2.5)
                            st.rerun()
                        else:
                            st.error(f"शीट रिस्पॉन्स एरर: Code {response.status_code}")
                    except requests.exceptions.Timeout:
                        st.warning("⚠️ सिंक में थोड़ा समय लग रहा है, लेकिन डेटा गूगल शीट में प्रोसेसिंग में भेज दिया गया है।")
                    except Exception as e:
                        st.error(f"नेटवर्क एरर: {str(e)}")
