# =========================================================================
    # 🔑 GEMINI API KEY CONFIGURATOR BOX (UI)
    # =========================================================================
    with st.expander("🔑 Gemini API Key Settings (यहाँ अपनी API Key दर्ज करें)", expanded=True):
        current_saved_key = load_gemini_api_key()
        masked_key = "********" + current_saved_key[-4:] if len(current_saved_key) > 4 else ""
        
        st.write(f"वर्तमान स्थिति: {'🟢 API Key सेट है' if current_saved_key else '🔴 API Key सेट नहीं है'}")
        if masked_key:
            st.caption(f"Saved Key: {masked_key}")
            
        new_api_key_input = st.text_input("Gemini API Key दर्ज करें:", value="", type="password", placeholder="AIzaSy...")
        
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            if st.button("💾 Save API Key", type="primary", use_container_width=True):
                if new_api_key_input.strip():
                    if save_gemini_api_key(new_api_key_input.strip()):
                        st.success("🎉 Gemini API Key सफलतापूर्वक सेव हो गई!")
                        st.rerun()
                    else:
                        st.error("एरर: की सेव करने में समस्या आई।")
                else:
                    st.error("कृपया वैध API Key दर्ज करें!")
        with col_k2:
            if st.button("🗑️ Delete API Key", type="secondary", use_container_width=True):
                save_gemini_api_key("")
                st.success("🗑️ API Key डिलीट कर दी गई है!")
                st.rerun()

    st.write("---")
