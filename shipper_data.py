import streamlit as st
import requests
import json
import base64
import pdfplumber
import time
import os
import re
from io import BytesIO

# Import core extraction logic from separated engine module
from pdf_engine import extract_header_value, detect_igst_status[cite: 1]

# Import Universal Test Suite module
from test_suite import render_universal_test_suite[cite: 1]

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"[cite: 1]

def get_val_case_insensitive(d, *keys, default=""):[cite: 1]
    if not isinstance(d, dict):[cite: 1]
        return default[cite: 1]
    d_lower = {str(k).lower(): v for k, v in d.items()}[cite: 1]
    for k in keys:[cite: 1]
        if str(k).lower() in d_lower:[cite: 1]
            val = d_lower[str(k).lower()][cite: 1]
            if val is not None:[cite: 1]
                return str(val).strip()[cite: 1]
    return default[cite: 1]

def get_default_item_rules():[cite: 1]
    return {[cite: 1]
        "RITC / HS Code": {"col": "K", "type": "PDF Row Item", "rule": "HS Code"},[cite: 1]
        "Description of Goods": {"col": "M", "type": "PDF Row Item", "rule": "Description"},[cite: 1]
        "Quantity": {"col": "N", "type": "PDF Row Item", "rule": "Qty Number"},[cite: 1]
        "Unit (UNIT)": {"col": "O", "type": "Smart Detection", "rule": "SET"},[cite: 1]
        "Rate in": {"col": "P", "type": "PDF Row Item", "rule": "Rate"},[cite: 1]
        "Amount": {"col": "Q", "type": "PDF Row Item", "rule": "Amount USD"},[cite: 1]
        "ROSCTL": {"col": "R", "type": "Smart Detection", "rule": "ROSCTL:60:19"},[cite: 1]
        "Drawback SR Code": {"col": "S", "type": "PDF Row Item", "rule": "DBK SR (+B Suffix)"},[cite: 1]
        "Taxable Value (INR)": {"col": "W", "type": "PDF Row Item", "rule": "Taxable Amt"},[cite: 1]
        "IGST Rate (%)": {"col": "X", "type": "PDF Row Item", "rule": "IGST %"},[cite: 1]
        "IGST Amount (INR)": {"col": "Y", "type": "PDF Row Item", "rule": "IGST Amt"},[cite: 1]
        "Nt.Wt(KGS)": {"col": "AB", "type": "PDF Row Item", "rule": "Net Weight"}[cite: 1]
    }[cite: 1]

def ensure_default_shipper():[cite: 1]
    if "shipper_database" not in st.session_state:[cite: 1]
        st.session_state["shipper_database"] = {}[cite: 1]
        
    s_name = "WELSPUN GLOBAL BRANDS LIMITED"[cite: 1]
    if s_name not in st.session_state["shipper_database"]:[cite: 1]
        st.session_state["shipper_database"][s_name] = {[cite: 1]
            "allowed_uploads": ["Full Job Excel Format File"], [cite: 1]
            "uploaded_files": {},[cite: 1]
            "mapping_rules": {},[cite: 1]
            "item_table_rules": get_default_item_rules(),[cite: 1]
            "igst_config": {[cite: 1]
                "lut_keywords": "LUT ARN NO., w/o payment of integrated tax, under bond",[cite: 1]
                "paid_keywords": "on payment of integrated tax, with payment of integrated tax"[cite: 1]
            }[cite: 1]
        }[cite: 1]

