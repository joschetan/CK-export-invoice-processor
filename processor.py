import streamlit as st
import openpyxl
import pdfplumber
import re
import base64
import os
from io import BytesIO

from item_parser import extract_item_table_rows, map_items_to_excel_dynamic
from shipper_data import fetch_data_from_google_sheet, ensure_default_shipper
from pdf_engine import apply_value_replacement

def apply_strict_rule_filter(raw_text, mode, stop_kw, flt, logic, kw=""):
    if not raw_text: return ""
    text = raw_text.strip()
    if text.startswith(":"): text = text[1:].strip()
    
    if mode == "Word Position" or mode.startswith("Word "):
        w_num = int(stop_kw.strip()) if stop_kw and str(stop_kw).strip().isdigit() else 1
        parts = text.split()
        text = parts[w_num - 1].strip() if len(parts) >= w_num else ""
    elif mode == "After Word" and stop_kw:
        if "=" not in stop_kw and stop_kw.lower() in text.lower():
            start_idx = text.lower().find(stop_kw.lower()) + len(stop_kw)
            text = text[start_idx:].strip()
            if text.startswith(":"): text = text[1:].strip()
    elif mode == "Exact Word":
        parts = text.split()
        text = parts[0].strip() if parts else ""
    elif mode == "Full Line":
        text = text.split("\n")[0].strip()

    # ALL FILTERS IMPLEMENTATION
    if flt in ["Text Inside Parentheses ()", "Inside Parentheses ()"]:
        bracket_match = re.search(r'\((.*?)\)', text)
        text = bracket_match.group(1).strip() if bracket_match else text.strip()
    elif flt == "Letters Only":
        text = re.sub(r'[^A-Za-z\s]', '', text).strip()
    elif flt == "Numbers Only":
        nums = re.findall(r'[\d,.]+', text)
        text = nums[0].strip() if nums else ""
    elif flt == "Clean Date (DD/MM/YYYY)":
        d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', text)
        text = d_match.group(0).replace(".", "/").replace("-", "/") if d_match else text.strip()
    elif flt == "Container Number (ISO Format)":
        cntr_match = re.search(r'\b[A-Za-z]{4}\s*\d{7}\b', text)
        text = cntr_match.group(0).replace(" ", "") if cntr_match else text.strip()

    # APPLY MULTI-CONDITION VALUE REPLACEMENT (FIND=REPLACE)
    if stop_kw and "=" in stop_kw:
        text = apply_value_replacement(text, stop_kw)
    if flt and "=" in flt:
        text = apply_value_replacement(text, flt)

    return text.strip()

def render_processor():
    fetch_data_from_google_sheet()
    ensure_default_shipper()
    
    st.header("📤 Invoice Processing Zone")
    st.caption("रूल्स के आधार पर 100% सटीक डेटा एक्सट्रैक्शन (Multi-Invoice Enabled)।")
    
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
                    
                    # 🎯 TEMPLATE LOADING DIRECTLY FROM GOOGLE SHEET DATA
                    wb = None
                    uploaded_files = shipper_info.get("uploaded_files", {})
                    
                    if "Full Job Excel Format File" in uploaded_files:
                        tpl_bytes = uploaded_files["Full Job Excel Format File"]
                        if isinstance(tpl_bytes, bytes) and len(tpl_bytes) > 100 and tpl_bytes.startswith(b'PK'):
                            try:
                                wb = openpyxl.load_workbook(BytesIO(tpl_bytes))
                            except Exception:
                                wb = None

                    # Fallback to new workbook if no template found
                    if wb is None:
                        wb = openpyxl.Workbook()
                        
                    # Target "INV" sheet
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
                        
                        # Process Header Rules
                        for field, r_info in rules.items():
                            kw = r_info.get("keyword", "").strip()
                            pos = r_info.get("position", "Right (आगे)")
                            target_cell = r_info.get("cell", "").strip().upper()
                            mode = r_info.get("match_mode", "Exact Word")
                            stop_kw = r_info.get("stop_kw", "").strip()
                            flt = r_info.get("filter", "None")
                            
                            raw_text = ""
                            if kw:
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
                                
                            found_val = apply_strict_rule_filter(raw_text, mode, stop_kw, flt, "", kw)
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

                        # MULTI-INVOICE SUMMARY TABLE MAPPING
                        summary_row = 1 + inv_sr_number
                        
                        ws[f"AH{summary_row}"] = inv_sr_number
                        ws[f"AI{summary_row}"] = current_inv_number
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

                        # Process Dynamic Item Rows
                        parsed_items = extract_item_table_rows(pdf_lines)
                        ws, overall_item_sr, excel_write_row = map_items_to_excel_dynamic(
                            ws, parsed_items, item_table_rules,
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
                    st.success(f"🎉 सफलता! कुल {len(uploaded_pdf_files)} इनवॉइस की फ़ाइल '{final_filename}' तैयार है!")
            
            if st.session_state.get("processed_file_ready", None):
                st.download_button(
                    label=f"📥 {st.session_state['processed_file_ready']['filename']} डाउनलोड करें",
                    data=st.session_state["processed_file_ready"]["data"],
                    file_name=st.session_state["processed_file_ready"]["filename"],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.session_state["processed_file_ready"] = None
