import streamlit as st
import os
import json
import pdfplumber
import io
from io import BytesIO

from pdf_engine import detect_igst_status
from test_suite import render_universal_test_suite
from ai_engine import ask_local_ai, save_gemini_api_key, load_gemini_api_key, push_all_to_sheet, create_new_parser_file_on_github

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
        push_all_to_sheet(st.session_state["shipper_database"])
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
    if "shipper_database" not in st.session_state or not st.session_state["shipper_database"]:
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

def fetch_data_from_google_sheet():
    load_local_shippers()
    return st.session_state.get("shipper_database", {})

# 🧪 Interactive Test Dialog with Accept / Re-check / Cancel Workflow
@st.dialog("🧪 Live Header Field Test & Verification")
def show_field_test_dialog(field_name, rule_data, result_val, selected_shipper, field_key):
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
    st.markdown("#### 🎯 AI Extracted Result:")
    if "❌" in result_val or not result_val.strip():
        st.error(f"❌ **Not Found!** Value: `{result_val}`")
    else:
        st.success("🎉 **Extracted Value:**")
        st.code(result_val, language="text")
        
    st.write("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("✅ Accept", type="primary", use_container_width=True):
            st.success("🎉 Rule Accepted & Saved!")
            save_local_shippers()
            st.rerun()
    with col_btn2:
        if st.button("🔄 Re-check", use_container_width=True):
            st.toast("Re-running AI check...")
            st.rerun()
    with col_btn3:
        if st.button("❌ Cancel", use_container_width=True):
            st.info("Action cancelled.")
            st.rerun()

@st.dialog("📦 Live Item Table Column Test Result")
def show_item_test_dialog(item_field, col_name, prompt_val, extracted_rows):
    st.write(f"### 📦 Item Column: **`{item_field}`** ➡️ Excel Col: **`{col_name}`**")
    st.markdown(f"* **AI Prompt Instruction:** `{prompt_val}`")
    st.write("---")
    st.markdown("#### 🎯 Extracted Row-by-Row List:")
    if not extracted_rows:
        st.warning("⚠️ कोई डेटा एक्सट्रैक्ट नहीं हो पाया। कृपया अपना AI प्रॉम्प्ट या Result Example जांचें।")
    else:
        for idx, r_val in enumerate(extracted_rows, start=1):
            st.markdown(f"**Row {idx} (Col {col_name}):** `{r_val}`")

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
                "logic": doc_source, "keyword": "", "cell": "", "ai_prompt": "", "result_example": ""
            }
            save_local_shippers()
            st.success(f"🎉 फ़ील्ड '{new_field}' जुड़ गया!")
            st.rerun()