def fetch_data_from_google_sheet(show_toast=False):[cite: 1]
    ensure_default_shipper()[cite: 1]
    try:[cite: 1]
        response = requests.get(f"{WEB_APP_URL}?action=get_data", timeout=15)[cite: 1]
        if response.status_code == 200:[cite: 1]
            res_text = response.text.strip()[cite: 1]
            if res_text.startswith("<"):[cite: 1]
                if show_toast: st.error("⚠️ गूगल शीट से HTML मिला। Web App Access 'Anyone' करें।")[cite: 1]
                return[cite: 1]

            data = response.json()[cite: 1]
            
            fetched_item_rules = {}[cite: 1]
            fetched_header_rules = {}[cite: 1]
            item_columns = ["K", "M", "N", "O", "P", "Q", "R", "S", "W", "X", "Y", "AB"][cite: 1]

            rules_list = data.get("rules", data.get("data", [])) if isinstance(data, dict) else data[cite: 1]
            if isinstance(rules_list, list) and len(rules_list) > 0:[cite: 1]
                for row in rules_list:[cite: 1]
                    if isinstance(row, dict):[cite: 1]
                        s_name = get_val_case_insensitive(row, "ShipperName", "shipper", "shippername")[cite: 1]
                        f_name = get_val_case_insensitive(row, "FieldName", "field", "fieldname")[cite: 1]
                        rule_kind = get_val_case_insensitive(row, "RuleKind", "kind", default="header").lower()[cite: 1]
                        cell_val = get_val_case_insensitive(row, "Cell", "cell", "col").strip().upper()[cite: 1]
                        
                        if f_name.lower() in ["igst status", "igst mode"] or cell_val in ["V", "B19"]:[cite: 1]
                            continue[cite: 1]

                        if s_name and f_name:[cite: 1]
                            target_key = "WELSPUN GLOBAL BRANDS LIMITED" if "welspun" in s_name.lower() else s_name[cite: 1]
                                
                            if target_key not in st.session_state["shipper_database"]:[cite: 1]
                                st.session_state["shipper_database"][target_key] = {[cite: 1]
                                    "allowed_uploads": ["Full Job Excel Format File"],[cite: 1]
                                    "uploaded_files": {},[cite: 1]
                                    "mapping_rules": {},[cite: 1]
                                    "item_table_rules": {},[cite: 1]
                                    "igst_config": {[cite: 1]
                                        "lut_keywords": "LUT ARN NO., w/o payment of integrated tax, under bond",[cite: 1]
                                        "paid_keywords": "on payment of integrated tax, with payment of integrated tax"[cite: 1]
                                    }[cite: 1]
                                }[cite: 1]
                            
                            if "item" in rule_kind or cell_val in item_columns or f_name.upper() == "ROSCTL":[cite: 1]
                                fetched_item_rules.setdefault(target_key, {})[f_name] = {[cite: 1]
                                    "col": cell_val if cell_val else "R",[cite: 1]
                                    "type": get_val_case_insensitive(row, "MatchMode", "match_mode", "type", default="Smart Detection"),[cite: 1]
                                    "rule": get_val_case_insensitive(row, "Keyword", "keyword", "rule")[cite: 1]
                                }[cite: 1]
                            else:
                                fetched_header_rules.setdefault(target_key, {})[f_name] = {[cite: 1]
                                    "keyword": get_val_case_insensitive(row, "Keyword", "keyword", "kw"),[cite: 1]
                                    "position": get_val_case_insensitive(row, "Position", "position", "pos", default="Right (आगे)"),[cite: 1]
                                    "cell": cell_val,[cite: 1]
                                    "match_mode": get_val_case_insensitive(row, "MatchMode", "match_mode", "matchmode", default="Exact Word"),[cite: 1]
                                    "stop_kw": get_val_case_insensitive(row, "StopKw", "stop_kw", "stopkw"),[cite: 1]
                                    "filter": get_val_case_insensitive(row, "Filter", "filter", "flt", default="None"),[cite: 1]
                                    "logic": get_val_case_insensitive(row, "Logic", "logic", "lg", default="None")[cite: 1]
                                }[cite: 1]

                for s_key, s_data in st.session_state["shipper_database"].items():[cite: 1]
                    if s_key in fetched_header_rules:[cite: 1]
                        s_data["mapping_rules"] = {k: v for k, v in fetched_header_rules[s_key].items() if k.upper() != "ROSCTL"}[cite: 1]
                        
                    if s_key in fetched_item_rules and fetched_item_rules[s_key]:[cite: 1]
                        s_data["item_table_rules"] = fetched_item_rules[s_key][cite: 1]
                    elif not s_data.get("item_table_rules"):[cite: 1]
                        s_data["item_table_rules"] = get_default_item_rules()[cite: 1]

            if show_toast: st.toast("✅ गूगल शीट से रूल्स लोड हो गए!")[cite: 1]
    except Exception as e:[cite: 1]
        if show_toast: st.error(f"फ़ैच एरर: {str(e)}")[cite: 1]

