import streamlit as st
import os
import json
import pdfplumber
import io
from io import BytesIO

from pdf_engine import detect_igst_status
from test_suite import render_universal_test_suite
from ai_parser_agent import render_ai_parser_agent_ui
from ai_engine import ask_local_ai, save_gemini_api_key, load_gemini_api_key

LOCAL_DATA_DIR = "local_shipper_data"
TEMPLATES_DIR = os.path.join(LOCAL_DATA_DIR, "templates")

def ensure_local_directories():
    if not os.path.exists(LOCAL_DATA_DIR):
        os.makedirs(LOCAL_DATA_DIR)
    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR)

def save_local_shippers():
    ensure_local_directories()
    json_path = os.path.join(LOCAL_DATA_DIR, "shippers_rules.json")
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(st.session_state["shipper_database"], f, indent=4)
    except Exception as e:
        st.error(f"लोकल सेव करने में एरर: {str(e)}")

def get_safe_filename(shipper_name):
    return "".join([c if c.isalnum() else "_" for c in str(shipper_name)]).strip("_")

def save_local_template_file(selected_shipper, uploaded_file_obj):
    ensure_local_directories()
    safe_name = get_safe_filename(selected_shipper)
    file_path = os.path.join(TEMPLATES_DIR, f"{safe_name}_template.xlsx")
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file_obj.getbuffer())
        return True
    except Exception as e:
        st.error(f"टेम्पलेट सेव करने में एरर: {str(e)}")
        return False

def check_template_exists(selected_shipper):
    ensure_local_directories()
    safe_name = get_safe_filename(selected_shipper)
    file_path = os.path.join(TEMPLATES_DIR, f"{safe_name}_template.xlsx")
    return os.path.exists(file_path)

def load_local_shippers():
    ensure_local_directories()
    json_path = os.path.join(LOCAL_DATA_DIR, "shippers_rules.json")
    
    st.session_state["shipper_database"] = {}
    
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

@st.dialog("🧪 Live Header Field Test Result")
def show_field_test_dialog(field_name, rule_data, result_val):
    st.write(f"### 🔍 Header Field: **`{field_name}`**")
    st.markdown("#### 📋 Applied Rule Parameters:")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"* **Keyword:** `{rule_data.get('keyword', 'N/A')}`")
        st.markdown(f"* **Target Cell:** `{rule_data.get('cell', 'N/A')}`")
    with col_b:
        st.markdown(f"* **AI Prompt:** `{rule_data.get('ai_prompt', 'N/A')}`")
        
    st.write("---")
    st.markdown("#### 🎯 Extracted Result for Excel:")
    if "❌" in result_val or not result_val.strip():
        st.error(f"❌ **Not Found!** Value: `{result_val}`")
    else:
        st.success("🎉 **SUCCESS! Extracted Value:**")
        st.code(result_val, language="text")

@st.dialog("📦 Live Item Table Column Test Result")
def show_item_test_dialog(item_field, col_name, prompt_val, extracted_rows):
    st.write(f"### 📦 Item Column: **`{item_field}`** ➡️ Excel Col: **`{col_name}`**")
    st.markdown(f"* **AI Prompt Instruction:** `{prompt_val}`")
    st.write("---")
    st.markdown("#### 🎯 Extracted Row-by-Row List (एक्सेल में जाने वाला डेटा):")
    
    if not extracted_rows:
        st.warning("⚠️ कोई डेटा एक्सट्रैक्ट नहीं हो पाया। कृपया अपना AI प्रॉम्प्ट जांचें।")
    else:
        for idx, r_val in enumerate(extracted_rows, start=1):
            st.markdown(f"**Row {idx} (Col {col_name}):** `{r_val}`")
        st.caption("*(यह असली डेटा आपकी एक्सेल टेम्पलेट के तय कॉलम में फीड होगा)*")

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
                "keyword": "", "cell": "", "ai_prompt": "", "logic": doc_source
            }
            save_local_shippers()
            st.success(f"🎉 फ़ील्ड '{new_field}' जुड़ गया!")
            st.rerun()

