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
