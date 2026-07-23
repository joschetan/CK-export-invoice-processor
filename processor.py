import streamlit as st
import openpyxl
import pdfplumber
import re
import base64
import os
from io import BytesIO

from item_parser import extract_item_table_rows, map_items_to_excel_dynamic[cite: 2]
from shipper_data import fetch_data_from_google_sheet, ensure_default_shipper[cite: 2]
from pdf_engine import apply_value_replacement[cite: 2]

DEFAULT_TEMPLATE_PATH = "template.xlsx"  # Project root directory template

def apply_strict_rule_filter(raw_text, mode, stop_kw, flt, logic, kw=""):[cite: 2]
    if not raw_text: return ""[cite: 2]
    text = raw_text.strip()[cite: 2]
    if text.startswith(":"): text = text[1:].strip()[cite: 2]
    
    if mode == "Word Position" or mode.startswith("Word "):[cite: 2]
        w_num = int(stop_kw.strip()) if stop_kw and str(stop_kw).strip().isdigit() else 1[cite: 2]
        parts = text.split()[cite: 2]
        text = parts[w_num - 1].strip() if len(parts) >= w_num else ""[cite: 2]
    elif mode == "After Word" and stop_kw:[cite: 2]
        if "=" not in stop_kw and stop_kw.lower() in text.lower():[cite: 2]
            start_idx = text.lower().find(stop_kw.lower()) + len(stop_kw)[cite: 2]
            text = text[start_idx:].strip()[cite: 2]
            if text.startswith(":"): text = text[1:].strip()[cite: 2]
    elif mode == "Exact Word":[cite: 2]
        parts = text.split()[cite: 2]
        text = parts[0].strip() if parts else ""[cite: 2]
    elif mode == "Full Line":[cite: 2]
        text = text.split("\n")[0].strip()[cite: 2]

    # ALL FILTERS IMPLEMENTATION
    if flt in ["Text Inside Parentheses ()", "Inside Parentheses ()"]:[cite: 2]
        bracket_match = re.search(r'\((.*?)\)', text)[cite: 2]
        text = bracket_match.group(1).strip() if bracket_match else text.strip()[cite: 2]
    elif flt == "Letters Only":[cite: 2]
        text = re.sub(r'[^A-Za-z\s]', '', text).strip()[cite: 2]
    elif flt == "Numbers Only":[cite: 2]
        nums = re.findall(r'[\d,.]+', text)[cite: 2]
        text = nums[0].strip() if nums else ""[cite: 2]
    elif flt == "Clean Date (DD/MM/YYYY)":[cite: 2]
        d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', text)[cite: 2]
        text = d_match.group(0).replace(".", "/").replace("-", "/") if d_match else text.strip()[cite: 2]
    elif flt == "Container Number (ISO Format)":[cite: 2]
        cntr_match = re.search(r'\b[A-Za-z]{4}\s*\d{7}\b', text)[cite: 2]
        text = cntr_match.group(0).replace(" ", "") if cntr_match else text.strip()[cite: 2]

    # APPLY MULTI-CONDITION VALUE REPLACEMENT (FIND=REPLACE)
    if stop_kw and "=" in stop_kw:[cite: 2]
        text = apply_value_replacement(text, stop_kw)[cite: 2]
    if flt and "=" in flt:[cite: 2]
        text = apply_value_replacement(text, flt)[cite: 2]

    return text.strip()[cite: 2]

