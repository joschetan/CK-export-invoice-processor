import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

from item_parser import extract_item_table_rows, map_items_to_excel_dynamic
from shipper_data import fetch_data_from_google_sheet, ensure_default_shipper
from pdf_engine import apply_rule_filter
from google_sheet_sync import load_template_from_sheet

def render_processor():
    fetch_data_from_google_sheet()
    ensure_default_shipper()
    
    st.header("📤 Invoice Processing Zone")
    st.caption("रूल्स और हेडर-वाइज फॉलबैक के आधार पर 100% सटीक डेटा एक्सट्रैक्शन[cite: 5].")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=0)
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            if f"inv_count_{selected_shipper}" not in st.session_state:
                st.session_state[f"inv_count_{selected_shipper}"] = 1
            
            inv_count = st.session_state[f"inv_count_{selected_shipper}"]
            
            st.subheader("📑 Upload Invoices (PDFs)")
            
            uploaded_pdf_files = []
            for i in range(inv_count):
                pdf_f = st.file_uploader(f"➡️ Invoice #{i+1} का PDF अपलोड करें", type=["pdf"], key=f"inv_pdf_{selected_shipper}_{i}")
                if pdf_f:
                    uploaded_pdf_files.append((i+1, pdf_f))
            
            col_b1, col_b2, col_space = st.columns([2, 2, 6])
            with col_b1:
                if inv_count < 10:
                    if st.button("➕ Add Invoice", key=f"add_btn_{selected_shipper}", use_container_width=True):
                        st.session_state[f"inv_count_{selected_shipper}"] += 1
                        st.rerun()
            with col_b2:
                if inv_count > 1:
                    if st.button("➖ Remove Last", key=f"rem_btn_{selected_shipper}", use_container_width=True):
                        st.session_state[f"inv_count_{selected_shipper}"] -= 1
                        st.rerun()
                        
            st.write("---")
            
            if uploaded_pdf_files and st.button("🚀 Process & Generate Excel", type="primary", use_container_width=True):
                with st.spinner(f"कुल {len(uploaded_pdf_files)} इनवॉइस प्रोसेस हो रहे हैं..."):
                    rules = shipper_info.get("mapping_rules", {})
                    item_table_rules = shipper_info.get("item_table_rules", {})
                    
                    igst_cfg = shipper_info.get("igst_config", {})
                    lut_kws = igst_cfg.get("lut_keywords", "")
                    paid_kws = igst_cfg.get("paid_keywords", "")
                    
                    wb = load_template_from_sheet(selected_shipper)
                    
                    if wb is None:
                        wb = openpyxl.Workbook()
                        
                    ws = wb["INV"] if "INV" in wb.sheetnames else wb.active
                    
                    first_inv_no = "INV"
                    overall_item_sr = 1
                    excel_write_row = 2
                    
                    for inv_sr_number, inv_file in uploaded_pdf_files:
                        pdf_text = ""
                        pdf_lines = []
                        with pdfplumber.open(inv_file) as pdf:
                            for page in pdf.pages:
                                t = page.extract_text()
                                if t:
                                    pdf_text += t + "\n"
                                    pdf_lines.extend(t.split("\n"))
                        
                        current_inv_number = f"INV_{inv_sr_number}"
                        current_inv_date = ""
                        inv_data_dict = {}
                        
                        for field, r_info in rules.items():
                            kw = r_info.get("keyword", "").strip()
                            if kw.startswith("'") and len(kw) > 1:
                                kw = kw[1:].strip()
                                
                            pos = r_info.get("position", "Right (आगे)")
                            target_cell = r_info.get("cell", "").strip().upper()
                            mode = r_info.get("match_mode", "Exact Word")
                            stop_kw = r_info.get("stop_kw", "").strip()
                            flt = r_info.get("filter", "None")
                            fallback_val = r_info.get("fallback", "").strip()
                            
                            raw_text = ""
                            if flt == "Exact Keyword Paste (If Found)":
                                raw_text = pdf_text
                            elif kw:
                                for line_i, line in enumerate(pdf_lines):
                                    if kw.lower() in line.lower():
                                        if pos == "Right (आगे)":
                                            start_idx = line.lower().find(kw.lower()) + len(kw)
                                            raw_text = line[start_idx:].strip()
                                            if raw_text.startswith(":"): raw_text = raw_text[1:].strip()
                                            if raw_text: break
                                        elif pos == "Below (नीचे)":
                                            if line_i + 1 < len(pdf_lines):
                                                raw_text = pdf_lines[line_i + 1].strip()
                                                if raw_text: break
                            else:
                                raw_text = pdf_text
                                
                            # 🎯 अब यहाँ सीधे pdf_engine का यूनिफाइड apply_rule_filter इस्तेमाल हो रहा है
                            found_val = apply_rule_filter(raw_text, mode, stop_kw, flt, kw)
                            
                            if not found_val or not found_val.strip():
                                if fallback_val:
                                    found_val = fallback_val
                                    
                            inv_data_dict[field.lower()] = found_val
                            
                            if target_cell:
                                if target_cell.isalpha():
                                    dynamic_cell = f"{target_cell}{1 + inv_sr_number}"
                                    ws[dynamic_cell] = found_val
                                elif len(target_cell) >= 2 and target_cell[1].isdigit():
                                    if inv_sr_number == 1:
                                        ws[target_cell] = found_val
                            
                            if "inv. no" in field.lower() or "invoice no" in field.lower():
                                if found_val:
                                    current_inv_number = found_val
                                    if inv_sr_number == 1: first_inv_no = found_val
                            
                            if "date" in field.lower() or "dt" in field.lower():
                                d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', found_val)
                                if d_match:
                                    current_inv_date = d_match.group(0).replace(".", "/").replace("-", "/")
                                elif found_val and not found_val.lower().startswith("inv"):
                                    current_inv_date = found_val

                        resolved_item_rules = {}
                        for i_name, i_info in item_table_rules.items():
                            i_type = i_info.get("type", "")
                            i_rule = i_info.get("rule", "")
                            if i_rule.startswith("'") and len(i_rule) > 1:
                                i_rule = i_rule[1:].strip()
                                
                            i_col = i_info.get("col", "K")
                            
                            actual_rule_val = i_rule
                            if i_type == "Header Field Mapping":
                                matched_header_key = i_rule.lower()
                                if matched_header_key in inv_data_dict:
                                    actual_rule_val = inv_data_dict[matched_header_key]
                                else:
                                    for h_k, h_v in inv_data_dict.items():
                                        if h_k.lower() == matched_header_key:
                                            actual_rule_val = h_v
                                            break
                            
                            resolved_item_rules[i_name] = {
                                "col": i_col,
                                "type": i_type if i_type != "Header Field Mapping" else "Constant Text",
                                "rule": actual_rule_val
                            }

                        summary_row = 1 + inv_sr_number
                        ws[f"AH{summary_row}"] = inv_sr_number
                        ws[f"AI{summary_row}"] = current_inv_number
                        
                        if current_inv_date:
                            ws[f"AJ{summary_row}"] = current_inv_date
                        
                        for f_key, f_val in inv_data_dict.items():
                            fk = f_key.lower()
                            if "terms" in fk or "cif" in fk or "fob" in fk or "incoterm" in fk: ws[f"AK{summary_row}"] = f_val
                            elif "currency" in fk or "curr" in fk: ws[f"AL{summary_row}"] = f_val
                            elif "freight" in fk: ws[f"AM{summary_row}"] = f_val
                            elif "insurance" in fk: ws[f"AN{summary_row}"] = f_val
                            elif "commission" in fk: ws[f"AO{summary_row}"] = f_val
                            elif "discount" in fk: ws[f"AP{summary_row}"] = f_val
                            elif "packaging" in fk or "misc" in fk: ws[f"AQ{summary_row}"] = f_val
                            elif "deduction" in fk or "other" in fk: ws[f"AR{summary_row}"] = f_val
                            elif "contract" in fk or "exp" in fk: ws[f"AS{summary_row}"] = f_val
                            elif "lut" in fk: ws[f"AT{summary_row}"] = f_val

                        parsed_items = extract_item_table_rows(pdf_lines)
                        ws, overall_item_sr, excel_write_row = map_items_to_excel_dynamic(
                            ws, parsed_items, resolved_item_rules,
                            inv_sr_no=inv_sr_number, 
                            start_overall_sr=overall_item_sr, 
                            start_excel_row=excel_write_row, 
                            default_invoice_no=current_inv_number, 
                            default_invoice_date=current_inv_date,
                            pdf_text=pdf_text,
                            lut_kws=lut_kws,
                            paid_kws=paid_kws
                        )

                    output = BytesIO()
                    wb.save(output)
                    
                    short_shipper = selected_shipper.split(" ")[0].lower()
                    clean_inv = re.sub(r'[\\/*?:"<>|]', "", first_inv_no)
                    final_filename = f"{clean_inv}_{short_shipper}_MultiInv.xlsx"
                    
                    st.session_state["processed_file_ready"] = {"filename": final_filename, "data": output.getvalue()}
                    st.success(f"🎉 सफलता! कुल {len(uploaded_pdf_files)} इनवॉइस की फ़ाइल '{final_filename}' तैयार है[cite: 5]!")
            
            if st.session_state.get("processed_file_ready", None):
                st.download_button(
                    label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                    data=st.session_state['processed_file_ready']['data'],
                    file_name=st.session_state['processed_file_ready']['filename'],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.session_state["processed_file_ready"] = None