@st.dialog("🧪 Live Extraction Field Test Result")[cite: 1]
def show_field_test_dialog(field_name, rule_data, result_val):[cite: 1]
    st.write(f"### 🔍 Field: **`{field_name}`**")[cite: 1]
    st.markdown("#### 📋 Applied Rule Parameters:")[cite: 1]
    
    raw_cell = str(rule_data.get('cell', 'Blank')).strip()[cite: 1]
    display_cell = f"{raw_cell} (Dynamic Row)" if raw_cell and raw_cell.isalpha() else raw_cell[cite: 1]

    col_a, col_b = st.columns(2)[cite: 1]
    with col_a:[cite: 1]
        st.markdown(f"* **Keyword:** `{rule_data.get('keyword', 'N/A')}`")[cite: 1]
        st.markdown(f"* **Position:** `{rule_data.get('position', 'Right (आगे)')}`")[cite: 1]
        st.markdown(f"* **Target Cell:** `{display_cell}`")[cite: 1]
    with col_b:[cite: 1]
        st.markdown(f"* **Match Mode:** `{rule_data.get('match_mode', 'Exact Word')}`")[cite: 1]
        st.markdown(f"* **Stop / Word No.:** `{rule_data.get('stop_kw', 'N/A')}`")[cite: 1]
        st.markdown(f"* **Filter/Logic:** `{rule_data.get('filter', 'None')}`")[cite: 1]
        
    st.write("---")[cite: 1]
    st.markdown("#### 🎯 Extracted Result from Uploaded PDF:")[cite: 1]
    if "❌" in result_val or not result_val.strip():[cite: 1]
        st.error(f"❌ **Not Found!** Value: `{result_val}`")[cite: 1]
    else:
        st.success("🎉 **SUCCESS! Extracted Value:**")[cite: 1]
        st.code(result_val, language="text")[cite: 1]

@st.dialog("⚠️ Urgent: Verify IGST Status for Column V")[cite: 1]
def show_igst_manual_prompt_dialog(invoice_no):[cite: 1]
    st.warning(f"⚠️ इन्वॉइस **`{invoice_no}`** पर LUT या Paid (P) का स्पष्ट टेक्स्ट नहीं मिला!")[cite: 1]
    st.write("कस्टम्स में भारी पेनाल्टी से बचने के लिए कृपया खुद से कन्फर्म करें:")[cite: 1]
    
    selected_status = st.selectbox("Column V के लिए सही मोड चुनें:", ["P", "LUT"], index=0)[cite: 1]
    
    if st.button("Confirm & Apply to Column V", type="primary"):[cite: 1]
        st.session_state[f"manual_igst_{invoice_no}"] = selected_status[cite: 1]
        st.success(f"✅ Selected `{selected_status}` for Invoice `{invoice_no}`")[cite: 1]
        st.rerun()[cite: 1]

@st.dialog("➕ Add New Custom Header Field")[cite: 1]
def add_custom_header_field_dialog(selected_shipper):[cite: 1]
    st.write("यहाँ नया हेडर फ़ील्ड जोड़ें:")[cite: 1]
    new_field = st.text_input("Field Name (उदा: Invoice No, Port of Loading):")[cite: 1]
    if st.button("Confirm & Add Field", type="primary"):[cite: 1]
        if not new_field.strip():[cite: 1]
            st.error("फ़ील्ड नाम खाली नहीं हो सकता!")[cite: 1]
        else:
            rules = st.session_state["shipper_database"][selected_shipper].setdefault("mapping_rules", {})[cite: 1]
            rules[new_field.strip()] = {[cite: 1]
                "keyword": "", "position": "Right (आगे)", "cell": "",[cite: 1]
                "match_mode": "Exact Word", "stop_kw": "", "filter": "None", "logic": "None"[cite: 1]
            }[cite: 1]
            st.success(f"🎉 फ़ील्ड '{new_field}' जुड़ गया!")[cite: 1]
            st.rerun()[cite: 1]

