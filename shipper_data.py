import streamlit as st
import os
import json
import pdfplumber
import io
from io import BytesIO

from pdf_engine import detect_igst_status
from test_suite import render_universal_test_suite
from ai_engine import ask_local_ai, create_new_parser_file_on_github, WEB_APP_URL
from ai_parser_agent import render_ai_parser_agent_ui
from google_sheet_sync import (
    fetch_all_from_sheet, push_rules_to_sheet, push_template_file_to_sheet, 
    load_template_bytes_from_sheet, save_gemini_api_key_to_sheet, load_gemini_api_key_from_sheet
)
import requests

LOCAL_DATA_DIR = "local_shipper_data"
TEMPLATES_DIR = os.path.join(LOCAL_DATA_DIR, "templates")

def ensure_local_directories():
    if not os.path.exists(LOCAL_DATA_DIR):
        os.makedirs(LOCAL_DATA_DIR)
    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR)

def fetch_data_from_google_sheet():
    try:
        data = fetch_all_from_sheet()
        if isinstance(data, dict) and data:
            return data
    except Exception as e:
        pass
    return {}

def save_local_shippers():
    ensure_local_directories()
    json_path = os.path.join(LOCAL_DATA_DIR, "shippers_rules.json")
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(st.session_state["shipper_database"], f, indent=4)
        shippers_payload = {}
        for s_name, s_data in st.session_state["shipper_database"].items():
            shippers_payload[s_name] = {
                "mapping_rules": s_data.get("mapping_rules", {}),
                "item_table_rules": s_data.get("item_table_rules", {}),
                "item_table_rule_name": s_data.get("item_table_rule_name", "parser_welspun"),
                "igst_config": s_data.get("igst_config", {})
            }
        push_rules_to_sheet(shippers_payload)
    except Exception as e:
        st.error(f"सेव करने में एरर: {str(e)}")

def get_safe_filename(shipper_name):
    return "".join([c if c.isalnum() else "_" for c in str(shipper_name)]).strip("_")

def load_local_shippers():
    ensure_local_directories()
    
    # 🚀 ऑप्टिमाइज़ेशन: यदि सेशन में डेटा पहले से मौजूद है, तो बार-बार गूगल शीट को कॉल नहीं किया जाएगा
    if "shipper_database" in st.session_state and st.session_state["shipper_database"]:
        return

    sheet_data = fetch_data_from_google_sheet()
    shippers_dict = sheet_data.get("shippers", {}) if isinstance(sheet_data, dict) else {}
    if shippers_dict:
        st.session_state["shipper_database"] = shippers_dict
    else:
        json_path = os.path.join(LOCAL_DATA_DIR, "shippers_rules.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    if isinstance(saved_data, dict) and saved_data:
                        st.session_state["shipper_database"] = saved_data
            except Exception:
                pass

def ensure_default_shipper():
    load_local_shippers()

@st.dialog("🧪 Live Header Field Test & Verification")
def show_field_test_dialog(field_name, rule_data, result_val, gen_logic, selected_shipper, field_key):
    st.write(f"### 🔍 Header Field: **`{field_name}`**")
    st.markdown("#### 📋 Rule Parameters:")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"* **Source Doc:** `{rule_data.get('logic', 'N/A')}`")
        st.markdown(f"* **Keyword:** `{rule_data.get('keyword', 'N/A')}`")
    with col_b:
        st.markdown(f"* **Target Cell:** `{rule_data.get('cell', 'N/A')}`")
        st.markdown(f"* **Result Example:** `{rule_data.get('result_example', 'N/A')}`")
        
    st.write("---")
    st.markdown("#### 🎯 AI Extracted Result & Suggested Regex Logic:")
    if "❌" in result_val or not result_val.strip():
        st.error(f"❌ **Not Found!** Value: `{result_val}`")
    else:
        st.success("🎉 **Extracted Value:**")
        st.code(result_val, language="text")
        
        if gen_logic:
            st.markdown("#### ⚡ Copy this Logic into your 'Logic (Regex)' column:")
            st.code(gen_logic, language="python")
        
    st.write("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Re-check", use_container_width=True, key=f"rec_h_{field_key}"):
            st.toast("Re-running AI check...")
            st.rerun()
    with col_btn2:
        if st.button("❌ Close", use_container_width=True, key=f"can_h_{field_key}"):
            st.info("Closing dialog.")
            st.rerun()

