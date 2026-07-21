import streamlit as st
import requests
import json
import base64
import pdfplumber
import re
import time
from io import BytesIO

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

# 🎯 लाइव टेस्ट का स्मार्ट पॉपअप (Container, Seal & Size Auto-Extract Fix)
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
                    elif pos == "Below (नीचे)" or pos == "Table Column":
                        if idx + 1 < len(pdf_lines):
                            raw_found = pdf_lines[idx + 1].strip()
                    break
        else:
            raw_found = pdf_text
            
        if raw_found:
            # Stop Keyword Check
            if stop_kw and stop_kw.lower() in raw_found.lower():
                st_idx = raw_found.lower().find(stop_kw.lower())
                raw_found = raw_found[:st_idx].strip()
            
            # 🎯 स्मार्ट पैटर्न डिटेक्शन (Container, Size, Seal Smart Filter)
            f_lower = field_name.lower()
            
            if "container" in f_lower or "cntr" in f_lower:
                # 4 अक्षरों + 7 अंकों वाला कंटेनर नंबर पैटर्न (जैसे HLBU3075456)
                cntr_match = re.search(r'\b[A-Z]{4}\d{7}\b', raw_found)
                if cntr_match:
                    extracted_val = cntr_match.group(0)
            
            elif "size" in f_lower or "type" in f_lower:
                # साइज पैटर्न (जैसे 20FT, 40HC, 40FT, 20GP, 40' आदि)
                size_match = re.search(r'\b(20\s*FT|40\s*FT|40\s*HC|20\s*GP|40\s*HQ|20|40)\b', raw_found, re.IGNORECASE)
                if size_match:
                    extracted_val = size_match.group(0)

            elif "seal" in f_lower:
                # सील नंबर (अक्षर + अंक पैटर्न जो कंटेनर नंबर से अलग हो)
                seals = re.findall(r'\b[A-Z0-9]{6,12}\b', raw_found)
                # कंटेनर नंबर और साइज को हटाकर सील नंबर ढूँढना
                valid_seals = [s for s in seals if not re.match(r'^[A-Z]{4}\d{7}$', s) and s not in ["40HC", "20FT", "40FT"]]
                if valid_seals:
                    extracted_val = " / ".join(valid_seals)

            # अगर ऊपर में से कोई विशेष मैच नहीं हुआ तो स्टैंडर्ड फिल्टर्स चलेंगे
            if not extracted_val:
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
                    
            # Custom Logic Checks
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
            
            # 🧪 2. लाइव टेस्टिंग के लिए सैंपल PDF अपलोडर
            st.subheader("🧪 2. Upload Sample PDF Invoice for Live Testing")
            sample_pdf = st.file_uploader("यहाँ कोई भी 1 सैंपल इनवॉइस PDF डालें (जिससे लाइव टेस्ट करना हो):", type=["pdf"], key=f"test_pdf_{selected_shipper}")
            if sample_pdf:
                st.session_state[f"sample_bytes_{selected_shipper}"] = sample_pdf.getvalue()
                st.info("💡 सैंपल PDF तैयार है! अब नीचे '⚡ Test' बटन दबाकर लाइव रिजल्ट देखें।")
            st.write("---")
            
            # 🛠️ 3. Rules Builder
            col_title, col_sync, col_add = st.columns([5, 3, 2])
            with col_title:
                st.subheader("🛠️ 3. AI Mapping Rules Builder")
            with col_sync:
                if st.button("🔄 Sync from Master Template", type="secondary", use_container_width=True):
                    current_rules = shipper_info.get("mapping_rules", {})
                    master_tpl = st.session_state.get("master_rules_template", {})
                    for mf, m_vals in master_tpl.items():
                        if mf not in current_rules:
                            current_rules[mf] = dict(m_vals)
                        else:
                            for key_attr in ["match_mode", "stop_kw", "filter", "logic"]:
                                if key_attr not in current_rules[mf] or not current_rules[mf][key_attr]:
                                    current_rules[mf][key_attr] = m_vals.get(key_attr, "None" if key_attr in ["filter", "logic"] else ("Exact Word" if key_attr == "match_mode" else ""))
                    shipper_info["mapping_rules"] = current_rules
                    st.success("🎉 मास्टर टेम्पलेट सिंक हो गया!")
                    st.rerun()
            with col_add:
                if st.button("➕ Add Field", type="secondary", use_container_width=True):
                    add_custom_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            # हेडर कॉलम्स
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
                    saved_mm = s_val.get("match_mode", "Exact Word")
                    m_idx = m_opts.index(saved_mm) if saved_mm in m_opts else 0
                    m_mode = st.selectbox(f"mm_{field}", m_opts, index=m_idx, label_visibility="collapsed")
                    
                with c6:
                    stop_kw = st.text_input(f"sk_{field}", value=s_val.get("stop_kw", ""), placeholder="e.g. Date", label_visibility="collapsed")
                    
                with c7:
                    flt_opts = ["None", "Numbers Only", "Letters Only", "Inside Brackets ()", "Write Custom..."]
                    saved_flt = s_val.get("filter", "None")
                    saved_lg = s_val.get("logic", "None")
                    
                    if saved_flt in flt_opts and saved_flt != "Write Custom...":
                        f_idx = flt_opts.index(saved_flt)
                    elif saved_lg and saved_lg != "None":
                        f_idx = 4
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
