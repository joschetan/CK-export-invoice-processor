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
from pdf_engine import extract_header_value, detect_igst_status

# Import Universal Test Suite module
from test_suite import render_universal_test_suite

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"

def get_val_case_insensitive(d, *keys, default=""):
    if not isinstance(d, dict):
        return default
    d_lower = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        if str(k).lower() in d_lower:
            val = d_lower[str(k).lower()]
            if val is not None:
                return str(val).strip()
    return default

def get_default_item_rules():
    return {
        "RITC / HS Code": {"col": "K", "type": "PDF Row Item", "rule": "HS Code"},
        "Description of Goods": {"col": "M", "type": "PDF Row Item", "rule": "Description"},
        "Quantity": {"col": "N", "type": "PDF Row Item", "rule": "Qty Number"},
        "Unit (UNIT)": {"col": "O", "type": "Smart Detection", "rule": "SET"},
        "Rate in": {"col": "P", "type": "PDF Row Item", "rule": "Rate"},
        "Amount": {"col": "Q", "type": "PDF Row Item", "rule": "Amount USD"},
        "ROSCTL": {"col": "R", "type": "Smart Detection", "rule": "ROSCTL:60:19"},
        "Drawback SR Code": {"col": "S", "type": "PDF Row Item", "rule": "DBK SR (+B Suffix)"},
        "Taxable Value (INR)": {"col": "W", "type": "PDF Row Item", "rule": "Taxable Amt"},
        "IGST Rate (%)": {"col": "X", "type": "PDF Row Item", "rule": "IGST %"},
        "IGST Amount (INR)": {"col": "Y", "type": "PDF Row Item", "rule": "IGST Amt"},
        "Nt.Wt(KGS)": {"col": "AB", "type": "PDF Row Item", "rule": "Net Weight"}
    }

def ensure_default_shipper():
    if "shipper_database" not in st.session_state:
        st.session_state["shipper_database"] = {}
        
    s_name = "WELSPUN GLOBAL BRANDS LIMITED"
    if s_name not in st.session_state["shipper_database"]:
        st.session_state["shipper_database"][s_name] = {
            "allowed_uploads": ["Full Job Excel Format File"], 
            "uploaded_files": {},
            "mapping_rules": {},
            "item_table_rules": get_default_item_rules(),
            "igst_config": {
                "lut_keywords": "LUT ARN NO., w/o payment of integrated tax, under bond",
                "paid_keywords": "on payment of integrated tax, with payment of integrated tax"
            }
        }