def render_shipper_data():
    load_local_shippers()
    
    st.header("🏢 Add Shipper Name & AI-Powered Mapping Builder")
    st.caption("मिनिमलिस्ट AI-संचालित हेडर और आइटम टेबल मैपिंग इंजन।")
    
    # 🔑 Gemini API Key Box
    with st.expander("🔑 Gemini API Key Settings", expanded=False):
        current_saved_key = load_gemini_api_key()
        if current_saved_key:
            st.write("वर्तमान स्थिति: 🟢 API Key सेट है")
            if st.button("🗑️ Delete API Key", type="secondary"):
                save_gemini_api_key("")
                st.success("🗑️ API Key डिलीट कर दी गई है!")
                st.rerun()
        else:
            st.write("वर्तमान स्थिति: 🔴 API Key सेट नहीं है")
            new_key = st.text_input("Gemini API Key दर्ज करें:", type="password")
            if st.button("💾 Save API Key", type="primary"):
                if new_key.strip() and save_gemini_api_key(new_key.strip()):
                    st.success("🎉 API Key सेव हो गई!")
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
                    st.success(f"🎉 नया शिपर '{s_clean}' सफलतापूर्वक जुड़ गया है!")
                    st.rerun()
                else:
                    st.warning("⚠️ यह शिपर पहले से मौजूद है!")

    shippers_list = sorted(list(st.session_state["shipper_database"].keys()))
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None, placeholder="शिपर चुनें...")
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            # 🧪 2. Instant PDF Upload & Live Data Test Engine
            st.subheader("🧪 1. Instant PDF Upload & Live Data Test Engine")
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

            st.write("---")
            c_title, c_add_h = st.columns([7, 3])
            with c_title:
                st.subheader("🛠️ 2. Header Fields Mapping Rules (Gemini AI-Powered)")
            with c_add_h:
                if st.button("➕ Add Header Field", type="secondary", use_container_width=True):
                    add_custom_header_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            doc_source_options = ["Main Invoice", "GST Invoice (PDF/Excel)", "DEEC Declaration (PDF/Excel)"]
            
            # कॉलम स्ट्रक्चर: Field Name, Source Doc, Keyword, Cell, AI Prompt, Result Example, Del, Test
            if current_rules:
                h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([1.5, 1.2, 1.5, 0.8, 1.8, 1.5, 0.4, 0.7])
                with h1: st.markdown("**Field Name**")
                with h2: st.markdown("**Source Doc**")
                with h3: st.markdown("**Keyword**")
                with h4: st.markdown("**Cell**")
                with h5: st.markdown("**🤖 AI Prompt**")
                with h6: st.markdown("**Result Example**")
                with h7: st.markdown("**Del**")
                with h8: st.markdown("**Test**")

            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.5, 1.2, 1.5, 0.8, 1.8, 1.5, 0.4, 0.7])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: final_logic = st.selectbox(f"logic_{field}", doc_source_options, index=doc_source_options.index(s_val.get("logic", doc_source_options[0])) if s_val.get("logic") in doc_source_options else 0, label_visibility="collapsed") 
                with c3: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                with c5: ai_p = st.text_input(f"ai_{field}", value=s_val.get("ai_prompt", ""), placeholder="उदा: कीवर्ड के आगे", label_visibility="collapsed")
                with c6: res_ex = st.text_input(f"ex_{field}", value=s_val.get("result_example", ""), placeholder="उदा: ICD TUMB", label_visibility="collapsed")
                
                with c7:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del shipper_info["mapping_rules"][field]
                        save_local_shippers()
                        st.rerun()
                with c8:
                    if st.button("⚡ Test", key=f"test_btn_{field}"):
                        curr_pdf_text = st.session_state.get("cached_pdf_text", "")
                        if not curr_pdf_text:
                            st.toast("⚠️ पहले ऊपर PDF अपलोड करें!")
                        else:
                            with st.spinner("Gemini AI डेटा ढूँढ रहा है..."):
                                header_test_prompt = [
                                    {"role": "system", "content": "You are an expert Indian Customs invoice data extraction AI. Extract the exact requested value based on the user's keyword, prompt instruction, and Result Example. Return ONLY the extracted value without any extra words."},
                                    {"role": "user", "content": f"""
                                    Invoice Text:
                                    {curr_pdf_text[:4000]}
                                    
                                    Field Name: '{edited_name}'
                                    Keyword: '{ky}'
                                    Prompt: '{ai_p}'
                                    Result Example expected: '{res_ex}'
                                    
                                    Task: Find the value near the keyword matching the example. Return ONLY the value.
                                    """}
                                ]
                                res_val = ask_local_ai(header_test_prompt)
                                show_field_test_dialog(edited_name, {"logic": final_logic, "keyword": ky, "cell": cl, "ai_prompt": ai_p, "result_example": res_ex}, res_val if res_val else "❌ (Not Found)", selected_shipper, field)
                
                updated_rules[edited_name] = {
                    "logic": final_logic, "keyword": ky, "cell": cl, "ai_prompt": ai_p, "result_example": res_ex
                }
            shipper_info["mapping_rules"] = updated_rules

            st.write("---")
            if st.button("💾 Save Rules Locally & Sync to Sheet", type="primary", use_container_width=True):
                save_local_shippers()
                st.success("🎉 सारे रूल्स सफलतापूर्वक सेव और सिंक हो गए हैं!")
