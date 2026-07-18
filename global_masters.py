import streamlit as st

def render_global_masters():
    st.header("🌍 Global Masters & Common Dictionaries")
    st.caption("यहाँ अपलोड की गई एक्सेल फाइलें सभी शिपर के इनवॉइसेज पर समान रूप से लागू होंगी।")
    
    # डिक्शनरी के नाम जो हमेशा चाहिए
    predefined_dicts = ["Port of Loading & Discharge Codes", "HS Code & DBK Dictionary", "Rodtep/Rosctl Rules"]
    
    for dict_name in predefined_dicts:
        st.write(f"### 📊 {dict_name}")
        
        # चेक करना कि क्या फाइल पहले से अपलोडेड है
        is_uploaded = dict_name in st.session_state["global_dictionaries"]
        
        if is_uploaded:
            st.success(f"✅ '{dict_name}' डेटाबेस में सुरक्षित सेव्ड है।")
            if st.button(f"🗑️ Delete & Upload Fresh File", key=f"del_global_{dict_name}"):
                del st.session_state["global_dictionaries"][dict_name]
                st.rerun()
        else:
            g_file = st.file_uploader(f"नया/अपडेटेड Excel अपलोड करें: {dict_name}", type=["xlsx", "xls"], key=f"upload_global_{dict_name}")
            if g_file:
                st.session_state["global_dictionaries"][dict_name] = g_file.getvalue()
                st.success(f"🎉 {dict_name} सफलतापूर्वक ग्लोबल मास्टर में सेव हो गया!")
                st.rerun()
        st.write("---")
