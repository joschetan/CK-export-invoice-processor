import streamlit as st
from global_masters import render_global_masters
from master_data import render_master_data
from shipper_data import render_shipper_data
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

    # --- मुख्य मेनू ---
    menu = st.sidebar.radio(
        "मुख्य मेनू (Main Menu)",
        [
            "1. Global Masters (Common Dictionaries)",
            "2. Add Master Data (Shipper Register)", 
            "3. Add Shipper Data (Format Setup)", 
            "4. Upload & Process Invoices"
        ]
    )

    # अलग-अलग फाइलों से फंक्शन्स को कॉल करना
    if menu == "1. Global Masters (Common Dictionaries)":
        render_global_masters()
    elif menu == "2. Add Master Data (Shipper Register)":
        render_master_data()
    elif menu == "3. Add Shipper Data (Format Setup)":
        render_shipper_data()
    elif menu == "4. Upload & Process Invoices":
        render_processor()
