import streamlit as st
import pandas as pd
import requests
import json
import base64

# --- 🚀 मुख्य विंडो सेटिंग्स ---
st.set_page_config(
    page_title="CK Export Invoice Processor", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🔗 आपका लाइव Google Web App URL
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"
SPREADSHEET_ID = "182qRuH7R0jZqWVKHCg_oAG1SK5CUSkQpxVPxH2O8QUQ"

# 📥 गूगल शीट से लाइव डेटा लोड करने का फंक्शन
def load_data_from_gsheet():
    try:
        # Rules Sheet लोड करना
        rules_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Rules"
        df_rules = pd.read_csv(rules_url)
        
        # Files Sheet लोड करना
        files_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Files"
        df_files = pd.read_csv(files_url)
        
        shipper_db = {}
        
        # 1. रूल्स को डिक्शनरी फॉर्मेट में री-बिल्ड करना
        if not df_rules.empty and "ShipperName" in df_rules.columns:
            for _, row in df_rules.iterrows():
                s_name = row["ShipperName"]
                if s_name not in shipper_db:
                    shipper_db[s_name] = {"allowed_uploads": ["Full Job Excel Format File"], "uploaded_files": {}, "mapping_rules": {}}
                
                field = row["FieldName"]
                shipper_db[s_name]["mapping_rules"][field] = {
                    "keyword": row["Keyword"] if pd.notna(row["Keyword"]) else "",
                    "position": row["Position"] if pd.notna(row["Position"]) else "Right (आगे)",
                    "cell": row["Cell"] if pd.notna(row["Cell"]) else ""
                }
        
        # 2. अपलोडेड एक्सेल टेम्पलेट्स को रिकवर करना
        if not df_files.empty and "ShipperName" in df_files.columns:
            for _, row in df_files.iterrows():
                s_name = row["ShipperName"]
                # अगर शिपर नाम रूल्स में नहीं था तो नया प्रोफाइल बनाएं
                if s_name not in shipper_db:
                    shipper_db[s_name] = {"allowed_uploads": ["Full Job Excel Format File"], "uploaded_files": {}, "mapping_rules": {}}
                
                if pd.notna(row["FileBase64"]):
                    file_bytes = base64.b64decode(row["FileBase64"])
                    shipper_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = file_bytes
                    
        return shipper_db
    except Exception:
        return {}

# --- डेटाबेस को लोड करना ---
if "shipper_database" not in st.session_state or "db_loaded" not in st.session_state:
    st.info("🔄 गूगल शीट डेटाबेस से कनेक्शन सुरक्षित किया जा रहा है...")
    st.session_state["shipper_database"] = load_data_from_gsheet()
    st.session_state["master_types"] = ["Full Job Excel Format File", "DEEC File", "Packing List"]
    st.session_state["global_dictionaries"] = {}
    st.session_state["db_loaded"] = True
    st.rerun()

if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if "processed_file_ready" not in st.session_state:
    st.session_state["processed_file_ready"] = None

# --- 🛠️ साइडबार कॉन्फ़िगरेशन ---
st.sidebar.title("⚙️ Control Panel")
st.sidebar.write("---")

with st.sidebar.expander("🛠️ Admin Settings Access"):
    if not st.session_state["admin_authenticated"]:
        pwd = st.text_input("एडमिन पासवर्ड डालें:", type="password", key="admin_pwd")
        if st.button("लॉगिन करें"):
            if pwd == "admin":
                st.session_state["admin_authenticated"] = True
                st.success("अनलॉक हो गया!")
                st.rerun()
            else:
                st.error("गलत पासवर्ड!")
    else:
        st.success("🔒 एडमिन मोड एक्टिव है")
        if st.button("लॉगआउट एडमिन"):
            st.session_state["admin_authenticated"] = False
            st.rerun()

# --- 🖥️ मुख्य स्क्रीन डिस्प्ले लॉजिक ---
if st.session_state["admin_authenticated"]:
    st.sidebar.write("---")
    from shipper_data import render_shipper_data
    from manage_buttons import render_manage_buttons
    from global_masters import render_global_masters
    
    sub_menu = st.sidebar.radio(
        "📋 एडमिन सेटिंग्स (Master Data)",
        [
            "i. 🏢 Add Shipper Name & Setup",
            "ii. ⚙️ Manage Specific Upload Buttons",
            "iii. 🌍 Global Masters & Common Dictionaries"
        ]
    )
    
    st.title("🚢 CK Export Processor - Admin Mode")
    st.write("---")
    
    if sub_menu == "i. 🏢 Add Shipper Name & Setup":
        render_shipper_data()
    elif sub_menu == "ii. ⚙️ Manage Specific Upload Buttons":
        render_manage_buttons()
    elif sub_menu == "iii. 🌍 Global Masters & Common Dictionaries":
        render_global_masters()
else:
    from processor import render_processor
    
    col_left, col_center, col_right = st.columns([1, 4, 1])
    
    with col_center:
        st.title("🚢 CK Export Invoice Processor Pro")
        st.caption("💡 साइडबार खोलने या एडमिन पैनल में जाने के लिए ऊपर बाएं कोने में दिए गए छोटे तीर (>) पर क्लिक करें।")
        st.write("---")
        
        render_processor()
