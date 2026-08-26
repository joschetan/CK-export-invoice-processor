import streamlit as st
import pdfplumber
import re
import pandas as pd
from pdf_engine import extract_header_value, apply_value_replacement
from parser_welspun import extract_welspun_items
from parser_bkt import extract_bkt_items

def render_universal_test_suite(selected_shipper):
    st.markdown("---")
    st.header("🚀 Master Test Engine (All Rules Validator)")
    st.caption("एक क्लिक में सभी हेडर और आइटम रूल्स को रन करें और नीचे टेबल में देखें कि किस कीवर्ड से क्या एक्सट्रैक्ट हुआ है।")

    if "cached_pdf_lines" not in st.session_state or not st.session_state["cached_pdf_lines"]:
        st.info("💡 कृपया पहले Section 2 में अपनी इनवॉइस PDF अपलोड करें, फिर यहाँ मास्टर टेस्ट रन करें।")
        return

    pdf_lines = st.session_state.get("cached_pdf_lines", [])
    pdf_text = st.session_state.get("cached_pdf_text", "")
    pdf_bytes = st.session_state.get("cached_pdf_bytes", None)
    
    shipper_info = st.session_state["shipper_database"].get(selected_shipper, {})
    header_rules = shipper_info.get("mapping_rules", {})
    item_rules = shipper_info.get("item_table_rules", {})
    assigned_parser = shipper_info.get("item_table_rule_name", "parser_welspun").strip().lower()

    if st.button("⚡ Run Master Test for All Rules", type="primary", use_container_width=True):
        master_results = []
        
        # 1. Test Header Rules
        for f_name, f_rule in header_rules.items():
            if f_name.lower() in ["igst status", "igst mode"]:
                continue
                
            ky = f_rule.get("keyword", "")
            pos = f_rule.get("position", "Right (आगे)")
            m_mode = f_rule.get("match_mode", "Exact Word")
            stop_kw = f_rule.get("stop_kw", "")
            final_flt = f_rule.get("filter", "None")
            fb_val = f_rule.get("fallback", "")

            res = extract_header_value(
                pdf_lines, pdf_text, ky, pos, m_mode, stop_kw, final_flt, field_label=f_name, pdf_bytes=pdf_bytes
            )
            
            if not res or not res.strip():
                res = fb_val
                
            master_results.append({
                "Type": "Header Field",
                "Name / Field": f_name,
                "Target Cell / Col": f_rule.get("cell", "N/A"),
                "Source Doc": f_rule.get("logic", "Main Invoice"),
                "Keyword Used": ky if ky else "N/A",
                "Extracted Value": res if res else "❌ Not Found"
            })
        
        # 2. Test Item Table Rules
        for i_name, i_rule in item_rules.items():
            if i_name.lower() in ["igst status", "igst mode"]:
                continue
                
            i_rule_text = i_rule.get("rule", "")
            i_type = i_rule.get("type", "PDF Row Item")
            
            if i_type == "Header Field Mapping":
                h_rule = header_rules.get(i_rule_text, {})
                res = extract_header_value(
                    pdf_lines, pdf_text, h_rule.get("keyword", ""), 
                    h_rule.get("position", ""), h_rule.get("match_mode", ""), 
                    h_rule.get("stop_kw", ""), h_rule.get("filter", ""), 
                    field_label=i_rule_text, pdf_bytes=pdf_bytes
                )
            else:
                res = extract_header_value(
                    pdf_lines, pdf_text, i_rule_text, 
                    "Below (नीचे)", "Exact Word", "", "None", 
                    field_label=i_name, pdf_bytes=pdf_bytes
                )
                
            master_results.append({
                "Type": "Item Column",
                "Name / Field": i_name,
                "Target Cell / Col": i_rule.get("col", "N/A"),
                "Source Doc": i_rule.get("logic", "Main Invoice"),
                "Keyword Used": i_rule_text,
                "Extracted Value": res if res else "❌ Not Found"
            })
        
        if master_results:
            df_master = pd.DataFrame(master_results)
            st.success("🎉 Master Test Completed Successfully!")
            st.dataframe(df_master, use_container_width=True)
        else:
            st.warning("⚠️ जाँचने के लिए कोई रूल्स उपलब्ध नहीं हैं।")
