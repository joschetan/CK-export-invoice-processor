import streamlit as st
import os
import json
from io import BytesIO
from ai_engine import (
    ask_local_ai, load_gemini_api_key_from_sheet, 
    update_parser_file_on_github, save_github_pat_to_sheet, load_github_pat_from_sheet
)

def get_parser_file_path(parser_rule_name):
    clean_name = str(parser_rule_name).strip().lower()
    if not clean_name.endswith(".py"):
        clean_name += ".py"
    if os.path.exists(clean_name):
        return clean_name
    return None

def render_ai_parser_agent_ui(selected_shipper, shipper_info):
    st.markdown("---")
    st.subheader("🤖 AI Parser Code & Rule Assistant (Gemini-Powered)")
    st.caption("इस शिपर के पार्सर और रूल्स को सीधे Gemini AI से बातचीत करके, PDF और स्क्रीनशॉट (SS) दिखाकर अपडेट करें।")
    
    # ⚡ 1-Click Connection Test Button (Gemini API Key Check)
    with st.container():
        col_t1, col_t2 = st.columns([1, 3])
        with col_t1:
            if st.button("⚡ Test AI Connection", key=f"top_test_btn_{selected_shipper}", type="secondary"):
                saved_key = load_gemini_api_key_from_sheet()
                if saved_key:
                    st.session_state["ai_tested"] = True
                else:
                    st.session_state["ai_tested"] = False
                st.session_state["ai_status_checked"] = True
        with col_t2:
            if st.session_state.get("ai_status_checked", False):
                if st.session_state.get("ai_tested", False):
                    st.success("✅ Gemini API Key एक्टिव और कनेक्टेड है!")
                else:
                    st.error("❌ कनेक्शन फेल! कृपया ऊपर सेटिंग्स में जाकर Gemini API Key दर्ज करें।")

    current_parser_name = shipper_info.get("item_table_rule_name", "parser_welspun")
    parser_file_path = get_parser_file_path(current_parser_name)
    
    # 🔑 Google Sheet Synced GitHub PAT Management
    with st.expander("🔑 GitHub Personal Access Token (PAT) Settings", expanded=False):
        saved_pat = load_github_pat_from_sheet()
        if saved_pat:
            st.write("वर्तमान स्थिति: 🟢 Google Sheet पर GitHub PAT सेट है")
        else:
            st.write("वर्तमान स्थिति: 🔴 GitHub PAT सेट नहीं है")
            
        input_pat = st.text_input("GitHub PAT दर्ज करें:", value=saved_pat, type="password", key=f"gha_pat_input_{selected_shipper}", placeholder="ghp_...")
        if st.button("💾 Save PAT to Google Sheet", type="primary", key=f"save_pat_btn_{selected_shipper}"):
            if input_pat.strip() and save_github_pat_to_sheet(input_pat.strip()):
                st.success("🎉 GitHub PAT गूगल शीट पर सफलतापर्वक सेव हो गया!")
                st.rerun()

    # 📸 स्क्रीनशॉट / इमेज अपलोड करने का विजुअल बॉक्स
    col_up1, col_up2 = st.columns([2, 1])
    with col_up1:
        uploaded_ss = st.file_uploader(
            "📷 इनवॉइस या एरर का स्क्रीनशॉट (PNG, JPG) यहाँ अपलोड करें:", 
            type=["png", "jpg", "jpeg", "webp"], 
            key=f"ai_ss_upload_{selected_shipper}"
        )
    with col_up2:
        if uploaded_ss:
            st.image(uploaded_ss, caption="Attached SS", width=150)
    
    chat_key = f"ai_chat_history_{selected_shipper}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {"role": "assistant", "content": f"नमस्ते! मैं आपका Gemini AI पार्सर एजेंट हूँ। वर्तमान शिपर **'{selected_shipper}'** के लिए एक्टिव पार्सर फाइल **`{current_parser_name}.py`** है। आप ऊपर स्क्रीनशॉट अपलोड कर सकते हैं या सीधे चैट में निर्देश दे सकते हैं।"}]
        
    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    user_prompt = st.chat_input(f"Gemini से बोलें (उदा: कॉलम I और J में इनवॉइस नंबर/डेट गलत आ रही है, पार्सर कोड सुधारो)...", key=f"chat_input_{selected_shipper}")
    
    # Session state to hold AI generated code block for editing/viewing box
    code_box_key = f"ai_generated_code_{selected_shipper}"
    if code_box_key not in st.session_state:
        st.session_state[code_box_key] = ""
        if parser_file_path and os.path.exists(parser_file_path):
            try:
                with open(parser_file_path, "r", encoding="utf-8") as f:
                    st.session_state[code_box_key] = f.read()
            except:
                pass

    if user_prompt:
        st.session_state[chat_key].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.write(user_prompt)
            if uploaded_ss:
                st.image(uploaded_ss, width=250)
            
        with st.spinner("Gemini AI पार्सर फाइल और आपके डेटा का विश्लेषण कर रहा है..."):
            parser_code_content = st.session_state[code_box_key]
                    
            cached_pdf_text = st.session_state.get("cached_pdf_text", "कोई PDF टेस्ट के लिए अपलोड नहीं की गई है।")
            shipper_context = json.dumps(shipper_info, indent=2)
            
            system_prompt = f"""
            You are an expert Python and Streamlit Developer assisting an Indian Customs Export Automation project.
            You are editing the parser file for shipper: '{selected_shipper}'.
            Current active parser file path: '{parser_file_path}'
            
            Here is the current content of the parser file:
            ```python
            {parser_code_content}
            ```
            
            Here is the text extracted from the sample PDF:
            -----------------------------------------
            {cached_pdf_text[:3000]}
            -----------------------------------------
            
            Here are the current mapping rules and configuration for this shipper:
            {shipper_context}
            
            Your job is to understand the user's request, write robust Python code / Regex matching logic that pdfplumber and python regex can execute reliably without failing, and provide:
            1. A clear explanation of what was changed.
            2. The complete updated Python code block wrapped in ```python ... ```.
            """
            
            messages_for_ai = [
                {"role": "system", "content": system_prompt},
                *st.session_state[chat_key]
            ]
            
            ai_response = ask_local_ai(messages_for_ai)
            if not ai_response:
                ai_response = "माफ़ कीजिए, अभी Gemini API से संपर्क नहीं हो पा रहा है। कृपया अपनी API Key जांचें।"
                
            st.session_state[chat_key].append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.write(ai_response)
                
            # Extract code block and update session state for the box
            if "```python" in ai_response:
                parts = ai_response.split("```python")
                if len(parts) > 1:
                    code_block = parts[1].split("```")[0].strip()
                    st.session_state[code_box_key] = code_block

    # 🛠️ Dedicated Code / Regex Inspection & Edit Box
    st.markdown("---")
    st.subheader("🛠️ AI Generated Parser Code / Regex Inspector Box")
    st.caption("AI द्वारा सुधारा गया या जनरेट किया गया यह कोड सीधे यहाँ दिखेगा। आप इसमें बदलाव भी कर सकते हैं और नीचे दिए गए बटन से सेव कर सकते हैं।")
    
    edited_code_input = st.text_area(
        "Parser Code & Regex Logic:", 
        value=st.session_state[code_box_key], 
        height=300, 
        key=f"text_area_code_{selected_shipper}"
    )
    st.session_state[code_box_key] = edited_code_input

    if parser_file_path and st.button("💾 Apply & Save to Local & GitHub", type="primary", key=f"save_ai_code_{selected_shipper}"):
        try:
            code_block = st.session_state[code_box_key].strip()
            if code_block:
                # 1. Local Machine पर सेव करना
                with open(parser_file_path, "w", encoding="utf-8") as pf:
                    pf.write(code_block)
                
                # 2. सीधे गूगल शीट से फेच किया गया PAT उपयोग करके GitHub पर पुश करना
                active_pat = load_github_pat_from_sheet()
                if active_pat.strip():
                    success, msg = update_parser_file_on_github(current_parser_name, code_block, active_pat.strip())
                    if success:
                        st.success(f"🎉 सफलता! लोकल फाइल और GitHub दोनों जगह कोड अपडेट हो गया है! ({msg})")
                    else:
                        st.warning(f"⚠️ लोकल सेव हो गया, लेकिन GitHub अपडेट में एरर: {msg}")
                else:
                    st.success(f"🎉 सफलता! फाइल `{parser_file_path}` में नया कोड लोकल रूप से सेव हो गया है (Google Sheet पर GitHub PAT सेट नहीं है)।")
            else:
                st.error("❌ कोड बॉक्स खाली है!")
        except Exception as e:
            st.error(f"फाइल सेव करने में एरर: {str(e)}")