@st.dialog("📦 Live Item Table Column Test & Verification")
def show_item_test_dialog(item_field, rule_data, extracted_rows, selected_shipper):
    st.write(f"### 📦 Item Column: **`{item_field}`** ➡️ Excel Col: **`{rule_data.get('col', 'N/A')}`**")
    st.markdown(f"* **Source Doc:** `{rule_data.get('logic', 'N/A')}`")
    st.markdown(f"* **AI Prompt Instruction:** `{rule_data.get('ai_prompt', 'N/A')}`")
    st.markdown(f"* **Result Example:** `{rule_data.get('result_example', 'N/A')}`")
    st.write("---")
    st.markdown("#### 🎯 Extracted Row-by-Row List:")
    if not extracted_rows:
        st.warning("⚠️ कोई डेटा एक्सट्रैक्ट नहीं हो पाया। कृपया अपना AI प्रॉम्प्ट या Result Example जांचें।")
    else:
        for idx, r_val in enumerate(extracted_rows, start=1):
            st.markdown(f"**Row {idx} (Col {rule_data.get('col', 'N/A')}):** `{r_val}`")
            
    st.write("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("✅ Accept", type="primary", use_container_width=True, key=f"acc_i_{item_field}"):
            st.success("🎉 Item Rule Accepted & Saved to Google Sheet!")
            save_local_shippers()
            st.rerun()
    with col_btn2:
        if st.button("🔄 Re-check", use_container_width=True, key=f"rec_i_{item_field}"):
            st.toast("Re-running AI check...")
            st.rerun()
    with col_btn3:
        if st.button("❌ Cancel", use_container_width=True, key=f"can_i_{item_field}"):
            st.info("Action cancelled.")
            st.rerun()

@st.dialog("➕ Add New Custom Header Field")
def add_custom_header_field_dialog(selected_shipper):
    st.write("यहाँ नया हेडर फ़ील्ड जोड़ें:")
    new_field = st.text_input("Field Name (उदा: Invoice No, GST Inv No):")
    doc_source = st.selectbox(
        "यह डेटा किस डॉक्यूमेंट से लिया जाएगा?",
        ["Main Invoice", "GST Invoice (PDF/Excel)", "DEEC Declaration (PDF/Excel)"]
    )
    if st.button("Confirm & Add Field", type="primary"):
        if not new_field.strip():
            st.error("फ़ील्ड नाम खाली नहीं हो सकता!")
        else:
            rules = st.session_state["shipper_database"][selected_shipper].setdefault("mapping_rules", {})
            rules[new_field.strip()] = {
                "logic": doc_source, "keyword": "", "cell": "", "ai_prompt": "", "result_example": "", "extracted_logic": ""
            }
            save_local_shippers()
            st.success(f"🎉 फ़ील्ड '{new_field}' गूगल शीट पर सिंक हो गया!")
            st.rerun()

def render_shipper_data():
    load_local_shippers()
    
    st.header("🏢 Add Shipper Name & AI-Powered Mapping Builder")
    st.caption("मिनिमलिस्ट AI-संचालित हेडर और आइटम टेबल मैपिंग इंजन (Google Sheet Synced)[cite: 4].")
    
    # 🔑 Gemini API Key Box (Google Sheet Synced)
    with st.expander("🔑 Gemini API Key Settings", expanded=False):
        current_saved_key = load_gemini_api_key_from_sheet()
        if current_saved_key:
            st.write("वर्तमान स्थिति: 🟢 Google Sheet पर API Key सेट है")
            if st.button("🗑️ Delete API Key", type="secondary"):
                save_gemini_api_key_to_sheet("")
                st.success("🗑️ API Key डिलीट कर दी गई है!")
                st.rerun()
        else:
            st.write("वर्तमान स्थिति: 🔴 API Key सेट नहीं है")
            new_key = st.text_input("Gemini API Key दर्ज करें:", type="password")
            if st.button("💾 Save API Key to Sheet", type="primary"):
                if new_key.strip() and save_gemini_api_key_to_sheet(new_key.strip()):
                    st.success("🎉 API Key गूगल शीट पर सेव हो गई!")
                    st.rerun()

    st.write("---")

    # ➕ Add New Shipper & Parser Creator
    with st.expander("➕ Add New Shipper & Create Parser File", expanded=False):
        new_shipper_name = st.text_input("नया शिपर कंपनी का नाम दर्ज करें:")
        
        st.markdown("#### 📂 Parser File Management")
        new_parser_name_input = st.text_input("नया पार्सर नाम दर्ज करें (उदा: parser_vapi_welspun):", placeholder="parser_...")
        github_pat_input = st.text_input("GitHub Personal Access Token (PAT):", type="password", placeholder="ghp_...")
        
        if st.button("🚀 Create Parser File on GitHub", type="secondary"):
            if not new_parser_name_input.strip() or not github_pat_input.strip():
                st.error("कृपया पार्सर का नाम और GitHub Token दोनों दर्ज करें!")
            else:
                success, msg = create_new_parser_file_on_github(new_parser_name_input.strip(), github_pat_input.strip())
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
                    
        available_parsers = ["parser_welspun", "parser_bkt", "parser_polycab", "parser_vapi_welspun"]
        if new_parser_name_input.strip():
            clean_p = new_parser_name_input.strip().lower()
            if not clean_p.endswith(".py"): clean_p += ".py"
            if not clean_p.startswith("parser_"): clean_p = f"parser_{clean_p}"
            if clean_p not in available_parsers: available_parsers.append(clean_p)
            
        selected_parser_rule = st.selectbox("इस शिपर के लिए पार्सर रूल चुनें:", available_parsers)
        
        if st.button("Create New Shipper Profile", type="primary"):
            if not new_shipper_name.strip():
                st.error("शिपर का नाम खाली नहीं हो सकता!")
            else:
                s_clean = new_shipper_name.strip()
                if s_clean not in st.session_state["shipper_database"]:
                    st.session_state["shipper_database"][s_clean] = {
                        "allowed_uploads": ["Full Job Excel Format File"],
                        "uploaded_files": {},
                        "mapping_rules": {},
                        "item_table_rules": {},
                        "item_table_rule_name": selected_parser_rule,
                        "igst_config": {"lut_keywords": "", "paid_keywords": ""}
                    }
                    save_local_shippers()
                    st.success(f"🎉 नया शिपर '{s_clean}' गूगल शीट पर सफलतापर्वक जुड़ गया है!")
                    st.rerun()
                else:
                    st.warning("⚠️ यह शिपर पहले से मौजूद है!")

    shippers_list = sorted(list(st.session_state["shipper_database"].keys()))
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None, placeholder="शिपर चुनें...")
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            current_assigned_parser = shipper_info.get("item_table_rule_name", "parser_welspun")
            p_idx = available_parsers.index(current_assigned_parser) if current_assigned_parser in available_parsers else 0
            updated_parser_choice = st.selectbox("📌 इस शिपर के लिए एक्टिव पार्सर रूल (Parser File):", available_parsers, index=p_idx, key=f"sel_parser_{selected_shipper}")
            shipper_info["item_table_rule_name"] = updated_parser_choice
            save_local_shippers()

            # 📁 1. टेम्पलेट फ़ाइल अपलोड (Google Sheet Synced)
            st.write("---")
            st.subheader("📁 1. टेम्पलेट फ़ाइल अपलोड (Full Job Excel Template)")
            
            t_bytes = load_template_bytes_from_sheet(selected_shipper)
            has_saved_template = t_bytes is not None and len(t_bytes) > 0
            
            if has_saved_template:
                st.success(f"✅ 'Full Job Excel Format File (Template)' गूगल शीट पर अपलोडेड एवं सुरक्षित है।")
                col_rep, col_del = st.columns([3, 1])
                with col_rep:
                    f_replace = st.file_uploader("🔄 Replace Template (नई एक्सेल फाइल चुनें):", type=["xlsx", "xls"], key=f"repl_tpl_{selected_shipper}")
                    if f_replace is not None:
                        if st.button("🚀 Confirm & Replace", type="primary", key=f"btn_repl_{selected_shipper}"):
                            with st.spinner("⏳ गूगल शीट पर टेम्पलेट अपलोड हो रही है..."):
                                if push_template_file_to_sheet(selected_shipper, f_replace.getvalue()):
                                    st.success("🎉 टेम्पलेट सफलतापूर्वक गूगल शीट पर रिप्लेस हो गई!")
                                    st.rerun()
                                else:
                                    st.error("❌ अपलोड फेल हो गया!")
                with col_del:
                    st.write("##") 
                    if st.button("🗑️ Delete Template", type="secondary", use_container_width=True, key=f"btn_del_tpl_{selected_shipper}"):
                        push_template_file_to_sheet(selected_shipper, b"")
                        st.success("🗑️ टेम्पलेट डिलीट हो गई!")
                        st.rerun()
            else:
                st.info("ℹ️ इस शिपर के लिए अभी कोई टेम्पलेट अपलोड नहीं की गई है।")
                f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template) चुनें", type=["xlsx", "xls"], key=f"tpl_{selected_shipper}")
                if f_upload is not None:
                    if st.button("🚀 Save Template to Google Sheet", type="primary", use_container_width=True, key=f"btn_upload_tpl_{selected_shipper}"):
                        with st.spinner("⏳ गूगल शीट पर टेम्पलेट अपलोड हो रही है..."):
                            if push_template_file_to_sheet(selected_shipper, f_upload.getvalue()):
                                st.success("🎉 टेम्पलेट एक्सेल फाइल सफलतापर्वक गूगल शीट पर सेव हो गई!")
                                st.rerun()
                            else:
                                st.error("❌ अपलोड फेल हो गया!")

            # 🧪 2. Instant PDF Upload & Live Data Test Engine
            st.write("---")
            st.subheader("🧪 2. Instant PDF Upload & Live Data Test Engine")
            test_pdf = st.file_uploader("➡️ टेस्ट करने के लिए सैंपल इनवॉइस PDF अपलोड करें", type=["pdf"], key=f"test_pdf_{selected_shipper}")
            if test_pdf:
                st.session_state["cached_pdf_bytes"] = test_pdf.getvalue()
                pdf_lines, pdf_text = [], ""
                with pdfplumber.open(test_pdf) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            pdf_text += t + "\n"
                            pdf_lines.extend(t.split("\n"))
                st.session_state["cached_pdf_lines"] = pdf_lines
                st.session_state["cached_pdf_text"] = pdf_text
                st.success(f"📄 PDF अपलोड है ({len(pdf_lines)} पंक्तियाँ)।")

            # 🛠️ 3. Header Fields Mapping Rules (अब 'Logic' कॉलम के साथ)
            st.write("---")
            c_title, c_add_h = st.columns([7, 3])
            with c_title:
                st.subheader("🛠️ 3. Header Fields Mapping Rules (Gemini AI-Powered)")
            with c_add_h:
                if st.button("➕ Add Header Field", type="secondary", use_container_width=True):
                    add_custom_header_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            doc_source_options = ["Main Invoice", "GST Invoice (PDF/Excel)", "DEEC Declaration (PDF/Excel)"]
            
            if current_rules:
                h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([1.3, 1.0, 1.2, 0.6, 1.4, 1.2, 1.5, 0.4, 0.6])
                with h1: st.markdown("**Field Name**")
                with h2: st.markdown("**Source Doc**")
                with h3: st.markdown("**Keyword**")
                with h4: st.markdown("**Cell**")
                with h5: st.markdown("**🤖 AI Prompt**")
                with h6: st.markdown("**Result Ex**")
                with h7: st.markdown("**⚡ Logic (Regex)**")
                with h8: st.markdown("**Del**")
                with h9: st.markdown("**Test**")

            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([1.3, 1.0, 1.2, 0.6, 1.4, 1.2, 1.5, 0.4, 0.6])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: final_logic = st.selectbox(f"logic_{field}", doc_source_options, index=doc_source_options.index(s_val.get("logic", doc_source_options[0])) if s_val.get("logic") in doc_source_options else 0, label_visibility="collapsed") 
                with c3: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                with c5: ai_p = st.text_input(f"ai_{field}", value=s_val.get("ai_prompt", ""), placeholder="उदा: कीवर्ड के आगे", label_visibility="collapsed")
                with c6: res_ex = st.text_input(f"ex_{field}", value=s_val.get("result_example", ""), placeholder="उदा: TUMB", label_visibility="collapsed")
                
                saved_ext_logic = s_val.get("extracted_logic", "")
                with c7: ext_logic = st.text_input(f"elogic_{field}", value=saved_ext_logic, placeholder="AI Logic / Regex", label_visibility="collapsed")
                
                with c8:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del shipper_info["mapping_rules"][field]
                        save_local_shippers()
                        st.rerun()
                with c9:
                    if st.button("⚡ Test", key=f"test_btn_{field}"):
                        curr_pdf_text = st.session_state.get("cached_pdf_text", "")
                        if not curr_pdf_text:
                            st.toast("⚠️ पहले ऊपर PDF अपलोड करें!")
                        else:
                            with st.spinner("Gemini AI वैल्यू और पक्का Regex लॉजिक तैयार कर रहा है..."):
                                header_test_prompt = [
                                    {"role": "system", "content": "You are an expert Indian Customs invoice extraction AI. First, find the requested value. Second, write a clean Python regex or text extraction logic snippet that can find this exact pattern. Output format exactly like this:\nValue: [extracted value]\nLogic: [python/regex logic snippet]"},
                                    {"role": "user", "content": f"""
                                    Invoice Text:
                                    {curr_pdf_text[:4000]}
                                    
                                    Field Name: '{edited_name}'
                                    Keyword: '{ky}'
                                    Prompt: '{ai_p}'
                                    Result Example expected: '{res_ex}'
                                    """}
                                ]
                                ai_res = ask_local_ai(header_test_prompt)
                                res_val = ""
                                generated_logic = ""
                                
                                if ai_res and "Value:" in ai_res and "Logic:" in ai_res:
                                    parts = ai_res.split("Logic:")
                                    res_val = parts[0].replace("Value:", "").strip()
                                    generated_logic = parts[1].strip()
                                else:
                                    res_val = ai_res.strip() if ai_res else "❌ (Not Found)"
                                    generated_logic = f"re.search(r'{ky}.*?([A-Za-z0-9-]+)', text)"

                                show_field_test_dialog(edited_name, {"logic": final_logic, "keyword": ky, "cell": cl, "ai_prompt": ai_p, "result_example": res_ex}, res_val, generated_logic, selected_shipper, field)
                
                updated_rules[edited_name] = {
                    "logic": final_logic, "keyword": ky, "cell": cl, "ai_prompt": ai_p, "result_example": res_ex, "extracted_logic": ext_logic
                }
            shipper_info["mapping_rules"] = updated_rules

            st.write("---")

            # 🛡️ SECTION 4: COLUMN V AUTO-DETECTION CONFIGURATOR
            st.subheader("🛡️ Column V Auto-Detection Configurator (LUT vs Paid 'P')")
            igst_cfg = shipper_info.setdefault("igst_config", {"lut_keywords": "", "paid_keywords": ""})
            s_lut, s_paid = st.columns(2)
            with s_lut:
                s_lut_val = st.text_area("📌 LUT Detection Keywords:", value=igst_cfg.get("lut_keywords", ""), key=f"lut_kw_{selected_shipper}")
            with s_paid:
                s_paid_val = st.text_area("📌 Paid (P) Detection Keywords:", value=igst_cfg.get("paid_keywords", ""), key=f"paid_kw_{selected_shipper}")
            shipper_info["igst_config"] = {"lut_keywords": s_lut_val, "paid_keywords": s_paid_val}
            
            st.write("---")

            # 📦 SECTION 5: DYNAMIC ITEM TABLE COLUMN BUILDER
            st.subheader("📦 4. Dynamic Item Table Column Builder (Gemini AI-Powered)")
            st.caption("आइटम टेबल के लिए कॉलम, सोर्स डॉक्यूमेंट, एक्सेल कॉलम, AI निर्देश और उदाहरण यहाँ दर्ज करें:")
            
            item_rules = shipper_info.setdefault("item_table_rules", {})
            updated_item_rules = {}
            
            if item_rules:
                ic1, ic2, ic3, ic4, ic5, ic6, ic7 = st.columns([1.8, 1.2, 0.8, 2.2, 1.5, 0.4, 0.7])
                with ic1: st.markdown("**Item Field Name**")
                with ic2: st.markdown("**Source Doc**")
                with ic3: st.markdown("**Excel Col**")
                with ic4: st.markdown("**🤖 AI Table Prompt**")
                with ic5: st.markdown("**Result Example**")
                with ic6: st.markdown("**Del**")
                with ic7: st.markdown("**Test**")
            
            for item_field in list(item_rules.keys()):
                ir = item_rules[item_field]
                ic1, ic2, ic3, ic4, ic5, ic6, ic7 = st.columns([1.8, 1.2, 0.8, 2.2, 1.5, 0.4, 0.7])
                
                with ic1: ie_field = st.text_input(f"if_{selected_shipper}_{item_field}", value=item_field, label_visibility="collapsed")
                with ic2: ie_logic = st.selectbox(f"ilogic_{selected_shipper}_{item_field}", doc_source_options, index=doc_source_options.index(ir.get("logic", doc_source_options[0])) if ir.get("logic") in doc_source_options else 0, label_visibility="collapsed")
                with ic3: ie_col = st.text_input(f"ic_{selected_shipper}_{item_field}", value=ir.get("col", "K"), label_visibility="collapsed").upper()
                with ic4: ie_prompt = st.text_input(f"ip_{selected_shipper}_{item_field}", value=ir.get("ai_prompt", ir.get("rule", "")), placeholder="उदा: हर row से HS Code लो", label_visibility="collapsed")
                with ic5: ie_ex = st.text_input(f"iex_{selected_shipper}_{item_field}", value=ir.get("result_example", ""), placeholder="उदा: 8504, 8507", label_visibility="collapsed")
                
                with ic6:
                    if st.button("🗑️", key=f"idel_{selected_shipper}_{item_field}"):
                        del shipper_info["item_table_rules"][item_field]
                        save_local_shippers()
                        st.rerun()
                with ic7:
                    if st.button("⚡ Test", key=f"test_item_btn_{item_field}"):
                        curr_pdf_text = st.session_state.get("cached_pdf_text", "")
                        if not curr_pdf_text:
                            st.toast("⚠️ पहले ऊपर PDF अपलोड करें!")
                        else:
                            with st.spinner("Gemini AI असली PDF से आइटम्स की लिस्ट निकाल रहा है..."):
                                table_extraction_prompt = [
                                    {"role": "system", "content": "You are an expert Indian Customs invoice item table extraction AI."},
                                    {"role": "user", "content": f"""
                                    Here is the extracted invoice text:
                                    ----------------------------------
                                    {curr_pdf_text[:4000]}
                                    ----------------------------------
                                    
                                    Field Name: '{ie_field}'
                                    Prompt Instruction: '{ie_prompt}'
                                    Result Example expected: '{ie_ex}'
                                    
                                    Task: Extract the list of values for '{ie_field}' row-by-row based on the instruction and example.
                                    Return ONLY a valid JSON list of strings (e.g., ["val1", "val2", "val3"]). No extra text.
                                    """}
                                ]
                                ai_res = ask_local_ai(table_extraction_prompt)
                                extracted_list = []
                                try:
                                    import re
                                    json_match = re.search(r'\[(.*?)\]', ai_res, re.DOTALL)
                                    if json_match:
                                        extracted_list = json.loads(json_match.group(0))
                                    else:
                                        extracted_list = [line.strip() for line in ai_res.split('\n') if line.strip()]
                                except:
                                    extracted_list = [ai_res]
                                    
                                show_item_test_dialog(ie_field, {"col": ie_col, "logic": ie_logic, "ai_prompt": ie_prompt, "result_example": ie_ex}, extracted_list, selected_shipper)
                        
                updated_item_rules[ie_field] = {
                    "col": ie_col, "logic": ie_logic, "ai_prompt": ie_prompt, "result_example": ie_ex, "type": "PDF Row Item", "rule": ie_prompt
                }
                
            shipper_info["item_table_rules"] = updated_item_rules
            
            if st.button("➕ Add Item Column", key=f"add_item_col_{selected_shipper}", type="secondary"):
                shipper_info["item_table_rules"]["New Item Field"] = {"col": "K", "logic": "Main Invoice", "ai_prompt": "", "result_example": "", "type": "PDF Row Item", "rule": ""}
                save_local_shippers()
                st.rerun()
                
            st.write("---")

            if st.button("💾 Save Rules & Sync to Google Sheet", type="primary", use_container_width=True, key="btn_save_rules_local"):
                save_local_shippers()
                st.success("🎉 आपके सारे रूल्स और सेटिंग्स सफलतापूर्वक गूगल शीट पर सेव और सिंक हो गए हैं!")

            # 🤖 AI Parser Code & Rule Assistant UI Integration
            render_ai_parser_agent_ui(selected_shipper, shipper_info)