def fetch_data_from_google_sheet(show_toast=False):
    ensure_default_shipper()
    try:
        response = requests.get(f"{WEB_APP_URL}?action=get_data", timeout=15)
        if response.status_code == 200:
            res_text = response.text.strip()
            if res_text.startswith("<"):
                if show_toast: st.error("⚠️ गूगल शीट से HTML मिला। Web App Access 'Anyone' करें।")
                return

            data = response.json()
            
            fetched_item_rules = {}
            fetched_header_rules = {}
            item_columns = ["K", "M", "N", "O", "P", "Q", "R", "S", "W", "X", "Y", "AB"]

            rules_list = data.get("rules", data.get("data", [])) if isinstance(data, dict) else data
            if isinstance(rules_list, list) and len(rules_list) > 0:
                for row in rules_list:
                    if isinstance(row, dict):
                        s_name = get_val_case_insensitive(row, "ShipperName", "shipper", "shippername")
                        f_name = get_val_case_insensitive(row, "FieldName", "field", "fieldname")
                        rule_kind = get_val_case_insensitive(row, "RuleKind", "kind", default="header").lower()
                        cell_val = get_val_case_insensitive(row, "Cell", "cell", "col").strip().upper()
                        
                        if f_name.lower() in ["igst status", "igst mode"] or cell_val in ["V", "B19"]:
                            continue

                        if s_name and f_name:
                            target_key = "WELSPUN GLOBAL BRANDS LIMITED" if "welspun" in s_name.lower() else s_name
                                
                            if target_key not in st.session_state["shipper_database"]:
                                st.session_state["shipper_database"][target_key] = {
                                    "allowed_uploads": ["Full Job Excel Format File"],
                                    "uploaded_files": {},
                                    "mapping_rules": {},
                                    "item_table_rules": {},
                                    "igst_config": {
                                        "lut_keywords": "LUT ARN NO., w/o payment of integrated tax, under bond",
                                        "paid_keywords": "on payment of integrated tax, with payment of integrated tax"
                                    }
                                }
                            
                            if "item" in rule_kind or cell_val in item_columns or f_name.upper() == "ROSCTL":
                                fetched_item_rules.setdefault(target_key, {})[f_name] = {
                                    "col": cell_val if cell_val else "R",
                                    "type": get_val_case_insensitive(row, "MatchMode", "match_mode", "type", default="Smart Detection"),
                                    "rule": get_val_case_insensitive(row, "Keyword", "keyword", "rule")
                                }
                            else:
                                fetched_header_rules.setdefault(target_key, {})[f_name] = {
                                    "keyword": get_val_case_insensitive(row, "Keyword", "keyword", "kw"),
                                    "position": get_val_case_insensitive(row, "Position", "position", "pos", default="Right (आगे)"),
                                    "cell": cell_val,
                                    "match_mode": get_val_case_insensitive(row, "MatchMode", "match_mode", "matchmode", default="Exact Word"),
                                    "stop_kw": get_val_case_insensitive(row, "StopKw", "stop_kw", "stopkw"),
                                    "filter": get_val_case_insensitive(row, "Filter", "filter", "flt", default="None"),
                                    "logic": get_val_case_insensitive(row, "Logic", "logic", "lg", default="None")
                                }

                for s_key, s_data in st.session_state["shipper_database"].items():
                    if s_key in fetched_header_rules:
                        s_data["mapping_rules"] = {k: v for k, v in fetched_header_rules[s_key].items() if k.upper() != "ROSCTL"}
                        
                    if s_key in fetched_item_rules and fetched_item_rules[s_key]:
                        s_data["item_table_rules"] = fetched_item_rules[s_key]
                    elif not s_data.get("item_table_rules"):
                        s_data["item_table_rules"] = get_default_item_rules()

            # 2. Fetch Files (From Shipper_Files)
            files_list = data.get("files", []) if isinstance(data, dict) else []
            if isinstance(files_list, list):
                for f_row in files_list:
                    if isinstance(f_row, dict):
                        s_name = get_val_case_insensitive(f_row, "ShipperName", "shipper")
                        b64_str = get_val_case_insensitive(f_row, "FileBase64", "base64", "file")
                        target_key = "WELSPUN GLOBAL BRANDS LIMITED" if "welspun" in s_name.lower() else s_name
                        if target_key in st.session_state["shipper_database"]:
                            if b64_str and len(b64_str.strip()) > 0:
                                try:
                                    decoded_bytes = base64.b64decode(b64_str)
                                    st.session_state["shipper_database"][target_key]["uploaded_files"]["Full Job Excel Format File"] = decoded_bytes
                                except Exception as e: pass
                            else:
                                # 🎯 Sheet mein khali hai toh session se bhi uda do
                                st.session_state["shipper_database"][target_key]["uploaded_files"]["Full Job Excel Format File"] = b""

                if show_toast: st.toast(f"✅ गूगल शीट से रूल्स लोड हो गए!")
    except Exception as e:
        if show_toast: st.error(f"फ़ैच एरर: {str(e)}")

@st.dialog("🧪 Live Extraction Field Test Result")
def show_field_test_dialog(field_name, rule_data, result_val):
    st.write(f"### 🔍 Field: **`{field_name}`**")
    st.markdown("#### 📋 Applied Rule Parameters:")
    
    raw_cell = str(rule_data.get('cell', 'Blank')).strip()
    display_cell = f"{raw_cell} (Dynamic Row)" if raw_cell and raw_cell.isalpha() else raw_cell

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"* **Keyword:** `{rule_data.get('keyword', 'N/A')}`")
        st.markdown(f"* **Position:** `{rule_data.get('position', 'Right (आगे)')}`")
        st.markdown(f"* **Target Cell:** `{display_cell}`")
    with col_b:
        st.markdown(f"* **Match Mode:** `{rule_data.get('match_mode', 'Exact Word')}`")
        st.markdown(f"* **Stop / Word No.:** `{rule_data.get('stop_kw', 'N/A')}`")
        st.markdown(f"* **Filter/Logic:** `{rule_data.get('filter', 'None')}`")
        
    st.write("---")
    st.markdown("#### 🎯 Extracted Result from Uploaded PDF:")
    if "❌" in result_val or not result_val.strip():
        st.error(f"❌ **Not Found!** Value: `{result_val}`")
    else:
        st.success(f"🎉 **SUCCESS! Extracted Value:**")
        st.code(result_val, language="text")