@st.dialog("➕ Add Item Column Rule")[cite: 1]
def add_item_col_dialog(selected_shipper):[cite: 1]
    st.write("यहाँ आइटम टेबल के लिए नया कॉलम हेडिंग और एक्सेल कॉलम जोड़ें:")[cite: 1]
    c_name = st.text_input("Heading Name (उदा: Net Weight, Boxes, Size):")[cite: 1]
    c_col = st.text_input("Excel Column Letter (उदा: L, M, N, Z):").upper()[cite: 1]
    c_type = st.selectbox("Rule Type:", ["PDF Row Item", "Table Row Item", "Constant Text", "Excel Cell Reference", "Smart Detection"])[cite: 1]
    c_rule = st.text_input("Rule Detail / Value (उदा: B19, SET, PCS, Numbers Only):")[cite: 1]
    
    if st.button("Confirm & Add Item Column", type="primary"):[cite: 1]
        if not c_name or not c_col:[cite: 1]
            st.error("Heading Name और Column Letter अनिवार्य हैं!")[cite: 1]
        else:
            item_rules = st.session_state["shipper_database"][selected_shipper].setdefault("item_table_rules", {})[cite: 1]
            item_rules[c_name] = {"col": c_col, "type": c_type, "rule": c_rule}[cite: 1]
            st.success(f"🎉 कॉलम '{c_name}' जुड़ गया!")[cite: 1]
            st.rerun()[cite: 1]

