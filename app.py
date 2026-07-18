import streamlit as st
from global_masters import render_global_masters
from manage_buttons import render_manage_buttons
from master_data import render_master_data
from processor import render_processor

st.set_page_config(page_title="CK Export Invoice Processor", layout="wide")

PASSWORD = "admin" 

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.subheader("🔒 CK Export Invoice Processor - Login")
    pwd = st.text_input("कृपया पासवर्ड दर्ज करें:", type="password")
    if st.button("लॉगिन करें"):
        if pwd == PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("गलत पासवर्ड! कृपया दोबारा प्रयास करें।")
else:
    # --- सेंट्रलाइज्ड डेटाबेस स्ट्रक्चर ---
    if "shipper_database" not in st.session_state:
        st.session_state["shipper_database"] = {}
    if "master_types" not in st.session_state:
        st.session_state["master_types"] = ["Full Job Excel Format File", "DEEC File", "Packing List"]
    if "global_dictionaries" not in st.session_state:
        st.session_state["global_dictionaries"] = {}
    if "processed_file_ready" not in st.session_state:
        st.session_state["processed_file_ready"] = None

    st.title("🚢 CK Export Invoice Processor Pro")
    st.write("---")

    # --- मुख्य मेनू (सिर्फ 2 बड़े बटन) ---
    main_menu = st.sidebar.radio(
        "मुख्य मेनू (Main Menu)",
        [
            "1. Add Master Data",
            "2. Upload & Process Invoice"
        ]
    )

    # --- 1. ADD MASTER DATA के अंदर के 3 सब-मेनू ---
    if main_menu == "1. Add Master Data":
        st.sidebar.write("---")
        sub_menu = st.sidebar.radio(
            "📋 मास्टर डेटा विकल्प (Sub-Menu)",
            [
                "i. 🌍 Global Masters & Common Dictionaries",
                "ii. ⚙️ Manage Specific Upload Buttons",
                "iii. 🏢 Add Shipper Name & Setup"
            ]
        )
        
        if sub_menu == "i. 🌍 Global Masters & Common Dictionaries":
            render_global_masters()
        elif sub_menu == "ii. ⚙️ Manage Specific Upload Buttons":
            render_manage_buttons()
        elif sub_menu == "iii. 🏢 Add Shipper Name & Setup":
            render_master_data()

    # --- 2. UPLOAD & PROCESS INVOICE ---
    elif main_menu == "2. Upload & Process Invoice":
        render_processor()
