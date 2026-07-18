import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO

st.set_page_config(page_title="CK Export Invoice Processor", layout="wide")
PASSWORD = "admin" # इसे आप कभी भी गिटहब पर बदल सकते हैं

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
            st.error("गलत पासवर्ड!")
else:
    st.title("🚢 CK Export Invoice Processor Pro")
    menu = st.sidebar.radio("मुख्य मेनू", ["1. Add Master Data", "2. Add Shipper Data", "3. Upload & Process Invoices", "4. Download Processed Files"])
    st.info(f"आपने '{menu}' चुना है। ऑनलाइन स्क्रिप्ट रेडी है!")
