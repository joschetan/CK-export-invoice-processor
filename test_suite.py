import streamlit as st
import pdfplumber
import re
import pandas as pd
from pdf_engine import extract_header_value, apply_value_replacement
from parser_welspun import extract_welspun_items
from parser_bkt import extract_bkt_items

def render_universal_test_suite(selected_shipper):
    st.markdown("---")
    st.header("🚀 Comprehensive Test Suite & Validator")
    st.caption("एक क्लिक में सभी हेडर और आइटम रूल्स को रन करें या नीचे 'Pick Value' से लाइव पीडीएफ टेक्स्ट चुनकर विजुअली टेस्ट करें।")

    if "cached_pdf_lines" not in st.session_state or not st.session_state["cached_pdf_lines"]:
        st.info("💡 कृपया पहले Section 2 में अपनी इनवॉइस PDF अपलोड करें, फिर यहाँ टेस्ट रन करें।")
        return

    pdf_lines = st.session_state.get("cached_pdf_lines", [])
    pdf_text = st.session_state.get("cached_pdf_text", "")
    pdf_bytes = st.session_state.get("cached_pdf_bytes", None)
    
    shipper_info = st.session_state["shipper_database"].get(selected_shipper, {})
    header_rules = shipper_info.get("mapping_rules", {})
    item_rules = shipper_info.get("item_table_rules", {})
    assigned_parser = shipper_info.get("item_table_rule_name", "parser_welspun").strip().lower()

    # 🔍 NEW FEATURE: Visual Text Inspector & "Pick Value" Selector
    with st.expander("🎯 Visual 'Pick Value' Inspector (PDF से सीधे वैल्यू चुनें)", expanded=False):
        st.markdown("अपलोड की गई PDF के अंदर के मुख्य शब्द नीचे दिए गए हैं। आप यहाँ से वैल्यू देखकर कीवर्ड या रूल बना सकते हैं:")
        try:
            if pdf_bytes:
                with pdfplumber.open(io.BytesIO(pdf_bytes) if 'io' in globals() else BytesIO(pdf_bytes)) as pdf_picker:
                    picker_words = pdf_picker.pages[0].extract_words()
                    word_list = [w['text'] for w in picker_words if len(w['text'].strip()) > 1]
                    
                    selected_picked_val = st.selectbox("📌 Pick Value from PDF Text:", options=["-- सिलेक्ट करें --"] + sorted(list(set(word_list))), key="pick_val_dropdown")
                    if selected_picked_val and selected_picked_val != "-- सिलेक्ट करें --":
                        st.info(f"💡 आपने चुनी है वैल्यू: `{selected_picked_val}` (इसे कॉपी करके अपने कीवर्ड या रूल में इस्तेमाल कर सकते हैं)")
        except Exception:
            # Fallback agar io module missing ho
            all_words_flat = [w for line in pdf_lines for w in line.split() if len(w) > 1]
            selected_picked_val = st.selectbox("📌 Pick Value from PDF Lines:", options=["-- सिलेक्ट करें --"] + sorted(list(set(all_words_flat))), key="pick_val_dropdown_fallback")
            if selected_picked_val and selected_picked_val != "-- सिलेक्ट करें --":
                st.info(f"💡 चुनी गई वैल्यू: `{selected_picked_val}`")

    if st.button("🚀 Run Comprehensive Test Suite", type="primary", use_container_width=True, key="btn_comprehensive_test_suite"):
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
        
        # 2. Test Item Table Rules[cite: 10]
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
            st.success("🎉 Test Suite Completed Successfully!")
            st.dataframe(df_master, use_container_width=True)
        else:
            st.warning("⚠️ जाँचने के लिए कोई रूल्स उपलब्ध नहीं हैं।")