def render_shipper_data():
    load_local_shippers()
    
    st.header("🏢 Add Shipper Name & AI-Powered Mapping Builder")
    st.caption("मिनिमलिस्ट AI-संचालित हेडर और आइटम टेबल मैपिंग इंजन।")
    
    # =========================================================================
    # 🔑 GEMINI API KEY CONFIGURATOR BOX (UI)
    # =========================================================================
    with st.expander("🔑 Gemini API Key Settings (यहाँ अपनी API Key दर्ज करें)", expanded=True):
        current_saved_key = load_gemini_api_key()
        masked_key = "********" + current_saved_key[-4:] if len(current_saved_key) > 4 else ""
        
        st.write(f"वर्तमान स्थिति: {'🟢 API Key सेट है' if current_saved_key else '🔴 API Key सेट नहीं है'}")
        if masked_key:
            st.caption(f"Saved Key: {masked_key}")
            
        new_api_key_input = st.text_input("Gemini API Key दर्ज करें:", value="", type="password", placeholder="AIzaSy...")
        
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            if st.button("💾 Save API Key", type="primary", use_container_width=True):
                if new_api_key_input.strip():
                    if save_gemini_api_key(new_api_key_input.strip()):
                        st.success("🎉 Gemini API Key सफलतापूर्वक सेव हो गई!")
                        st.rerun()
                    else:
                        st.error("एरर: की सेव करने में समस्या आई।")
                else:
                    st.error("कृपया वैध API Key दर्ज करें!")
        with col_k2:
            if st.button("🗑️ Delete API Key", type="secondary", use_container_width=True):
                save_gemini_api_key("")
                st.success("🗑️ API Key डिलीट कर दी गई है!")
                st.rerun()

    st.write("---")

    with st.expander("➕ Add New Shipper (नया शिपर जोड़ें)", expanded=False):
        new_shipper_name = st.text_input("नया शिपर कंपनी का नाम दर्ज करें:", key="input_new_shipper_name")
        
        available_parsers = ["parser_welspun", "parser_bkt", "parser_polycab", "parser_vapi_welspun"]
        selected_parser_rule = st.selectbox("इस शिपर के लिए पार्सर रूल (Parser File) चुनें:", available_parsers, key="input_new_shipper_parser")
        
        if st.button("Create New Shipper Profile", type="primary", key="btn_create_shipper"):
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
                    st.success(f"🎉 नया शिपर '{s_clean}' सफलतापूर्वक जुड़ गया है!")
                    st.rerun()
                else:
                    st.warning("⚠️ यह शिपर पहले से मौजूद है!")

    shippers_list = sorted(list(st.session_state["shipper_database"].keys()))
    
    if not shippers_list:
        st.info("ℹ️ वर्तमान में कोई शिपर मौजूद नहीं है। ऊपर दिए गए 'Add New Shipper' से नया शिपर जोड़ें।")
    else:
        selected_shipper = st.selectbox(
            "कॉन्फ़िगर करने के लिए शिपर चुनें:", 
            shippers_list, 
            index=None, 
            placeholder="शिपर का नाम टाइप करें या चुनें..."
        )
        
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            current_assigned_parser = shipper_info.get("item_table_rule_name", "parser_welspun")
            available_parsers = ["parser_welspun", "parser_bkt", "parser_polycab", "parser_vapi_welspun"]
            p_idx = available_parsers.index(current_assigned_parser) if current_assigned_parser in available_parsers else 0
            
            updated_parser_choice = st.selectbox("📌 इस शिपर के लिए एक्टिव पार्सर रूल (Parser File):", available_parsers, index=p_idx, key=f"sel_parser_{selected_shipper}")
            shipper_info["item_table_rule_name"] = updated_parser_choice
            save_local_shippers()

            st.write("---")
            st.subheader("📁 1. टेम्पलेट फ़ाइल अपलोड (Local Excel Template)")
            
            has_saved_template = check_template_exists(selected_shipper)
            
            if has_saved_template:
                st.success(f"✅ 'Full Job Excel Format File (Template)' अपलोडेड और सुरक्षित है।")
                
                col_rep, col_del = st.columns([3, 1])
                with col_rep:
                    f_replace = st.file_uploader("🔄 Replace Template (नई एक्सेल फाइल चुनें):", type=["xlsx", "xls"], key=f"repl_tpl_{selected_shipper}")
                    if f_replace is not None:
                        if st.button("🚀 Confirm & Replace", type="primary", key=f"btn_repl_{selected_shipper}"):
                            if save_local_template_file(selected_shipper, f_replace):
                                st.success("🎉 टेम्पलेट सफलतापूर्वक रिप्लेस हो गई!")
                                st.rerun()
                with col_del:
                    st.write("##") 
                    if st.button("🗑️ Delete Template", type="secondary", use_container_width=True, key=f"btn_del_tpl_{selected_shipper}"):
                        safe_name = get_safe_filename(selected_shipper)
                        file_path = os.path.join(TEMPLATES_DIR, f"{safe_name}_template.xlsx")
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            st.success("🗑️ टेम्पलेट डिलीट हो गई!")
                            st.rerun()
            else:
                st.info("ℹ️ इस शिपर के लिए अभी कोई टेम्पलेट अपलोड नहीं की गई है।")
                f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template) चुनें", type=["xlsx", "xls"], key=f"tpl_{selected_shipper}")
                
                if f_upload is not None:
                    if st.button("🚀 Save Template Locally", type="primary", use_container_width=True, key=f"btn_upload_tpl_{selected_shipper}"):
                        if save_local_template_file(selected_shipper, f_upload):
                            st.success("🎉 टेम्पलेट एक्सेल फाइल फोल्डर में सफलतापर्वक सेव हो गई!")
                            st.rerun()

            st.write("---")
            st.subheader("🧪 2. Instant PDF Upload & Live Data Test Engine")
            test_pdf = st.file_uploader("➡️ टेस्ट करने के लिए इनवॉइस PDF अपलोड करें", type=["pdf"], key=f"test_pdf_{selected_shipper}")
            
            if test_pdf:
                st.session_state["cached_pdf_bytes"] = test_pdf.getvalue()
                pdf_lines = []
                pdf_text = ""
                with pdfplumber.open(test_pdf) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            pdf_text += t + "\n"
                            pdf_lines.extend(t.split("\n"))
                st.session_state["cached_pdf_lines"] = pdf_lines
                st.session_state["cached_pdf_text"] = pdf_text
                st.success(f"📄 PDF अपलोड है ({len(pdf_lines)} पंक्तियाँ)।")

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
                h1, h2, h3, h4, h5, h6, h7 = st.columns([1.8, 1.8, 0.9, 2.2, 1.3, 0.5, 0.8])
                with h1: st.markdown("**Field Name**")
                with h2: st.markdown("**Keyword**")
                with h3: st.markdown("**Cell**")
                with h4: st.markdown("**🤖 AI Instruction / Prompt**")
                with h5: st.markdown("**Source Doc**")
                with h6: st.markdown("**Del**")
                with h7: st.markdown("**Test**")

            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7 = st.columns([1.8, 1.8, 0.9, 2.2, 1.3, 0.5, 0.8])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c3: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                with c4: ai_p = st.text_input(f"ai_{field}", value=s_val.get("ai_prompt", ""), placeholder="उदा: कीवर्ड के आगे वाली वैल्यू लो", label_visibility="collapsed")
                with c5: final_logic = st.selectbox(f"logic_{field}", doc_source_options, index=doc_source_options.index(s_val.get("logic", doc_source_options[0])) if s_val.get("logic") in doc_source_options else 0, label_visibility="collapsed") 
                with c6:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field]
                        save_local_shippers()
                        st.rerun()
                with c7:
                    if st.button("⚡ Test", key=f"test_btn_{field}"):
                        curr_pdf_text = st.session_state.get("cached_pdf_text", "")
                        if not curr_pdf_text:
                            st.toast("⚠️ पहले ऊपर PDF अपलोड करें!")
                        else:
                            with st.spinner("Gemini AI डेटा ढूँढ रहा है..."):
                                header_test_prompt = [
                                    {"role": "system", "content": "You are an expert Indian Customs invoice data extraction AI. Extract the exact requested value based on the user's keyword and prompt instruction. Return ONLY the extracted value without any extra words or conversational text."},
                                    {"role": "user", "content": f"""
                                    Invoice Text Content:
                                    ----------------------------------
                                    {curr_pdf_text[:4000]}
                                    ----------------------------------
                                    
                                    Field Name: '{edited_name}'
                                    Keyword given: '{ky}'
                                    User Instruction / Prompt: '{ai_p}'
                                    
                                    Task: Find the value near the keyword following the instruction. Return ONLY the value.
                                    """}
                                ]
                                res_val = ask_local_ai(header_test_prompt)
                                show_field_test_dialog(edited_name, {"keyword": ky, "cell": cl, "ai_prompt": ai_p}, res_val if res_val else "❌ (Not Found)")
                
                updated_rules[edited_name] = {"keyword": ky, "cell": cl, "ai_prompt": ai_p, "logic": final_logic}
                
            shipper_info["mapping_rules"] = updated_rules

            st.write("---")
            
            # =========================================================================
            # 🛡️ SECTION 4: COLUMN V AUTO-DETECTION CONFIGURATOR
            # =========================================================================
            st.subheader("🛡️ Column V Auto-Detection Configurator (LUT vs Paid 'P')")
            igst_cfg = shipper_info.setdefault("igst_config", {"lut_keywords": "", "paid_keywords": ""})
            
            s_lut, s_paid = st.columns(2)
            with s_lut:
                s_lut_val = st.text_area("📌 LUT Detection Keywords:", value=igst_cfg.get("lut_keywords", ""), key=f"lut_kw_{selected_shipper}")
            with s_paid:
                s_paid_val = st.text_area("📌 Paid (P) Detection Keywords:", value=igst_cfg.get("paid_keywords", ""), key=f"paid_kw_{selected_shipper}")
                
            shipper_info["igst_config"] = {"lut_keywords": s_lut_val, "paid_keywords": s_paid_val}
            st.write("---")

            # =========================================================================
            # 📦 SECTION 5: DYNAMIC ITEM TABLE COLUMN BUILDER (Gemini AI-Powered Live Extraction)
            # =========================================================================
            st.subheader("📦 Dynamic Item Table Column Builder (Gemini AI-Powered)")
            st.caption("आइटम टेबल के लिए कॉलम, एक्सेल कॉलम और AI निर्देश यहाँ दर्ज करें:")
            
            item_rules = shipper_info.setdefault("item_table_rules", {})
            updated_item_rules = {}
            
            if item_rules:
                ic1, ic2, ic3, ic4, ic5 = st.columns([2.2, 1.2, 3.5, 0.5, 0.8])
                with ic1: st.markdown("**Item Field Name**")
                with ic2: st.markdown("**Excel Col**")
                with ic3: st.markdown("**🤖 AI Table Prompt**")
                with ic4: st.markdown("**Del**")
                with ic5: st.markdown("**Test**")
            
            for item_field in list(item_rules.keys()):
                ir = item_rules[item_field]
                ic1, ic2, ic3, ic4, ic5 = st.columns([2.2, 1.2, 3.5, 0.5, 0.8])
                
                with ic1: ie_field = st.text_input(f"if_{selected_shipper}_{item_field}", value=item_field, label_visibility="collapsed")
                with ic2: ie_col = st.text_input(f"ic_{selected_shipper}_{item_field}", value=ir.get("col", "K"), label_visibility="collapsed").upper()
                with ic3: ie_prompt = st.text_input(f"ip_{selected_shipper}_{item_field}", value=ir.get("ai_prompt", ""), placeholder="उदा: PDF की हर row से HS Code निकालो", label_visibility="collapsed")
                with ic4:
                    if st.button("🗑️", key=f"idel_{selected_shipper}_{item_field}"):
                        del shipper_info["item_table_rules"][item_field]
                        save_local_shippers()
                        st.rerun()
                with ic5:
                    if st.button("⚡ Test", key=f"test_item_btn_{item_field}"):
                        curr_pdf_text = st.session_state.get("cached_pdf_text", "")
                        if not curr_pdf_text:
                            st.toast("⚠️ पहले ऊपर PDF अपलोड करें!")
                        else:
                            with st.spinner("Gemini AI असली PDF से आइटम्स की लिस्ट निकाल रहा है..."):
                                table_extraction_prompt = [
                                    {"role": "system", "content": "You are an expert Indian Customs invoice data extraction AI."},
                                    {"role": "user", "content": f"""
                                    Here is the extracted invoice text:
                                    ----------------------------------
                                    {curr_pdf_text[:4000]}
                                    ----------------------------------
                                    
                                    The user wants to extract the column field '{ie_field}' for all items in the table.
                                    Specific instruction/prompt given by user: '{ie_prompt}'
                                    
                                    Task: Extract the list of values for '{ie_field}' row-by-row based on the instruction.
                                    Return ONLY a valid JSON list of strings (e.g., ["value1", "value2", "value3"]). Do not add conversational filler.
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
                                    
                                show_item_test_dialog(ie_field, ie_col, ie_prompt, extracted_list)
                        
                updated_item_rules[ie_field] = {"col": ie_col, "ai_prompt": ie_prompt}
                
            shipper_info["item_table_rules"] = updated_item_rules
            
            if st.button("➕ Add Item Column", key=f"add_item_col_{selected_shipper}", type="secondary"):
                shipper_info["item_table_rules"]["New Item Field"] = {"col": "K", "ai_prompt": ""}
                save_local_shippers()
                st.rerun()
                
            st.write("---")

            if st.button("💾 Save Rules Locally", type="primary", use_container_width=True, key="btn_save_rules_local"):
                save_local_shippers()
                st.success("🎉 आपके सारे रूल्स लोकल फोल्डर में सुरक्षित सेव हो गए हैं!")

            render_universal_test_suite(selected_shipper)
            
            # 🤖 AI PARSER AGENT INTEGRATION
            render_ai_parser_agent_ui(selected_shipper, shipper_info)
