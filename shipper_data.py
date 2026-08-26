import streamlit as st
import os
import json
import pdfplumber
import io
from io import BytesIO
import re

from pdf_engine import detect_igst_status, extract_header_value
from google_sheet_sync import (
    fetch_all_from_sheet, push_rules_to_sheet, push_template_file_to_sheet, 
    load_template_bytes_from_sheet
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
    new_field = st.text_input("Field Name (उदा: Invoice No, Amount):")
    doc_source = st.selectbox(
        "यह डॉक्यूमेंट सोर्स चुनें:",
        ["Main Invoice", "GST Invoice (PDF/Excel)", "DEEC Declaration (PDF/Excel)"]
    )
    if st.button("Confirm & Add Field", type="primary"):
        if not new_field.strip():
            st.error("फ़ील्ड नाम खाली नहीं हो सकता!")
        else:
            rules = st.session_state["shipper_database"][selected_shipper].setdefault("mapping_rules", {})
            rules[new_field.strip()] = {
                "logic": doc_source, 
                "keyword": "", 
                "position": "Right (आगे का शब्द)", 
                "cell": "", 
                "match_mode": "Exact Word", 
                "stop_kw": "", 
                "filter": "None", 
                "fallback": "", 
                "result_example": ""
            }
            save_local_shippers()
            st.success(f"🎉 फ़ील्ड '{new_field}' सफलतापूर्वक जोड़ दिया गया है!")
            st.rerun()

@st.dialog("➕ Add New Table Column Rule")
def add_custom_table_column_dialog(selected_shipper):
    st.write("यहाँ नया आइटम टेबल कॉलम जोड़ें:")
    col_name = st.text_input("Item Field Name (उदा: Description, HSN Code, Qty):")
    target_excel_col = st.text_input("Excel Column (उदा: C, F, H):", value="K")
    source_type_opts = [
        "PDF Row Item", 
        "Extract After Keyword (MID/SEARCH)", 
        "Extract Between Two Words", 
        "Header Field Mapping", 
        "Constant Text",
        "DEEC Declaration (PDF/Excel)", 
        "GST Invoice (PDF/Excel)"
    ]
    sel_source_type = st.selectbox("Source Type / Mode:", source_type_opts)
    
    if st.button("Confirm & Add Column", type="primary"):
        if not col_name.strip():
            st.error("कॉलम नाम खाली नहीं हो सकता!")
        else:
            item_rules = st.session_state["shipper_database"][selected_shipper].setdefault("item_table_rules", {})
            item_rules[col_name.strip()] = {
                "col": target_excel_col.strip().upper(),
                "type": sel_source_type,
                "rule": "",
                "result_example": ""
            }
            save_local_shippers()
            st.success(f"🎉 कॉलम '{col_name}' सफलतापर्वक जोड़ दिया गया है!")
            st.rerun()

def render_shipper_data():
    load_local_shippers()
    
    st.header("🏢 Shipper Rules & Advanced Extraction Manager")
    st.caption("मास्टर टेस्ट बटन और नीचे आने वाले प्रैक्टिकल टेस्ट रिजल्ट्स के साथ अपडेटेड मैनेजर।")
    
    shippers_list = sorted(list(st.session_state["shipper_database"].keys()))
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=None, placeholder="शिपर चुनें...")
        if selected_shipper:
            st.write(f"### ⚙️ शिपर प्रोफाइल: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]

            # 📁 1. टेम्पलेट फ़ाइल अपलोड
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

            # 🧪 2. PDF Upload & Text Inspector
            st.write("---")
            st.subheader("🧪 2. Sample PDF Upload & Text Viewer")
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
                st.success(f"📄 PDF लोड हो गई है ({len(pdf_lines)} पंक्तियाँ)।")

            curr_pdf_text = st.session_state.get("cached_pdf_text", "")
            curr_pdf_lines = st.session_state.get("cached_pdf_lines", [])
            if curr_pdf_text:
                with st.expander("👁️ View PDF Raw Text (यहाँ से वैल्यू देखें)", expanded=False):
                    st.text_area("PDF Raw Text:", value=curr_pdf_text[:4000], height=180, key=f"raw_txt_{selected_shipper}")

            # 🛠️ 3. Header Fields Mapping Table
            st.write("---")
            c_title, c_add_h = st.columns([7, 3])
            with c_title:
                st.subheader("🛠️ 3. Header Fields Mapping & Smart Modes")
            with c_add_h:
                if st.button("➕ Add Header Field", type="secondary", use_container_width=True):
                    add_custom_header_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            doc_source_options = ["Main Invoice", "GST Invoice (PDF/Excel)", "DEEC Declaration (PDF/Excel)"]
            position_options = ["Right (आगे का शब्द)", "Below (नीचे की लाइन)", "📦 Extract Inside Box (डब्बा)"]
            match_mode_options = ["Exact Word", "Word Position", "Full Line", "After Word", "Between Keywords", "Table Row Match"]
            filter_options = ["None", "Text Inside", "Numbers Only", "Letters Only", "Container", "Clean Date", "Exact Keyword", "Remove All"]

            if current_rules:
                h1, h2, h3, h4, h5, h6, h7, h8, h9, h10 = st.columns([1.2, 1.2, 1.0, 0.6, 1.1, 1.0, 1.0, 1.0, 0.4, 0.6])
                with h1: st.markdown("**Field**")
                with h2: st.markdown("**Keyword**")
                with h3: st.markdown("**Position**")
                with h4: st.markdown("**Cell**")
                with h5: st.markdown("**Match Mode**")
                with h6: st.markdown("**Filter**")
                with h7: st.markdown("**Source**")
                with h8: st.markdown("**Fallback**")
                with h9: st.markdown("**Del**")
                with h10: st.markdown("**Test**")

            # सिंगल रो टेस्ट रिजल्ट स्टोर करने के लिए स्टेट की
            if f"test_results_{selected_shipper}" not in st.session_state:
                st.session_state[f"test_results_{selected_shipper}"] = {}

            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([1.2, 1.2, 1.0, 0.6, 1.1, 1.0, 1.0, 1.0, 0.4, 0.6])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                
                saved_pos = s_val.get("position", position_options[0])
                if saved_pos not in position_options: saved_pos = position_options[0]
                with c3: pos = st.selectbox(f"pos_{field}", position_options, index=position_options.index(saved_pos), label_visibility="collapsed")
                
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                
                saved_mode = s_val.get("match_mode", match_mode_options[0])
                if saved_mode not in match_mode_options: saved_mode = match_mode_options[0]
                with c5: mode = st.selectbox(f"mode_{field}", match_mode_options, index=match_mode_options.index(saved_mode), label_visibility="collapsed")
                
                saved_flt = s_val.get("filter", filter_options[0])
                if saved_flt not in filter_options: saved_flt = filter_options[0]
                with c6: flt = st.selectbox(f"flt_{field}", filter_options, index=filter_options.index(saved_flt), label_visibility="collapsed")
                
                saved_logic = s_val.get("logic", doc_source_options[0])
                if saved_logic not in doc_source_options: saved_logic = doc_source_options[0]
                with c7: logic = st.selectbox(f"logic_{field}", doc_source_options, index=doc_source_options.index(saved_logic), label_visibility="collapsed")
                
                with c8: fallback = st.text_input(f"fb_{field}", value=s_val.get("fallback", ""), placeholder="अगर ब्लैंक हो", label_visibility="collapsed")
                
                with c9:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del shipper_info["mapping_rules"][field]
                        save_local_shippers()
                        st.rerun()
                
                with c10:
                    if st.button("⚡ Test", key=f"test_h_{field}"):
                        if not curr_pdf_text:
                            st.error("कृपया ऊपर पहले सैंपल PDF अपलोड करें!")
                        else:
                            pdf_b_cache = st.session_state.get("cached_pdf_bytes", None)
                            res = extract_header_value(
                                curr_pdf_lines, curr_pdf_text, ky, pos, mode, "", flt, field_label=edited_name, pdf_bytes=pdf_b_cache
                            )
                            st.session_state[f"test_results_{selected_shipper}"][edited_name] = res

                updated_rules[edited_name] = {
                    "logic": logic, 
                    "keyword": ky, 
                    "position": pos,
                    "cell": cl, 
                    "match_mode": mode,
                    "stop_kw": s_val.get("stop_kw", ""),
                    "filter": flt,
                    "fallback": fallback,
                    "result_example": s_val.get("result_example", "")
                }
            shipper_info["mapping_rules"] = updated_rules

            # 🚀 MASTER TEST BUTTON FOR ALL HEADER FIELDS (नीचे साफ-सुथरा परिणाम दिखाने के लिए)
            st.write("##")
            master_col1, master_col2 = st.columns([2, 4])
            with master_col1:
                if st.button("🚀 Run Master Test (Check All Headers)", type="primary", use_container_width=True):
                    if not curr_pdf_text:
                        st.error("कृपया पहले सैंपल PDF अपलोड करें!")
                    else:
                        pdf_b_cache = st.session_state.get("cached_pdf_bytes", None)
                        batch_res = {}
                        for f_name, f_rule in shipper_info.get("mapping_rules", {}).items():
                            val = extract_header_value(
                                curr_pdf_lines, curr_pdf_text, 
                                f_rule.get("keyword", ""), 
                                f_rule.get("position", ""), 
                                f_rule.get("match_mode", ""), 
                                "", 
                                f_rule.get("filter", ""), 
                                field_label=f_name, 
                                pdf_bytes=pdf_b_cache
                            )
                            batch_res[f_name] = val
                        st.session_state[f"master_test_res_{selected_shipper}"] = batch_res

            # यदि कोई मास्टर टेस्ट या सिंगल टेस्ट रिजल्ट मौजूद है, तो उसे नीचे एक बड़े और स्पष्ट बॉक्स में दिखाएं
            if f"master_test_res_{selected_shipper}" in st.session_state and st.session_state[f"master_test_res_{selected_shipper}"]:
                st.info("📋 **Master Test Results (सभी हेडर फील्ड्स का रिजल्ट):**")
                st.json(st.session_state[f"master_test_res_{selected_shipper}"])

            # व्यक्तिगत टेस्ट रिजल्ट्स को रो के नीचे साफ़ दिखाने के लिए
            test_res_dict = st.session_state.get(f"test_results_{selected_shipper}", {})
            if test_res_dict:
                with st.expander("🔍 View Individual Test Field Results (हाल के टेस्ट रिजल्ट्स)", expanded=True):
                    for k, v in test_res_dict.items():
                        st.markdown(f"• **{k}** 👉 `value: {v}`")

            # 🛠️ 4. Dynamic Item Table Rules & Mapping Table
            st.write("---")
            c_it_title, c_it_add = st.columns([7, 3])
            with c_it_title:
                st.subheader("📋 4. Dynamic Item Table Rules & Mapping")
            with c_it_add:
                if st.button("➕ Add Table Column", type="secondary", use_container_width=True):
                    add_custom_table_column_dialog(selected_shipper)
            
            current_parser_name = shipper_info.get("item_table_rule_name", "parser_welspun")
            parser_options = ["parser_welspun", "parser_polycab", "parser_bkt", "parser_vapi_welspun"]
            selected_parser = st.selectbox(
                "इस शिपर के लिए मुख्य आइटम पार्सर चुनें:", 
                parser_options, 
                index=parser_options.index(current_parser_name) if current_parser_name in parser_options else 0,
                key=f"parser_sel_{selected_shipper}"
            )
            shipper_info["item_table_rule_name"] = selected_parser

            item_rules = shipper_info.setdefault("item_table_rules", {})
            updated_item_rules = {}
            
            if item_rules:
                it_c1, it_c2, it_c3, it_c4, it_c5, it_c6 = st.columns([1.5, 0.8, 1.8, 2.0, 1.5, 0.5])
                with it_c1: st.markdown("**Item Field Name**")
                with it_c2: st.markdown("**Excel Col**")
                with it_c3: st.markdown("**Source Type / Mode**")
                with it_c4: st.markdown("**Rule / Keyword / Formula Hint**")
                with it_c5: st.markdown("**Result Example**")
                with it_c6: st.markdown("**Del**")

            source_type_opts = [
                "PDF Row Item", 
                "Extract After Keyword (MID/SEARCH)", 
                "Extract Between Two Words", 
                "Header Field Mapping", 
                "Constant Text",
                "DEEC Declaration (PDF/Excel)", 
                "GST Invoice (PDF/Excel)"
            ]

            for it_field, it_val in list(item_rules.items()):
                ic1, ic2, ic3, ic4, ic5, ic6 = st.columns([1.5, 0.8, 1.8, 2.0, 1.5, 0.5])
                
                with ic1: edited_it_name = st.text_input(f"it_name_{it_field}", value=it_field, label_visibility="collapsed")
                with ic2: it_col = st.text_input(f"it_col_{it_field}", value=it_val.get("col", "K"), label_visibility="collapsed")
                
                saved_type = it_val.get("type", "PDF Row Item")
                if saved_type not in source_type_opts: saved_type = source_type_opts[0]
                with ic3: it_type = st.selectbox(f"it_type_{it_field}", source_type_opts, index=source_type_opts.index(saved_type), label_visibility="collapsed")
                
                with ic4: it_rule = st.text_input(f"it_rule_{it_field}", value=it_val.get("rule", ""), placeholder="कीवर्ड या सर्च स्ट्रिंग", label_visibility="collapsed")
                with ic5: it_ex = st.text_input(f"it_ex_{it_field}", value=it_val.get("result_example", ""), placeholder="उदा: 8544...", label_visibility="collapsed")
                
                with ic6:
                    if st.button("🗑️", key=f"del_it_{it_field}"):
                        del shipper_info["item_table_rules"][it_field]
                        save_local_shippers()
                        st.rerun()
                
                updated_item_rules[edited_it_name] = {
                    "col": it_col.upper(),
                    "type": it_type,
                    "rule": it_rule,
                    "result_example": it_ex
                }
            shipper_info["item_table_rules"] = updated_item_rules

            # 🛠️ 5. IGST & Lut Configuration
            st.write("---")
            st.subheader("⚙️ 5. IGST & Lut Configuration")
            igst_cfg = shipper_info.setdefault("igst_config", {})
            c_igst1, c_igst2 = st.columns(2)
            with c_igst1:
                lut_kws = st.text_input("LUT Keywords (कॉमा से अलग करें):", value=igst_cfg.get("lut_keywords", "LUT, UNDER LUT, UNDER BOND"), key=f"lut_{selected_shipper}")
            with c_igst2:
                paid_kws = st.text_input("Paid Keywords (कॉमा से अलग करें):", value=igst_cfg.get("paid_keywords", "SUPPLY MEANT FOR EXPORT ON PAYMENT OF IGST."), key=f"paid_{selected_shipper}")
            
            igst_cfg["lut_keywords"] = lut_kws
            igst_cfg["paid_keywords"] = paid_kws

            st.write("---")
            if st.button("💾 Save All Rules & Sync to Google Sheet", type="primary", use_container_width=True, key="btn_save_rules_local"):
                save_local_shippers()
                st.success("🎉 आपके सारे रूल्स, मास्टर टेस्ट फीचर्स और मैपिंग गूगल शीट पर सफलतापर्वक सिंक हो गई है!")