@st.dialog("⚠️ Urgent: Verify IGST Status for Column V")
def show_igst_manual_prompt_dialog(invoice_no):
    st.warning(f"⚠️ इन्वॉइस **`{invoice_no}`** पर LUT या Paid (P) का स्पष्ट टेक्स्ट नहीं मिला!")
    st.write("कस्टम्स में भारी पेनाल्टी से बचने के लिए कृपया खुद से कन्फर्म करें:")
    
    selected_status = st.selectbox("Column V के लिए सही मोड चुनें:", ["P", "LUT"], index=0)
    
    if st.button("Confirm & Apply to Column V", type="primary"):
        st.session_state[f"manual_igst_{invoice_no}"] = selected_status
        st.success(f"✅ Selected `{selected_status}` for Invoice `{invoice_no}`")
        st.rerun()

@st.dialog("➕ Add New Custom Header Field")
def add_custom_header_field_dialog(selected_shipper):
    st.write("यहाँ नया हेडर फ़ील्ड जोड़ें:")
    new_field = st.text_input("Field Name (उदा: Invoice No, Port of Loading):")
    if st.button("Confirm & Add Field", type="primary"):
        if not new_field.strip():
            st.error("फ़ील्ड नाम खाली नहीं हो सकता!")
        else:
            rules = st.session_state["shipper_database"][selected_shipper].setdefault("mapping_rules", {})
            rules[new_field.strip()] = {
                "keyword": "", "position": "Right (आगे)", "cell": "",
                "match_mode": "Exact Word", "stop_kw": "", "filter": "None", "logic": "None"
            }
            st.success(f"🎉 फ़ील्ड '{new_field}' जुड़ गया!")
            st.rerun()

@st.dialog("➕ Add Item Column Rule")
def add_item_col_dialog(selected_shipper):
    st.write("यहाँ आइटम टेबल के लिए नया कॉलम हेडिंग और एक्सेल कॉलम जोड़ें:")
    c_name = st.text_input("Heading Name (उदा: Net Weight, Boxes, Size):")
    c_col = st.text_input("Excel Column Letter (उदा: L, M, N, Z):").upper()
    c_type = st.selectbox("Rule Type:", ["PDF Row Item", "Table Row Item", "Constant Text", "Excel Cell Reference", "Smart Detection"])
    c_rule = st.text_input("Rule Detail / Value (उदा: B19, SET, PCS, Numbers Only):")
    
    if st.button("Confirm & Add Item Column", type="primary"):
        if not c_name or not c_col:
            st.error("Heading Name और Column Letter अनिवार्य हैं!")
        else:
            item_rules = st.session_state["shipper_database"][selected_shipper].setdefault("item_table_rules", {})
            item_rules[c_name] = {"col": c_col, "type": c_type, "rule": c_rule}
            st.success(f"🎉 कॉलम '{c_name}' जुड़ गया!")
            st.rerun()

