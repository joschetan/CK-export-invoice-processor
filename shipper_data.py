import streamlit as st
import requests
import json
import base64
import pdfplumber
import re
import time
from io import BytesIO

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

def ensure_default_shipper():
    if "shipper_database" not in st.session_state:
        st.session_state["shipper_database"] = {}
        
    if "WELSPUN GLOBAL BRANDS LIMITED" not in st.session_state["shipper_database"]:
        initial_rules = dict(st.session_state.get("master_rules_template", {}))
        st.session_state["shipper_database"]["WELSPUN GLOBAL BRANDS LIMITED"] = {
            "allowed_uploads": ["Full Job Excel Format File"], 
            "uploaded_files": {},
            "mapping_rules": initial_rules,
            "item_table_rules": {
                "RITC / HS Code": {"col": "K", "type": "PDF Row Item", "rule": "HS Code"},
                "Quantity": {"col": "N", "type": "PDF Row Item", "rule": "Qty Number"},
                "Unit (UNIT)": {"col": "O", "type": "Smart Detection", "rule": "Detect SET or PCS from Description"},
                "Goods Value (USD)": {"col": "P", "type": "PDF Row Item", "rule": "Goods Value"},
                "Drawback SR Code": {"col": "R", "type": "PDF Row Item", "rule": "DBK SR (+B Suffix)"},
                "Taxable Value (INR)": {"col": "V", "type": "PDF Row Item", "rule": "Taxable Amt"},
                "IGST Rate (%)": {"col": "W", "type": "PDF Row Item", "rule": "IGST %"},
                "IGST Amount (INR)": {"col": "X", "type": "PDF Row Item", "rule": "IGST Amt"}
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
            rules_list = data.get("rules", data.get("data", [])) if isinstance(data, dict) else data
                
            if isinstance(rules_list, list) and len(rules_list) > 0:
                for row in rules_list:
                    if isinstance(row, dict):
                        s_name = get_val_case_insensitive(row, "ShipperName", "shipper", "shippername")
                        f_name = get_val_case_insensitive(row, "FieldName", "field", "fieldname")
                        
                        if s_name and f_name:
                            target_key = s_name
                            if "welspun" in s_name.lower():
                                target_key = "WELSPUN GLOBAL BRANDS LIMITED"
                                
                            if target_key not in st.session_state["shipper_database"]:
                                st.session_state["shipper_database"][target_key] = {
                                    "allowed_uploads": ["Full Job Excel Format File"],
                                    "uploaded_files": {},
                                    "mapping_rules": {},
                                    "item_table_rules": {}
                                }
                            
                            st.session_state["shipper_database"][target_key]["mapping_rules"][f_name] = {
                                "keyword": get_val_case_insensitive(row, "Keyword", "keyword", "kw"),
                                "position": get_val_case_insensitive(row, "Position", "position", "pos", default="Right (आगे)"),
                                "cell": get_val_case_insensitive(row, "Cell", "cell"),
                                "match_mode": get_val_case_insensitive(row, "MatchMode", "match_mode", "matchmode", default="Exact Word"),
                                "stop_kw": get_val_case_insensitive(row, "StopKw", "stop_kw", "stopkw"),
                                "filter": get_val_case_insensitive(row, "Filter", "filter", "flt", default="None"),
                                "logic": get_val_case_insensitive(row, "Logic", "logic", "lg", default="None")
                            }
                if show_toast: st.toast(f"✅ गूगल शीट से रूल्स लोड हो गए!")
    except Exception as e:
        if show_toast: st.error(f"फ़ैच एरर: {str(e)}")

@st.dialog("➕ Add Item Column Rule")
def add_item_col_dialog(selected_shipper):
    st.write("यहाँ आइटम टेबल के लिए नया कॉलम हेडिंग और एक्सेल कॉलम जोड़ें:")
    c_name = st.text_input("Heading Name (उदा: Net Weight, Boxes, Size):")
    c_col = st.text_input("Excel Column Letter (उदा: L, M, N, Z):").upper()
    c_type = st.selectbox("Rule Type:", ["PDF Row Item", "Constant Text", "Smart Detection"])
    c_rule = st.text_input("Rule Detail / Value (उदा: SET, PCS, Numbers Only):")
    
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
            has_file = "Full Job Excel Format File" in shipper_info.get("uploaded_files", {})
            if has_file:
                st.success("✅ Blank Full Job Excel Format File अपलोडेड है।")
                if st.button("🗑️ Delete & Replace Template", key=f"del_tpl_{selected_shipper}"):
                    del shipper_info["uploaded_files"]["Full Job Excel Format File"]
                    st.rerun()
            else:
                f_upload = st.file_uploader("➡️ Blank Full Job Excel Format File (Template) अपलोड करें", type=["xlsx", "xls"], key=f"tpl_{selected_shipper}")
                if f_upload:
                    shipper_info["uploaded_files"]["Full Job Excel Format File"] = f_upload.getvalue()
                    st.success("टेम्पलेट सेव हो गया!")
                    st.rerun()
                    
            st.write("---")
            
            # --- SECTION 3: HEADER MAPPING RULES ---
            col_title, col_sync = st.columns([6, 4])
            with col_title:
                st.subheader("🛠️ 3. Header Fields Mapping Rules")
            with col_sync:
                if st.button("🔄 Reload Saved Rules from Sheet", type="secondary", use_container_width=True):
                    st.session_state["shipper_database"] = {}
                    fetch_data_from_google_sheet(show_toast=True)
                    st.rerun()
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 2.5, 1.5, 1, 1.8, 1.5, 1.5])
            with c1: st.markdown("**Field Name**")
            with c2: st.markdown("**Keyword**")
            with c3: st.markdown("**Position**")
            with c4: st.markdown("**Cell**")
            with c5: st.markdown("**Match Mode**")
            with c6: st.markdown("**Stop / Word No.**")
            with c7: st.markdown("**Filter/Logic**")
            st.write("---")
            
            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 2.5, 1.5, 1, 1.8, 1.5, 1.5])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c3: pos = st.selectbox(f"p_{field}", ["Right (आगे)", "Below (नीचे)"], index=0 if s_val.get("position") == "Right (आगे)" else 1, label_visibility="collapsed")
                with c4: cl = st.text_input(f"c_{field}", value=s_val.get("cell", ""), label_visibility="collapsed")
                with c5: m_mode = st.selectbox(f"mm_{field}", ["Exact Word", "Word Position", "Full Line", "After Word", "Skip 1st Word"], label_visibility="collapsed")
                with c6: stop_kw = st.text_input(f"sk_{field}", value=s_val.get("stop_kw", ""), label_visibility="collapsed")
                with c7: final_flt = st.selectbox(f"flt_{field}", ["None", "Numbers Only", "Letters Only", "Container Number (ISO Format)", "Container Size (20/40 Only)"], label_visibility="collapsed")
                
                updated_rules[edited_name] = {"keyword": ky, "position": pos, "cell": cl, "match_mode": m_mode, "stop_kw": stop_kw, "filter": final_flt, "logic": "None"}
                
            st.session_state["shipper_database"][selected_shipper]["mapping_rules"] = updated_rules
            
            st.write("---")
            
            # --- SECTION 4: DYNAMIC ITEM TABLE COLUMN BUILDER ---
            c_head, c_add_btn = st.columns([7, 3])
            with c_head:
                st.subheader("📦 4. Dynamic Item Table Column Builder (Shipper-Wise)")
            with c_add_btn:
                if st.button("➕ Add Item Column", use_container_width=True):
                    add_item_col_dialog(selected_shipper)
            
            item_rules = shipper_info.setdefault("item_table_rules", {})
            updated_item_rules = {}
            
            ic1, ic2, ic3, ic4, ic5 = st.columns([3, 2, 3, 3, 1])
            with ic1: st.markdown("**Item Field Name**")
            with ic2: st.markdown("**Excel Column**")
            with ic3: st.markdown("**Rule Type**")
            with ic4: st.markdown("**Rule Detail / Value**")
            with ic5: st.markdown("**Del**")
            st.write("---")
            
            for item_field in list(item_rules.keys()):
                ir = item_rules[item_field]
                ic1, ic2, ic3, ic4, ic5 = st.columns([3, 2, 3, 3, 1])
                
                with ic1: e_ifield = st.text_input(f"if_{item_field}", value=item_field, label_visibility="collapsed")
                with ic2: e_icol = st.text_input(f"ic_{item_field}", value=ir.get("col", "K"), label_visibility="collapsed").upper()
                with ic3: e_itype = st.selectbox(f"it_{item_field}", ["PDF Row Item", "Constant Text", "Smart Detection"], index=0 if ir.get("type")=="PDF Row Item" else (1 if ir.get("type")=="Constant Text" else 2), label_visibility="collapsed")
                with ic4: e_irule = st.text_input(f"ir_{item_field}", value=ir.get("rule", ""), label_visibility="collapsed")
                with ic5:
                    if st.button("🗑️", key=f"idel_{item_field}"):
                        del item_rules[item_field]
                        st.rerun()
                        
                updated_item_rules[e_ifield] = {"col": e_icol, "type": e_itype, "rule": e_irule}
                
            st.session_state["shipper_database"][selected_shipper]["item_table_rules"] = updated_item_rules
            st.write("---")
            
            if st.button("💾 Save All AI Mapping Rules to Google Sheet", type="primary", use_container_width=True):
                rules_payload = []
                for s_name, s_data in st.session_state["shipper_database"].items():
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({
                            "ShipperName": s_name, "FieldName": f_name, "Keyword": r_info.get("keyword", ""),
                            "Position": r_info.get("position", "Right (आगे)"), "Cell": r_info.get("cell", ""),
                            "MatchMode": r_info.get("match_mode", "Exact Word"), "StopKw": r_info.get("stop_kw", ""),
                            "Filter": r_info.get("filter", "None"), "Logic": r_info.get("logic", "None")
                        })
                
                with st.spinner("⏳ गूगल शीट में सिंक हो रहा है..."):
                    try:
                        requests.post(WEB_APP_URL, data=json.dumps({"action": "save_rules", "rules": rules_payload}), timeout=30)
                        st.success("🎉 आपके सभी रूल्स (Header + Items) गूगल शीट में सुरक्षित सेव हो गए हैं!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"सिंक एरर: {str(e)}")
