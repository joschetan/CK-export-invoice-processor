import streamlit as st
import os
import json
import pdfplumber
import io
from io import BytesIO
import re

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
    
    st.header("🏢 Add Shipper Name & No-Code Visual Mapping Builder")
    st.caption("कीवर्ड, पोजीशन (आगे/नीचे) और वर्ड इंडेक्स के जरिए स्मार्ट टेस्ट और सेव टूल।")
    
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
            if curr_pdf_text:
                with st.expander("👁️ View PDF Raw Text (यहाँ से वैल्यू देखें)", expanded=False):
                    st.text_area("PDF Raw Text:", value=curr_pdf_text[:4000], height=180, key=f"raw_txt_{selected_shipper}")

            # ⚡ 3. Smart Test & Save Generator Box (आगे या नीचे विकल्प के साथ)
            st.write("---")
            st.subheader("⚡ 3. Smart Test & Save Generator")
            st.caption("कीवर्ड, दिशा (आगे/नीचे) और वर्ड इंडेक्स सेट करके पहले टेस्ट करें, फिर सेव करें:")
            
            gen_col1, gen_col2, gen_col3, gen_col4 = st.columns([1.5, 1.5, 1.0, 1.0])
            with gen_col1:
                target_val_input = st.text_input("1. टारगेट वैल्यू:", key=f"t_val_{selected_shipper}")
            with gen_col2:
                keyword_input = st.text_input("2. मुख्य कीवर्ड:", key=f"t_kw_{selected_shipper}")
            with gen_col3:
                pos_direction = st.selectbox("3. दिशा:", ["Right (आगे)", "Below (नीचे)"], key=f"t_dir_{selected_shipper}")
            with gen_col4:
                word_offset = st.number_input("4. Word Index:", min_value=1, max_value=20, value=1, key=f"t_off_{selected_shipper}")
            
            test_state_key = f"tested_code_{selected_shipper}"
            
            # टेस्ट बटन
            if st.button("🧪 Test Extraction First", type="secondary", key=f"btn_test_{selected_shipper}"):
                if not keyword_input.strip():
                    st.error("कृपया कीवर्ड दर्ज करें!")
                else:
                    escaped_kw = re.escape(keyword_input.strip())
                    if "Below" in pos_direction:
                        # यदि कीवर्ड के नीचे वाली लाइन से वैल्यू निकालनी हो
                        generated_code = (
                            f'import re\n'
                            f'lines = text.split("\\n")\n'
                            f'found_line = ""\n'
                            f'for idx, l in enumerate(lines):\n'
                            f'    if re.search(r"{escaped_kw}", l, re.IGNORECASE):\n'
                            f'        if idx + 1 < len(lines):\n'
                            f'            found_line = lines[idx + 1].strip()\n'
                            f'            break\n'
                            f'words = found_line.split()\n'
                            f'value = words[{word_offset - 1}] if len(words) >= {word_offset} else (found_line if found_line else None)'
                        )
                    else:
                        # यदि कीवर्ड के आगे (Right) से निकालनी हो
                        generated_code = (
                            f'import re\n'
                            f'text_clean = re.sub(r"\\s+", " ", text)\n'
                            f'pattern = r"{escaped_kw}(?:[^A-Za-z0-9]+[A-Za-z0-9]+){{{word_offset - 1}}}[^A-Za-z0-9]+([0-9A-Z\\-/\\.]{{2,25}})"\n'
                            f'match = re.search(pattern, text_clean)\n'
                            f'value = match.group(1) if match else None'
                        )
                        
                    st.session_state[test_state_key] = generated_code
                    
                    try:
                        local_env = {"text": curr_pdf_text, "re": re}
                        exec(generated_code, {}, local_env)
                        found_res = local_env.get("value", "Not Found")
                        if found_res and found_res != "None":
                            st.success(f"✅ **Test Result Found:** 👉 **`{found_res}`** (यदि यह सही है, तो नीचे फील्ड चुनकर 'Confirm & Save' दबाएं)")
                        else:
                            st.warning("⚠️ इस कीवर्ड और पोजीशन पर वैल्यू नहीं मिली। कृपया इंडेक्स या कीवर्ड बदल कर दोबारा टेस्ट करें।")
                    except Exception as ex:
                        st.error(f"Test Error: {str(ex)}")

            # 4. फील्ड सेलेक्शन और सेव बटन
            mapping_keys = list(shipper_info.get("mapping_rules", {}).keys())
            target_field_to_update = st.selectbox("5. यह लॉजिक किस हेडर फील्ड (Field Name) पर सेव करना है?", mapping_keys if mapping_keys else ["Inv. No."], key=f"target_f_{selected_shipper}")
                
            if st.button("💾 Confirm & Save to Shipper Rule", type="primary", use_container_width=True, key=f"btn_save_tested_{selected_shipper}"):
                if test_state_key in st.session_state and st.session_state[test_state_key]:
                    final_code_to_save = st.session_state[test_state_key]
                    shipper_info["mapping_rules"][target_field_to_update]["extracted_logic"] = final_code_to_save
                    shipper_info["mapping_rules"][target_field_to_update]["result_example"] = target_val_input.strip()
                    shipper_info["mapping_rules"][target_field_to_update]["keyword"] = keyword_input.strip()
                    shipper_info["mapping_rules"][target_field_to_update]["position"] = pos_direction
                    
                    save_local_shippers()
                    st.success(f"🎉 सफलता! '{target_field_to_update}' के लिए रूल गूगल शीट पर परमानेंट सेव हो गया है!")
                else:
                    st.warning("⚠️ कृपया पहले ऊपर 'Test Extraction First' बटन दबाकर रिजल्ट वैलिडेट करें!")

            # 🛠️ 4. Header Fields Mapping Rules Table
            st.write("---")
            c_title, c_add_h = st.columns([7, 3])
            with c_title:
                st.subheader("🛠️ 4. Header Fields Mapping & Regex Rules")
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
                with c6: res_ex = st.text_input(f"ex_{field}", value=s_val.get("result_example", ""), placeholder="उदा: 02-07-2026", label_visibility="collapsed")
                
                saved_ext_logic = s_val.get("extracted_logic", "")
                with c7: ext_logic = st.text_input(f"elogic_{field}", value=saved_ext_logic, placeholder="यहाँ लॉजिक सेव है", label_visibility="collapsed")
                
                with c8:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del shipper_info["mapping_rules"][field]
                        save_local_shippers()
                        st.rerun()
                
                updated_rules[edited_name] = {
                    "logic": final_logic, "keyword": ky, "cell": cl, "ai_prompt": ai_p, "result_example": res_ex, "extracted_logic": ext_logic
                }
            shipper_info["mapping_rules"] = updated_rules

            # 🛠️ 5. Dynamic Item Table Rules & Mapping Table
            st.write("---")
            st.subheader("📋 5. Dynamic Item Table Rules & Mapping")
            
            current_parser_name = shipper_info.get("item_table_rule_name", "parser_welspun")
            parser_options = ["parser_welspun", "parser_polycab", "parser_bkt", "parser_vapi_welspun"]
            selected_parser = st.selectbox(
                "इस शिपर के लिए आइटम पार्सर चुनें:", 
                parser_options, 
                index=parser_options.index(current_parser_name) if current_parser_name in parser_options else 0,
                key=f"parser_sel_{selected_shipper}"
            )
            shipper_info["item_table_rule_name"] = selected_parser

            item_rules = shipper_info.setdefault("item_table_rules", {})
            updated_item_rules = {}
            
            if item_rules:
                it_c1, it_c2, it_c3, it_c4, it_c5, it_c6 = st.columns([1.5, 0.8, 1.5, 1.8, 1.8, 0.5])
                with it_c1: st.markdown("**Item Field Name**")
                with it_c2: st.markdown("**Excel Col**")
                with it_c3: st.markdown("**Source Type**")
                with it_c4: st.markdown("**Extraction Rule / Keyword**")
                with it_c5: st.markdown("**Result Example**")
                with it_c6: st.markdown("**Del**")

            source_type_opts = ["PDF Row Item", "Header Field Mapping", "Constant Text", "DEEC Declaration (PDF/Excel)", "GST Invoice (PDF/Excel)"]

            for it_field, it_val in list(item_rules.items()):
                ic1, ic2, ic3, ic4, ic5, ic6 = st.columns([1.5, 0.8, 1.5, 1.8, 1.8, 0.5])
                
                with ic1: edited_it_name = st.text_input(f"it_name_{it_field}", value=it_field, label_visibility="collapsed")
                with ic2: it_col = st.text_input(f"it_col_{it_field}", value=it_val.get("col", "K"), label_visibility="collapsed")
                
                saved_type = it_val.get("type", "PDF Row Item")
                if saved_type not in source_type_opts: saved_type = source_type_opts[0]
                with ic3: it_type = st.selectbox(f"it_type_{it_field}", source_type_opts, index=source_type_opts.index(saved_type), label_visibility="collapsed")
                
                with ic4: it_rule = st.text_input(f"it_rule_{it_field}", value=it_val.get("rule", ""), placeholder="उदा: HSN / Description", label_visibility="collapsed")
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

            # 🛠️ 6. IGST & Lut Configuration
            st.write("---")
            st.subheader("⚙️ 6. IGST & Lut Configuration")
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
                st.success("🎉 आपके सारे रूल्स, डाइनैमिक आइटम टेबल मैपिंग और IGST कॉन्फ़िगरेशन सफलतापूर्वक गूगल शीट पर सिंक हो गए हैं!")