def render_shipper_data():
    if "sheet_data_loaded" not in st.session_state:
        fetch_data_from_google_sheet(show_toast=False)
        st.session_state["sheet_data_loaded"] = True
    
    st.header("🏢 Add Shipper Name & Live-Test AI Mapping Builder")
    st.caption("सटीक डेटा एक्सट्रैक्शन और रो-बाय-रो लाइव टेस्ट इंजन।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list, index=0)
        
        if selected_shipper:
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            # --- SECTION 1: TEMPLATE UPLOAD ---
            st.subheader("📁 1. टेम्पलेट फ़ाइल अपलोड")
            
            uploaded_files_dict = shipper_info.get("uploaded_files", {})
            has_file = "Full Job Excel Format File" in uploaded_files_dict and len(uploaded_files_dict["Full Job Excel Format File"]) > 0
            
            if has_file:
                st.success("✅ Blank Full Job Excel Format File अपलोडेड एवं सुरक्षित है।")
                if st.button("🗑️ Delete & Replace Template", key=f"del_tpl_{selected_shipper}"):
                    shipper_info["uploaded_files"]["Full Job Excel Format File"] = b""
                    st.rerun()
            else:
                f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template) अपलोड करें", type=["xlsx", "xls"], key=f"tpl_{selected_shipper}")
                if f_upload is not None:
                    file_bytes = f_upload.getvalue()
                    if file_bytes and len(file_bytes) > 0:
                        shipper_info.setdefault("uploaded_files", {})["Full Job Excel Format File"] = file_bytes
                        st.success("टेम्पलेट लोड हो गया! नीचे 'Save All Rules' दबाकर गूगल शीट में सेव करें।")
                        st.rerun()
                    
            st.write("---")
            
            # --- SECTION 2: LIVE TEST PDF ENGINE ---
            st.subheader("🧪 2. Instant PDF Upload & Live Data Test Engine")
            st.caption("यहाँ टेस्ट इनवॉइस PDF अपलोड करें, फिर रूल्स के सामने ⚡ Test दबाकर पॉप-अप में लाइव डेटा देखें।")
            
            test_pdf = st.file_uploader("➡️ टेस्ट करने के लिए इनवॉइस PDF अपलोड करें", type=["pdf"], key=f"test_pdf_{selected_shipper}")
            
            pdf_lines = []
            pdf_text = ""
            if test_pdf:
                with pdfplumber.open(test_pdf) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            pdf_text += t + "\n"
                            pdf_lines.extend(t.split("\n"))
                st.session_state["cached_pdf_lines"] = pdf_lines
                st.session_state["cached_pdf_text"] = pdf_text
                st.success(f"📄 PDF अपलोड है ({len(pdf_lines)} पंक्तियाँ)। अब नीचे ⚡ Test बटन दबाएँ!")

            st.write("---")
            
            # --- SECTION 3: HEADER MAPPING RULES ---
            col_title, col_sync, col_add_h = st.columns([5, 3, 2])
            with col_title:
                st.subheader("🛠️ 3. Header Fields Mapping Rules")
            with col_sync:
                if st.button("🔄 Reload Saved Rules from Sheet", type="secondary", use_container_width=True):
                    st.session_state["shipper_database"] = {}
                    fetch_data_from_google_sheet(show_toast=True)
                    st.rerun()
            with col_add_h:
                if st.button("➕ Add Header Field", type="secondary", use_container_width=True):
                    add_custom_header_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            pos_options = ["Right (आगे)", "Below (नीचे)", "2 Lines Below", "Table Row Item", "Table Row Index"]
            mode_options = ["Exact Word", "Word Position", "Full Line", "After Word", "Between Keywords", "Table Row Match"]
            
            filter_options = [
                "None", 
                "Text Inside Parentheses ()", 
                "Numbers Only", 
                "Letters Only", 
                "Container Number (ISO Format)", 
                "Container Size (20/40 Only)", 
                "Clean Date (DD/MM/YYYY)"
            ]
            
            c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2, 2.5, 1.5, 0.8, 1.8, 1.5, 1.8, 0.8, 1.2])
            with c1: st.markdown("**Field Name**")
            with c2: st.markdown("**Keyword**")
            with c3: st.markdown("**Position**")
            with c4: st.markdown("**Cell**")
            with c5: st.markdown("**Match Mode**")
            with c6: st.markdown("**Stop / Word No.**")
            with c7: st.markdown("**Filter/Logic**")
            with c8: st.markdown("**Del**")
            with c9: st.markdown("**⚡ Live Test**")
            st.write("---")
            
            curr_pdf_lines = st.session_state.get("cached_pdf_lines", [])
            curr_pdf_text = st.session_state.get("cached_pdf_text", "")

            for field in list(current_rules.keys()):
                if field.lower() in ["igst status", "igst mode", "rosctl"] or current_rules[field].get("cell", "").strip().upper() in ["V", "B19", "R"]:
                    continue

                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([2, 2.5, 1.5, 0.8, 1.8, 1.5, 1.8, 0.8, 1.2])
                
                saved_pos = s_val.get("position", "Right (आगे)")
                pos_idx = pos_options.index(saved_pos) if saved_pos in pos_options else 0
                
                saved_mode = s_val.get("match_mode", "Exact Word")
                mode_idx = mode_options.index(saved_mode) if saved_mode in mode_options else 0
                
                saved_flt = s_val.get("filter", "None")
                if saved_flt in ["Inside Parentheses ()", "Text Inside ()"]:
                    saved_flt = "Text Inside Parentheses ()"
                
                flt_idx = filter_options.index(saved_flt) if saved_flt in filter_options else 0

                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c3: pos = st.selectbox(f"p_{field}", pos_options, index=pos_idx, label_visibility="collapsed")
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                with c5: m_mode = st.selectbox(f"mm_{field}", mode_options, index=mode_idx, label_visibility="collapsed")
                with c6: stop_kw = st.text_input(f"sk_{field}", value=s_val.get("stop_kw", ""), label_visibility="collapsed")
                with c7: final_flt = st.selectbox(f"flt_{field}", filter_options, index=flt_idx, label_visibility="collapsed")
                with c8:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field]
                        st.rerun()
                with c9:
                    if st.button("⚡ Test", key=f"test_btn_{field}"):
                        if not curr_pdf_lines:
                            st.toast("⚠️ पहले Section 2 में PDF अपलोड करें!")
                        else:
                            res_val = extract_header_value(curr_pdf_lines, curr_pdf_text, ky, pos, m_mode, stop_kw, final_flt)
                            
                            rule_summary = {
                                "keyword": ky, "position": pos, "cell": cl,
                                "match_mode": m_mode, "stop_kw": stop_kw, "filter": final_flt
                            }
                            show_field_test_dialog(edited_name, rule_summary, res_val if res_val else "❌ (Not Found)")
                
                updated_rules[edited_name] = {"keyword": ky, "position": pos, "cell": cl, "match_mode": m_mode, "stop_kw": stop_kw, "filter": final_flt, "logic": "None"}
                
            st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules
            
            # --- SECTION 3.1: SHIPPER-WISE IGST STATUS (COLUMN V) CONFIGURATOR ---
            st.write("---")
            st.subheader("🛡️ Column V Auto-Detection Configurator (LUT vs Paid 'P')")
            st.caption("कस्टम्स पेनल्टी से बचने के लिए शिपर के हिसाब से LUT और Paid ढूँढने के कीवर्ड्स यहाँ तय करें:")
            
            igst_cfg = shipper_info.setdefault("igst_config", {
                "lut_keywords": "LUT ARN NO., w/o payment of integrated tax, under bond",
                "paid_keywords": "on payment of integrated tax, with payment of integrated tax"
            })
            
            col_lut, col_paid = st.columns(2)
            with col_lut:
                updated_lut_kws = st.text_area(
                    "📌 LUT Detection Keywords (कॉमा से अलग करें):",
                    value=igst_cfg.get("lut_keywords", "LUT ARN NO., w/o payment of integrated tax, under bond"),
                    help="अगर इनमें से कोई भी शब्द PDF में मिला तो V कॉलम में सीधे 'LUT' जाएगा।"
                )
            with col_paid:
                updated_paid_kws = st.text_area(
                    "📌 Paid (P) Detection Keywords (कॉमा से अलग करें):",
                    value=igst_cfg.get("paid_keywords", "on payment of integrated tax, with payment of integrated tax"),
                    help="अगर LUT नहीं मिला और इनमें से कोई शब्द मिला तो V कॉलम में सीधे 'P' जाएगा।"
                )
                
            shipper_info["igst_config"] = {
                "lut_keywords": updated_lut_kws,
                "paid_keywords": updated_paid_kws
            }

            st.write("---")
            
            # --- SECTION 4: DYNAMIC ITEM TABLE COLUMN BUILDER ---
            c_head, c_add_btn = st.columns([7, 3])
            with c_head:
                st.subheader("📦 4. Dynamic Item Table Column Builder (Shipper-Wise)")
            with c_add_btn:
                if st.button("➕ Add Item Column", use_container_width=True):
                    add_item_col_dialog(selected_shipper)
            
            item_rules = shipper_info.get("item_table_rules", {})
            if not item_rules:
                item_rules = get_default_item_rules()
                shipper_info["item_table_rules"] = item_rules

            updated_item_rules = {}
            
            ic1, ic2, ic3, ic4, ic5 = st.columns([3, 2, 3, 3, 1])
            with ic1: st.markdown("**Item Field Name**")
            with ic2: st.markdown("**Excel Column**")
            with ic3: st.markdown("**Rule Type**")
            with ic4: st.markdown("**Rule Detail / Value**")
            with ic5: st.markdown("**Del**")
            st.write("---")
            
            rule_type_options = ["PDF Row Item", "Table Row Item", "Constant Text", "Excel Cell Reference", "Smart Detection"]
            
            for item_field in list(item_rules.keys()):
                if item_field.lower() in ["igst status", "igst mode"] or item_rules[item_field].get("col", "").strip().upper() in ["V", "B19"]:
                    continue

                ir = item_rules[item_field]
                ic1, ic2, ic3, ic4, ic5 = st.columns([3, 2, 3, 3, 1])
                
                saved_type = ir.get("type", "PDF Row Item")
                type_idx = rule_type_options.index(saved_type) if saved_type in rule_type_options else 0
                
                with ic1: e_ifield = st.text_input(f"if_{item_field}", value=item_field, label_visibility="collapsed")
                with ic2: e_icol = st.text_input(f"ic_{item_field}", value=ir.get("col", "K"), label_visibility="collapsed").upper()
                with ic3: e_itype = st.selectbox(f"it_{item_field}", rule_type_options, index=type_idx, label_visibility="collapsed")
                with ic4: e_irule = st.text_input(f"ir_{item_field}", value=ir.get("rule", ""), label_visibility="collapsed")
                with ic5:
                    if st.button("🗑️", key=f"idel_{item_field}"):
                        del item_rules[item_field]
                        st.rerun()
                        
                updated_item_rules[e_ifield] = {"col": e_icol, "type": e_itype, "rule": e_irule}
                
            st.session_state["shipper_database"][selected_shipper]["item_table_rules"] = updated_item_rules
            st.write("---")
            
            # SAVE BUTTON
            if st.button("💾 Save All AI Mapping Rules to Google Sheet", type="primary", use_container_width=True):
                rules_payload = []
                files_payload = []
                
                for s_name, s_data in st.session_state["shipper_database"].items():
                    # 1. Header Rules
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({
                            "ShipperName": s_name, "FieldName": f_name, "Keyword": r_info.get("keyword", ""),
                            "Position": r_info.get("position", "Right (आगे)"), "Cell": r_info.get("cell", ""),
                            "MatchMode": r_info.get("match_mode", "Exact Word"), "StopKw": r_info.get("stop_kw", ""),
                            "Filter": r_info.get("filter", "None"), "Logic": r_info.get("logic", "None"),
                            "RuleKind": "header"
                        })
                    # 2. Item Rules
                    for i_field, i_info in s_data.get("item_table_rules", {}).items():
                        rules_payload.append({
                            "ShipperName": s_name, "FieldName": i_field, "Keyword": i_info.get("rule", ""),
                            "Position": "Right (आगे)", "Cell": i_info.get("col", "K"),
                            "MatchMode": i_info.get("type", "PDF Row Item"), "StopKw": "",
                            "Filter": "None", "Logic": "None",
                            "RuleKind": "item"
                        })
                        
                    # 3. Template File payload
                    tpl_bytes = s_data.get("uploaded_files", {}).get("Full Job Excel Format File", b"")
                    if isinstance(tpl_bytes, bytes) and len(tpl_bytes) > 0:
                        b64_str = base64.b64encode(tpl_bytes).decode('utf-8')
                        files_payload.append({
                            "ShipperName": s_name,
                            "FileBase64": b64_str
                        })
                    else:
                        # 🎯 FORCE GOOGLE SHEET TO CLEAR FILE ROW IF DELETED
                        files_payload.append({
                            "ShipperName": s_name,
                            "FileBase64": ""
                        })
                
                full_post_data = {
                    "action": "save_all",
                    "rules": rules_payload,
                    "files": files_payload
                }
                
                with st.spinner("⏳ गूगल शीट (Shipper_Rules + Shipper_Files) में सुरक्षित सेव हो रहा है..."):
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps(full_post_data), timeout=30)
                        st.success("🎉 आपके सभी रूल्स गूगल शीट में 100% परमानेंट सेव हो गए हैं!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"सिंक एरर: {str(e)}")

            # ATTACHED UNIVERSAL TEST SUITE AT THE VERY BOTTOM
            render_universal_test_suite(selected_shipper)
