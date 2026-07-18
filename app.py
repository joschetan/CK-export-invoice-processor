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

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"
SPREADSHEET_ID = "182qRuH7R0jZqWVKHCg_oAG1SK5CUSkQpxVPxH2O8QUQ"

def load_data_from_gsheet():
    shipper_db = {}
    
    # 1. पहले रूल्स लोड करके प्रोफाइल स्ट्रक्चर तैयार करें
    try:
        rules_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Rules"
        df_rules = pd.read_csv(rules_url)
        
        if not df_rules.empty:
            # कॉलम नामों को साफ़ करना (ताकि स्पेस की दिक्कत न हो)
            df_rules.columns = df_rules.columns.str.strip()
            
            for _, row in df_rules.iterrows():
                if "ShipperName" in df_rules.columns and pd.notna(row["ShipperName"]):
                    s_name = str(row["ShipperName"]).strip()
                    if s_name and s_name.lower() != "nan":
                        if s_name not in shipper_db:
                            shipper_db[s_name] = {"allowed_uploads": ["Full Job Excel Format File"], "uploaded_files": {}, "mapping_rules": {}}
                        
                        field = str(row["FieldName"]).strip() if "FieldName" in df_rules.columns else None
                        if field and pd.notna(row["FieldName"]):
                            shipper_db[s_name]["mapping_rules"][field] = {
                                "keyword": row["Keyword"] if "Keyword" in df_rules.columns and pd.notna(row["Keyword"]) else "",
                                "position": row["Position"] if "Position" in df_rules.columns and pd.notna(row["Position"]) else "Right (आगे)",
                                "cell": row["Cell"] if "Cell" in df_rules.columns and pd.notna(row["Cell"]) else ""
                            }
    except Exception:
        pass

    # 2. अब अपलोडेड फाइल्स लोड करें और उन्हें सही शिपर से मैच करें
    try:
        files_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Files"
        df_files = pd.read_csv(files_url)
        
        if not df_files.empty:
            df_files.columns = df_files.columns.str.strip()
            
            for _, row in df_files.iterrows():
                if "ShipperName" in df_files.columns and pd.notna(row["ShipperName"]):
                    s_name = str(row["ShipperName"]).strip()
                    
                    # अगर शिpper रूल्स में नहीं था, तो भी प्रोफाइल बनाएं
                    if s_name not in shipper_db:
                        shipper_db[s_name] = {"allowed_uploads": ["Full Job Excel Format File"], "uploaded_files": {}, "mapping_rules": {}}
                    
                    if "FileBase64" in df_files.columns and pd.notna(row["FileBase64"]):
                        try:
                            file_bytes = base64.b64decode(str(row["FileBase64"]).strip())
                            # हमेशा लेटेस्ट अपलोडेड फ़ाइल को स्टोर करना
                            shipper_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = file_bytes
                        except Exception:
                            pass
    except Exception:
        pass
                    
    return shipper_db

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

# --- SideBar Settings ---
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
        st.success("🔒 Admin Mode Active")
        if st.button("Log Out Admin"):
            st.session_state["admin_authenticated"] = False
            st.rerun()

# --- Main Page Display ---
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
