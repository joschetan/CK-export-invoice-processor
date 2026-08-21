import streamlit as st
import os
import json
import pdfplumber
import io
from io import BytesIO

from pdf_engine import detect_igst_status, extract_header_value
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

def load_local_shippers():
    ensure_local_directories()
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
    
    st.header("🏢 Add Shipper Name & Visual No-Code Mapping Builder")
    st.caption("बिना किसी कोडिंग या बार-बार AI के, विजुअल तरीके से पीडीएफ से डेटा कैप्चर करने का स्मार्ट इंजन।")
    
    # शिपर सेलेक्शन
    shippers_list = sorted(list(st.session_state["shipper_database"].keys()))
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None, placeholder="शिपर चुनें...")
        if selected_shipper:
            st.write(f"### ⚙️ शिपर प्रोफाइल: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]

            # 🧪 1. Instant PDF Upload & Visual Text Inspector
            st.write("---")
            st.subheader("🧪 1. Sample PDF Upload & Visual Text Inspector")
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
                st.success(f"📄 PDF सफलतापूर्वक लोड हो गई है ({len(pdf_lines)} पंक्तियाँ)।")

            # 👁️ 2. Visual Text Inspector Box (ताकि आप खुद देखकर तुरंत नियम बना सकें)
            curr_pdf_text = st.session_state.get("cached_pdf_text", "")
            if curr_pdf_text:
                with st.expander("👁️ View Extracted PDF Raw Text (यहाँ से देखकर आसानी से कीवर्ड या वैल्यू चुनें)", expanded=False):
                    st.text_area("PDF Raw Text Content:", value=curr_pdf_text[:4000], height=200, key=f"raw_txt_{selected_shipper}")
                    st.info("💡 टिप: यहाँ से वैल्यू (जैसे इनवॉइस नंबर) को कॉपी करें और नीचे अपने हेडर रूल में सीधे पेस्ट कर दें। इससे आपको कभी कोडिंग या AI की जरूरत नहीं पड़ेगी!")

            # 🛠️ 3. Header Fields Mapping Rules (Deterministic Regex / Keyword Engine)
            st.write("---")
            c_title, c_add_h = st.columns([7, 3])
            with c_title:
                st.subheader("🛠️ 2. Header Fields Mapping & Regex Rules")
            with c_add_h:
                if st.button("➕ Add Header Field", type="secondary", use_container_width=True):
                    add_custom_header_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            doc_source_options = ["Main Invoice", "GST Invoice (PDF/Excel)", "DEEC Declaration (PDF/Excel)"]
            
            if current_rules:
                h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([1.3, 1.0, 1.2, 0.6, 1.4, 1.2, 1.8, 0.4])
                with h1: st.markdown("**Field Name**")
                with h2: st.markdown("**Source Doc**")
                with h3: st.markdown("**Keyword**")
                with h4: st.markdown("**Cell**")
                with h5: st.markdown("**Prompt**")
                with h6: st.markdown("**Result Ex**")
                with h7: st.markdown("**⚡ Local Python/Regex Logic**")
                with h8: st.markdown("**Del**")

            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.3, 1.0, 1.2, 0.6, 1.4, 1.2, 1.8, 0.4])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: final_logic = st.selectbox(f"logic_{field}", doc_source_options, index=doc_source_options.index(s_val.get("logic", doc_source_options[0])) if s_val.get("logic") in doc_source_options else 0, label_visibility="collapsed") 
                with c3: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                with c5: ai_p = st.text_input(f"ai_{field}", value=s_val.get("ai_prompt", ""), placeholder="उदा: नीचे वाली लाइन", label_visibility="collapsed")
                with c6: res_ex = st.text_input(f"ex_{field}", value=s_val.get("result_example", ""), placeholder="उदा: GJ29XE...", label_visibility="collapsed")
                
                saved_ext_logic = s_val.get("extracted_logic", "")
                # पॉलीकैब या अन्य के लिए डिफ़ॉल्ट मजबूत रेजेक्स जो बिना AI के सीधे काम करेगा
                if not saved_ext_logic and ("inv. no" in field.lower() or "invoice no" in field.lower()):
                    saved_ext_logic = 'import re\nmatch = re.search(r"INVOICE NO\\.\\s*&\\s*DATE[\\s\\S]*?\\n\\s*([A-Z0-9]{10,20})", text)\nvalue = match.group(1) if match else None'

                with c7: ext_logic = st.text_input(f"elogic_{field}", value=saved_ext_logic, placeholder="re.search(...) लॉजिक यहाँ लिखें", label_visibility="collapsed")
                
                with c8:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del shipper_info["mapping_rules"][field]
                        save_local_shippers()
                        st.rerun()
                
                updated_rules[edited_name] = {
                    "logic": final_logic, "keyword": ky, "cell": cl, "ai_prompt": ai_p, "result_example": res_ex, "extracted_logic": ext_logic
                }
            shipper_info["mapping_rules"] = updated_rules

            st.write("---")
            if st.button("💾 Save Rules & Sync to Google Sheet", type="primary", use_container_width=True, key="btn_save_rules_local"):
                save_local_shippers()
                st.success("🎉 आपके रूल्स और लोकल रेजेक्स लॉजिक सफलतापूर्वक गूगल शीट पर सेव हो गए हैं! अब इनवॉइस प्रोसेस करते वक्त कोई API लिमिट नहीं आएगी।")