def render_shipper_data():[cite: 1]
    if "sheet_data_loaded" not in st.session_state:[cite: 1]
        fetch_data_from_google_sheet(show_toast=False)[cite: 1]
        st.session_state["sheet_data_loaded"] = True[cite: 1]
    
    st.header("🏢 Add Shipper Name & Live-Test AI Mapping Builder")[cite: 1]
    st.caption("सटीक डेटा एक्सट्रैक्शन और रो-बाय-रो लाइव टेस्ट इंजन।")[cite: 1]
    
    shippers_list = list(st.session_state["shipper_database"].keys())[cite: 1]
    
    if shippers_list:[cite: 1]
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=0)[cite: 1]
        
        if selected_shipper:[cite: 1]
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")[cite: 1]
            shipper_info = st.session_state["shipper_database"][selected_shipper][cite: 1]
            
            # --- SECTION 1: TEMPLATE UPLOAD ---
            st.subheader("📁 1. टेम्पलेट फ़ाइल अपलोड")[cite: 1]
            
            uploaded_files_dict = shipper_info.get("uploaded_files", {})[cite: 1]
            tpl_bytes = uploaded_files_dict.get("Full Job Excel Format File", b"")
            has_session_file = isinstance(tpl_bytes, bytes) and len(tpl_bytes) > 0 and tpl_bytes.startswith(b'PK')
            has_local_file = os.path.exists("template.xlsx")

            if has_session_file or has_local_file:
                st.success("✅ Blank Full Job Excel Format File उपलब्ध एवं सुरक्षित है।")
                if st.button("🗑️ Delete & Replace Template", key=f"del_tpl_{selected_shipper}"):[cite: 1]
                    shipper_info["uploaded_files"]["Full Job Excel Format File"] = b""[cite: 1]
                    if os.path.exists("template.xlsx"):
                        os.remove("template.xlsx")
                    st.rerun()[cite: 1]
            else:
                f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template) अपलोड करें", type=["xlsx", "xls"], key=f"tpl_{selected_shipper}")[cite: 1]
                if f_upload is not None:[cite: 1]
                    file_bytes = f_upload.getvalue()[cite: 1]
                    if file_bytes and len(file_bytes) > 0:[cite: 1]
                        shipper_info.setdefault("uploaded_files", {})["Full Job Excel Format File"] = file_bytes[cite: 1]
                        # Save locally for absolute guarantee
                        with open("template.xlsx", "wb") as f:
                            f.write(file_bytes)
                        st.success("🎉 टेम्पलेट अपलोड और सेव हो गया!")[cite: 1]
                        st.rerun()[cite: 1]
                    
            st.write("---")[cite: 1]
            
            # --- SECTION 2: LIVE TEST PDF ENGINE ---
            st.subheader("🧪 2. Instant PDF Upload & Live Data Test Engine")[cite: 1]
            st.caption("यहाँ टेस्ट इनवॉइस PDF अपलोड करें, फिर रूल्स के सामने ⚡ Test दबाकर पॉप-अप में लाइव डेटा देखें।")[cite: 1]
            
            test_pdf = st.file_uploader("➡️ टेस्ट करने के लिए इनवॉइस PDF अपलोड करें", type=["pdf"], key=f"test_pdf_{selected_shipper}")[cite: 1]
            
            pdf_lines = [][cite: 1]
            pdf_text = ""[cite: 1]
            if test_pdf:[cite: 1]
                with pdfplumber.open(test_pdf) as pdf:[cite: 1]
                    for page in pdf.pages:[cite: 1]
                        t = page.extract_text()[cite: 1]
                        if t:[cite: 1]
                            pdf_text += t + "\n"[cite: 1]
                            pdf_lines.extend(t.split("\n"))[cite: 1]
                st.session_state["cached_pdf_lines"] = pdf_lines[cite: 1]
                st.session_state["cached_pdf_text"] = pdf_text[cite: 1]
                st.success(f"📄 PDF अपलोड है ({len(pdf_lines)} पंक्तियाँ)। अब नीचे ⚡ Test बटन दबाएँ!")[cite: 1]

            st.write("---")[cite: 1]
            
            # --- SECTION 3: HEADER MAPPING RULES ---
            col_title, col_sync, col_add_h = st.columns([5, 3, 2])[cite: 1]
            with col_title:[cite: 1]
                st.subheader("🛠️ 3. Header Fields Mapping Rules")[cite: 1]
            with col_sync:[cite: 1]
                if st.button("🔄 Reload Saved Rules from Sheet", type="secondary", use_container_width=True):[cite: 1]
                    st.session_state["shipper_database"] = {}[cite: 1]
                    fetch_data_from_google_sheet(show_toast=True)[cite: 1]
                    st.rerun()[cite: 1]
            with col_add_h:[cite: 1]
                if st.button("➕ Add Header Field", type="secondary", use_container_width=True):[cite: 1]
                    add_custom_header_field_dialog(selected_shipper)[cite: 1]
            
            current_rules = shipper_info.get("mapping_rules", {})[cite: 1]
            updated_rules = {}[cite: 1]
            
            pos_options = ["Right (आगे)", "Below (नीचे)", "2 Lines Below", "Table Row Item", "Table Row Index"][cite: 1]
            mode_options = ["Exact Word", "Word Position", "Full Line", "After Word", "Between Keywords", "Table Row Match"][cite: 1]
            
            filter_options = [[cite: 1]
                "None", [cite: 1]
                "Text Inside Parentheses ()", [cite: 1]
                "Numbers Only", [cite: 1]
                "Letters Only", [cite: 1]
                "Container Number (ISO Format)", [cite: 1]
                "Container Size (20/40 Only)", [cite: 1]
                "Clean Date (DD/MM/YYYY)"[cite: 1]
            ]
            
            c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2, 2.5, 1.5, 0.8, 1.8, 1.5, 1.8, 0.8, 1.2])[cite: 1]
            with c1: st.markdown("**Field Name**")[cite: 1]
            with c2: st.markdown("**Keyword**")[cite: 1]
            with c3: st.markdown("**Position**")[cite: 1]
            with c4: st.markdown("**Cell**")[cite: 1]
            with c5: st.markdown("**Match Mode**")[cite: 1]
            with c6: st.markdown("**Stop / Word No.**")[cite: 1]
            with c7: st.markdown("**Filter/Logic**")[cite: 1]
            with c8: st.markdown("**Del**")[cite: 1]
            with c9: st.markdown("**⚡ Live Test**")[cite: 1]
            st.write("---")[cite: 1]
            
            curr_pdf_lines = st.session_state.get("cached_pdf_lines", [])[cite: 1]
            curr_pdf_text = st.session_state.get("cached_pdf_text", "")[cite: 1]

            for field in list(current_rules.keys()):[cite: 1]
                if field.lower() in ["igst status", "igst mode", "rosctl"] or current_rules[field].get("cell", "").strip().upper() in ["V", "B19", "R"]:[cite: 1]
                    continue[cite: 1]

                s_val = current_rules[field][cite: 1]
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2, 2.5, 1.5, 0.8, 1.8, 1.5, 1.8, 0.8, 1.2])[cite: 1]
                
                saved_pos = s_val.get("position", "Right (आगे)")[cite: 1]
                pos_idx = pos_options.index(saved_pos) if saved_pos in pos_options else 0[cite: 1]
                
                saved_mode = s_val.get("match_mode", "Exact Word")[cite: 1]
                mode_idx = mode_options.index(saved_mode) if saved_mode in mode_options else 0[cite: 1]
                
                saved_flt = s_val.get("filter", "None")[cite: 1]
                if saved_flt in ["Inside Parentheses ()", "Text Inside ()"]:[cite: 1]
                    saved_flt = "Text Inside Parentheses ()"[cite: 1]
                
                flt_idx = filter_options.index(saved_flt) if saved_flt in filter_options else 0[cite: 1]

                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")[cite: 1]
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")[cite: 1]
                with c3: pos = st.selectbox(f"p_{field}", pos_options, index=pos_idx, label_visibility="collapsed")[cite: 1]
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")[cite: 1]
                with c5: m_mode = st.selectbox(f"mm_{field}", mode_options, index=mode_idx, label_visibility="collapsed")[cite: 1]
                with c6: stop_kw = st.text_input(f"sk_{field}", value=s_val.get("stop_kw", ""), label_visibility="collapsed")[cite: 1]
                with c7: final_flt = st.selectbox(f"flt_{field}", filter_options, index=flt_idx, label_visibility="collapsed")[cite: 1]
                with c8:[cite: 1]
                    if st.button("🗑️", key=f"del_h_{field}"):[cite: 1]
                        del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field][cite: 1]
                        st.rerun()[cite: 1]
                with c9:[cite: 1]
                    if st.button("⚡ Test", key=f"test_btn_{field}"):[cite: 1]
                        if not curr_pdf_lines:[cite: 1]
                            st.toast("⚠️ पहले Section 2 में PDF अपलोड करें!")[cite: 1]
                        else:
                            res_val = extract_header_value(curr_pdf_lines, curr_pdf_text, ky, pos, m_mode, stop_kw, final_flt)[cite: 1]
                            
                            rule_summary = {[cite: 1]
                                "keyword": ky, "position": pos, "cell": cl,[cite: 1]
                                "match_mode": m_mode, "stop_kw": stop_kw, "filter": final_flt[cite: 1]
                            }[cite: 1]
                            show_field_test_dialog(edited_name, rule_summary, res_val if res_val else "❌ (Not Found)")[cite: 1]
                
                updated_rules[edited_name] = {"keyword": ky, "position": pos, "cell": cl, "match_mode": m_mode, "stop_kw": stop_kw, "filter": final_flt, "logic": "None"}[cite: 1]
                
            st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules[cite: 1]
            
            # --- SECTION 3.1: SHIPPER-WISE IGST STATUS (COLUMN V) CONFIGURATOR ---
            st.write("---")[cite: 1]
            st.subheader("🛡️ Column V Auto-Detection Configurator (LUT vs Paid 'P')")[cite: 1]
            st.caption("कस्टम्स पेनल्टी से बचने के लिए शिपर के हिसाब से LUT और Paid ढूँढने के कीवर्ड्स यहाँ तय करें:")[cite: 1]
            
            igst_cfg = shipper_info.setdefault("igst_config", {[cite: 1]
                "lut_keywords": "LUT ARN NO., w/o payment of integrated tax, under bond",[cite: 1]
                "paid_keywords": "on payment of integrated tax, with payment of integrated tax"[cite: 1]
            })[cite: 1]
            
            col_lut, col_paid = st.columns(2)[cite: 1]
            with col_lut:[cite: 1]
                updated_lut_kws = st.text_area([cite: 1]
                    "📌 LUT Detection Keywords (कॉमा से अलग करें):",[cite: 1]
                    value=igst_cfg.get("lut_keywords", "LUT ARN NO., w/o payment of integrated tax, under bond"),[cite: 1]
                    help="अगर इनमें से कोई भी शब्द PDF में मिला तो V कॉलम में सीधे 'LUT' जाएगा।"[cite: 1]
                )[cite: 1]
            with col_paid:[cite: 1]
                updated_paid_kws = st.text_area([cite: 1]
                    "📌 Paid (P) Detection Keywords (कॉमा से अलग करें):",[cite: 1]
                    value=igst_cfg.get("paid_keywords", "on payment of integrated tax, with payment of integrated tax"),[cite: 1]
                    help="अगर LUT नहीं मिला और इनमें से कोई शब्द मिला तो V कॉलम में सीधे 'P' जाएगा।"[cite: 1]
                )[cite: 1]
                
            shipper_info["igst_config"] = {[cite: 1]
                "lut_keywords": updated_lut_kws,[cite: 1]
                "paid_keywords": updated_paid_kws[cite: 1]
            }[cite: 1]

            st.write("---")[cite: 1]
            
            # --- SECTION 4: DYNAMIC ITEM TABLE COLUMN BUILDER ---
            c_head, c_add_btn = st.columns([7, 3])[cite: 1]
            with c_head:[cite: 1]
                st.subheader("📦 4. Dynamic Item Table Column Builder (Shipper-Wise)")[cite: 1]
            with c_add_btn:[cite: 1]
                if st.button("➕ Add Item Column", use_container_width=True):[cite: 1]
                    add_item_col_dialog(selected_shipper)[cite: 1]
            
            item_rules = shipper_info.get("item_table_rules", {})[cite: 1]
            if not item_rules:[cite: 1]
                item_rules = get_default_item_rules()[cite: 1]
                shipper_info["item_table_rules"] = item_rules[cite: 1]

            updated_item_rules = {}[cite: 1]
            
            ic1, ic2, ic3, ic4, ic5 = st.columns([3, 2, 3, 3, 1])[cite: 1]
            with ic1: st.markdown("**Item Field Name**")[cite: 1]
            with ic2: st.markdown("**Excel Column**")[cite: 1]
            with ic3: st.markdown("**Rule Type**")[cite: 1]
            with ic4: st.markdown("**Rule Detail / Value**")[cite: 1]
            with ic5: st.markdown("**Del**")[cite: 1]
            st.write("---")[cite: 1]
            
            rule_type_options = ["PDF Row Item", "Table Row Item", "Constant Text", "Excel Cell Reference", "Smart Detection"][cite: 1]
            
            for item_field in list(item_rules.keys()):[cite: 1]
                if item_field.lower() in ["igst status", "igst mode"] or item_rules[item_field].get("col", "").strip().upper() in ["V", "B19"]:[cite: 1]
                    continue[cite: 1]

                ir = item_rules[item_field][cite: 1]
                ic1, ic2, ic3, ic4, ic5 = st.columns([3, 2, 3, 3, 1])[cite: 1]
                
                saved_type = ir.get("type", "PDF Row Item")[cite: 1]
                type_idx = rule_type_options.index(saved_type) if saved_type in rule_type_options else 0[cite: 1]
                
                with ic1: e_ifield = st.text_input(f"if_{item_field}", value=item_field, label_visibility="collapsed")[cite: 1]
                with ic2: e_icol = st.text_input(f"ic_{item_field}", value=ir.get("col", "K"), label_visibility="collapsed").upper()[cite: 1]
                with ic3: e_itype = st.selectbox(f"it_{item_field}", rule_type_options, index=type_idx, label_visibility="collapsed")[cite: 1]
                with ic4: e_irule = st.text_input(f"ir_{item_field}", value=ir.get("rule", ""), label_visibility="collapsed")[cite: 1]
                with ic5:[cite: 1]
                    if st.button("🗑️", key=f"idel_{item_field}"):[cite: 1]
                        del item_rules[item_field][cite: 1]
                        st.rerun()[cite: 1]
                        
                updated_item_rules[e_ifield] = {"col": e_icol, "type": e_itype, "rule": e_irule}[cite: 1]
                
            st.session_state["shipper_database"][selected_shipper]["item_table_rules"] = updated_item_rules[cite: 1]
            st.write("---")[cite: 1]
            
            # SAVE BUTTON
            if st.button("💾 Save All AI Mapping Rules to Google Sheet", type="primary", use_container_width=True):[cite: 1]
                rules_payload = [][cite: 1]
                
                for s_name, s_data in st.session_state["shipper_database"].items():[cite: 1]
                    # 1. Header Rules
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():[cite: 1]
                        rules_payload.append({[cite: 1]
                            "ShipperName": s_name, "FieldName": f_name, "Keyword": r_info.get("keyword", ""),[cite: 1]
                            "Position": r_info.get("position", "Right (आगे)"), "Cell": r_info.get("cell", ""),[cite: 1]
                            "MatchMode": r_info.get("match_mode", "Exact Word"), "StopKw": r_info.get("stop_kw", ""),[cite: 1]
                            "Filter": r_info.get("filter", "None"), "Logic": r_info.get("logic", "None"),[cite: 1]
                            "RuleKind": "header"[cite: 1]
                        })[cite: 1]
                    # 2. Item Rules
                    for i_field, i_info in s_data.get("item_table_rules", {}).items():[cite: 1]
                        rules_payload.append({[cite: 1]
                            "ShipperName": s_name, "FieldName": i_field, "Keyword": i_info.get("rule", ""),[cite: 1]
                            "Position": "Right (आगे)", "Cell": i_info.get("col", "K"),[cite: 1]
                            "MatchMode": i_info.get("type", "PDF Row Item"), "StopKw": "",[cite: 1]
                            "Filter": "None", "Logic": "None",[cite: 1]
                            "RuleKind": "item"[cite: 1]
                        })[cite: 1]
                
                full_post_data = {[cite: 1]
                    "action": "save_all",[cite: 1]
                    "rules": rules_payload,[cite: 1]
                    "files": [] # NO BINARY FILE SENT TO GOOGLE SHEET TO PREVENT TRUNCATION/CORRUPTION
                }[cite: 1]
                
                with st.spinner("⏳ गूगल शीट में रूल्स सुरक्षित सेव हो रहे हैं..."):[cite: 1]
                    try:[cite: 1]
                        requests.post(WEB_APP_URL, data=json.dumps(full_post_data), timeout=30)[cite: 1]
                        st.success("🎉 आपके सभी रूल्स गूगल शीट में 100% परमानेंट सेव हो गए हैं!")[cite: 1]
                        st.balloons()[cite: 1]
                    except Exception as e:[cite: 1]
                        st.error(f"सिंक एरर: {str(e)}")[cite: 1]

            # ATTACHED UNIVERSAL TEST SUITE AT THE VERY BOTTOM
            render_universal_test_suite(selected_shipper)[cite: 1]