def render_processor():[cite: 2]
    fetch_data_from_google_sheet()[cite: 2]
    ensure_default_shipper()[cite: 2]
    
    st.header("📤 Invoice Processing Zone")[cite: 2]
    st.caption("रूल्स के आधार पर 100% सटीक डेटा एक्सट्रैक्शन (Multi-Invoice Enabled)।")[cite: 2]
    
    shippers_list = list(st.session_state["shipper_database"].keys())[cite: 2]
    
    if shippers_list:[cite: 2]
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=0)[cite: 2]
        
        if selected_shipper:[cite: 2]
            shipper_info = st.session_state["shipper_database"][selected_shipper][cite: 2]
            
            if f"inv_count_{selected_shipper}" not in st.session_state:[cite: 2]
                st.session_state[f"inv_count_{selected_shipper}"] = 1[cite: 2]
            
            inv_count = st.session_state[f"inv_count_{selected_shipper}"][cite: 2]
            
            st.subheader("📑 Upload Invoices (PDFs)")[cite: 2]
            
            uploaded_pdf_files = [][cite: 2]
            for i in range(inv_count):[cite: 2]
                pdf_f = st.file_uploader(f"➡️ Invoice #{i+1} का PDF अपलोड करें", type=["pdf"], key=f"inv_pdf_{selected_shipper}_{i}")[cite: 2]
                if pdf_f:[cite: 2]
                    uploaded_pdf_files.append((i+1, pdf_f))[cite: 2]
            
            col_b1, col_b2, col_space = st.columns([2, 2, 6])[cite: 2]
            with col_b1:[cite: 2]
                if inv_count < 10:[cite: 2]
                    if st.button("➕ Add Invoice", key=f"add_btn_{selected_shipper}", use_container_width=True):[cite: 2]
                        st.session_state[f"inv_count_{selected_shipper}"] += 1[cite: 2]
                        st.rerun()[cite: 2]
            with col_b2:[cite: 2]
                if inv_count > 1:[cite: 2]
                    if st.button("➖ Remove Last", key=f"rem_btn_{selected_shipper}", use_container_width=True):[cite: 2]
                        st.session_state[f"inv_count_{selected_shipper}"] -= 1[cite: 2]
                        st.rerun()[cite: 2]
                        
            st.write("---")[cite: 2]
            
            if uploaded_pdf_files and st.button("🚀 Process & Generate Excel", type="primary", use_container_width=True):[cite: 2]
                with st.spinner(f"कुल {len(uploaded_pdf_files)} इनवॉइस प्रोसेस हो रहे हैं..."):[cite: 2]
                    rules = shipper_info.get("mapping_rules", {})[cite: 2]
                    item_table_rules = shipper_info.get("item_table_rules", {})[cite: 2]
                    
                    igst_cfg = shipper_info.get("igst_config", {})[cite: 2]
                    lut_kws = igst_cfg.get("lut_keywords", "")[cite: 2]
                    paid_kws = igst_cfg.get("paid_keywords", "")[cite: 2]
                    
                    # 🎯 100% SOLID TEMPLATE LOADING PRIORITY
                    wb = None
                    uploaded_files = shipper_info.get("uploaded_files", {})[cite: 2]
                    
                    # 1. Try from Session Memory (if user uploaded in tab 1)
                    if "Full Job Excel Format File" in uploaded_files:[cite: 2]
                        tpl_bytes = uploaded_files["Full Job Excel Format File"]
                        if isinstance(tpl_bytes, bytes) and len(tpl_bytes) > 100 and tpl_bytes.startswith(b'PK'):
                            try:
                                wb = openpyxl.load_workbook(BytesIO(tpl_bytes))
                            except Exception:
                                wb = None

                    # 2. Try from Local Project Template File
                    if wb is None and os.path.exists(DEFAULT_TEMPLATE_PATH):
                        try:
                            wb = openpyxl.load_workbook(DEFAULT_TEMPLATE_PATH)
                        except Exception:
                            wb = None

                    # 3. Fallback to blank workbook if neither exists
                    if wb is None:
                        wb = openpyxl.Workbook()[cite: 2]
                        
                    # Target "INV" sheet
                    ws = wb["INV"] if "INV" in wb.sheetnames else wb.active[cite: 2]
                    
                    first_inv_no = "INV"[cite: 2]
                    overall_item_sr = 1[cite: 2]
                    excel_write_row = 2[cite: 2]
                    
                    for inv_sr_number, inv_file in uploaded_pdf_files:[cite: 2]
                        pdf_text = ""[cite: 2]
                        pdf_lines = [][cite: 2]
                        with pdfplumber.open(inv_file) as pdf:[cite: 2]
                            for page in pdf.pages:[cite: 2]
                                t = page.extract_text()[cite: 2]
                                if t:[cite: 2]
                                    pdf_text += t + "\n"[cite: 2]
                                    pdf_lines.extend(t.split("\n"))[cite: 2]
                        
                        current_inv_number = f"INV_{inv_sr_number}"[cite: 2]
                        current_inv_date = ""[cite: 2]
                        inv_data_dict = {}[cite: 2]
                        
                        # Process Header Rules
                        for field, r_info in rules.items():[cite: 2]
                            kw = r_info.get("keyword", "").strip()[cite: 2]
                            pos = r_info.get("position", "Right (आगे)")[cite: 2]
                            target_cell = r_info.get("cell", "").strip().upper()[cite: 2]
                            mode = r_info.get("match_mode", "Exact Word")[cite: 2]
                            stop_kw = r_info.get("stop_kw", "").strip()[cite: 2]
                            flt = r_info.get("filter", "None")[cite: 2]
                            
                            raw_text = ""[cite: 2]
                            if kw:[cite: 2]
                                for line_i, line in enumerate(pdf_lines):[cite: 2]
                                    if kw.lower() in line.lower():[cite: 2]
                                        if pos == "Right (आगे)":[cite: 2]
                                            start_idx = line.lower().find(kw.lower()) + len(kw)[cite: 2]
                                            raw_text = line[start_idx:].strip()[cite: 2]
                                            if raw_text.startswith(":"): raw_text = raw_text[1:].strip()[cite: 2]
                                            if raw_text: break[cite: 2]
                                        elif pos == "Below (नीचे)":[cite: 2]
                                            if line_i + 1 < len(pdf_lines):[cite: 2]
                                                raw_text = pdf_lines[line_i + 1].strip()[cite: 2]
                                                if raw_text: break[cite: 2]
                            else:
                                raw_text = pdf_text[cite: 2]
                                
                            found_val = apply_strict_rule_filter(raw_text, mode, stop_kw, flt, "", kw)[cite: 2]
                            inv_data_dict[field.lower()] = found_val[cite: 2]
                            
                            if target_cell:[cite: 2]
                                if target_cell.isalpha():[cite: 2]
                                    dynamic_cell = f"{target_cell}{1 + inv_sr_number}"[cite: 2]
                                    ws[dynamic_cell] = found_val[cite: 2]
                                elif len(target_cell) >= 2 and target_cell[1].isdigit():[cite: 2]
                                    if inv_sr_number == 1:[cite: 2]
                                        ws[target_cell] = found_val[cite: 2]
                            
                            if "inv. no" in field.lower() or "invoice no" in field.lower():[cite: 2]
                                if found_val:[cite: 2]
                                    current_inv_number = found_val[cite: 2]
                                    if inv_sr_number == 1: first_inv_no = found_val[cite: 2]
                            
                            if "date" in field.lower() or "dt" in field.lower():[cite: 2]
                                d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', found_val)[cite: 2]
                                if d_match:[cite: 2]
                                    current_inv_date = d_match.group(0).replace(".", "/").replace("-", "/")[cite: 2]
                                elif found_val and not found_val.lower().startswith("inv"):[cite: 2]
                                    current_inv_date = found_val[cite: 2]

                        # MULTI-INVOICE SUMMARY TABLE MAPPING
                        summary_row = 1 + inv_sr_number[cite: 2]
                        
                        ws[f"AH{summary_row}"] = inv_sr_number[cite: 2]
                        ws[f"AI{summary_row}"] = current_inv_number[cite: 2]
                        ws[f"AJ{summary_row}"] = current_inv_date[cite: 2]
                        
                        for f_key, f_val in inv_data_dict.items():[cite: 2]
                            fk = f_key.lower()[cite: 2]
                            if "terms" in fk or "cif" in fk or "fob" in fk or "incoterm" in fk: ws[f"AK{summary_row}"] = f_val[cite: 2]
                            elif "currency" in fk or "curr" in fk: ws[f"AL{summary_row}"] = f_val[cite: 2]
                            elif "freight" in fk: ws[f"AM{summary_row}"] = f_val[cite: 2]
                            elif "insurance" in fk: ws[f"AN{summary_row}"] = f_val[cite: 2]
                            elif "commission" in fk: ws[f"AO{summary_row}"] = f_val[cite: 2]
                            elif "discount" in fk: ws[f"AP{summary_row}"] = f_val[cite: 2]
                            elif "packaging" in fk or "misc" in fk: ws[f"AQ{summary_row}"] = f_val[cite: 2]
                            elif "deduction" in fk or "other" in fk: ws[f"AR{summary_row}"] = f_val[cite: 2]
                            elif "contract" in fk or "exp" in fk: ws[f"AS{summary_row}"] = f_val[cite: 2]
                            elif "lut" in fk: ws[f"AT{summary_row}"] = f_val[cite: 2]

                        # Process Dynamic Item Rows
                        parsed_items = extract_item_table_rows(pdf_lines)[cite: 2]
                        ws, overall_item_sr, excel_write_row = map_items_to_excel_dynamic([cite: 2]
                            ws, parsed_items, item_table_rules,[cite: 2]
                            inv_sr_no=inv_sr_number, [cite: 2]
                            start_overall_sr=overall_item_sr, [cite: 2]
                            start_excel_row=excel_write_row, [cite: 2]
                            default_invoice_no=current_inv_number, [cite: 2]
                            default_invoice_date=current_inv_date,[cite: 2]
                            pdf_text=pdf_text,[cite: 2]
                            lut_kws=lut_kws,[cite: 2]
                            paid_kws=paid_kws[cite: 2]
                        )[cite: 2]

                    output = BytesIO()[cite: 2]
                    wb.save(output)[cite: 2]
                    
                    short_shipper = selected_shipper.split(" ")[0].lower()[cite: 2]
                    clean_inv = re.sub(r'[\\/*?:"<>|]', "", first_inv_no)[cite: 2]
                    final_filename = f"{clean_inv}_{short_shipper}_MultiInv.xlsx"[cite: 2]
                    
                    st.session_state["processed_file_ready"] = {"filename": final_filename, "data": output.getvalue()}[cite: 2]
                    st.success(f"🎉 सफलता! कुल {len(uploaded_pdf_files)} इनवॉइस की फ़ाइल '{final_filename}' तैयार है!")[cite: 2]
            
            if st.session_state.get("processed_file_ready", None):[cite: 2]
                st.download_button([cite: 2]
                    label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",[cite: 2]
                    data=st.session_state["processed_file_ready"]["data"],[cite: 2]
                    file_name=st.session_state["processed_file_ready"]["filename"],[cite: 2]
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"[cite: 2]
                )[cite: 2]
                st.session_state["processed_file_ready"] = None[cite: 2]
