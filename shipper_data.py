if st.button("💾 Save All AI Mapping Rules to Google Sheet", type="primary", use_container_width=True, key="btn_save_all_sheet"):
                rules_payload = []
                files_payload = []
                
                for s_name, s_data in st.session_state["shipper_database"].items():
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({
                            "ShipperName": s_name, "FieldName": f_name, "Keyword": r_info.get("keyword", ""),
                            "Position": r_info.get("position", "Right (आगे)"), "Cell": r_info.get("cell", ""),
                            "MatchMode": r_info.get("match_mode", "Exact Word"), "StopKw": r_info.get("stop_kw", ""),
                            "Filter": r_info.get("filter", "None"), "Logic": "Main Invoice",
                            "Fallback": r_info.get("fallback", ""),
                            "RuleKind": "header"
                        })
                    for i_field, i_info in s_data.get("item_table_rules", {}).items():
                        rules_payload.append({
                            "ShipperName": s_name, "FieldName": i_field, "Keyword": i_info.get("rule", ""),
                            "Position": "Right (आगे)", "Cell": i_info.get("col", "K"),
                            "MatchMode": i_info.get("type", "PDF Row Item"), "StopKw": "",
                            "Filter": "None", "Logic": "None", "Fallback": "",
                            "RuleKind": "item"
                        })
                    
                    igst_data = s_data.get("igst_config", {})
                    rules_payload.append({
                        "ShipperName": s_name, "FieldName": "lut_keywords", "Keyword": igst_data.get("lut_keywords", ""),
                        "Position": "Right (आगे)", "Cell": "", "MatchMode": "Config", "StopKw": "",
                        "Filter": "None", "Logic": "None", "Fallback": "", "RuleKind": "igst_config"
                    })
                    rules_payload.append({
                        "ShipperName": s_name, "FieldName": "paid_keywords", "Keyword": igst_data.get("paid_keywords", ""),
                        "Position": "Right (आगे)", "Cell": "", "MatchMode": "Config", "StopKw": "",
                        "Filter": "None", "Logic": "None", "Fallback": "", "RuleKind": "igst_config"
                    })
                        
                    tpl_bytes = s_data.get("uploaded_files", {}).get("Full Job Excel Format File", b"")
                    if isinstance(tpl_bytes, bytes) and len(tpl_bytes) > 0:
                        b64_str = base64.b64encode(tpl_bytes).decode('utf-8')
                        files_payload.append({
                            "ShipperName": s_name,
                            "FileBase64": b64_str
                        })
                
                with st.spinner("⏳ गूगल शीट में सुरक्षित सेव हो रहा है..."):
                    success = push_all_to_sheet(rules_payload, files_payload)
                    if success:
                        st.success("🎉 आपके सभी रूल्स, IGST कॉन्फिग और Excel टेम्पलेट गूगल शीट में 100% परमानेंट सेव हो गए हैं!")
                        st.balloons()
                    else:
                        st.error("❌ सेव करते समय एरर आया!")

            render_universal_test_suite(selected_shipper)
