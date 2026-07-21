import streamlit as st
import pandas as pd
import requests
import json
import base64

# --- 🚀 मुख्य विंडो सेटिंग्स (साफ़ और सीधा डिफ़ॉल्ट लेआउट) ---
st.set_page_config(
    page_title="CK Export Invoice Processor Pro", 
    page_icon="🚢",
    layout="wide", 
    initial_sidebar_state="collapsed"  # ऐप खुलने पर साइडबार बंद रहेगा
)

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"
SPREADSHEET_ID = "182qRuH7R0jZqWVKHCg_oAG1SK5CUSkQpxVPxH2O8QUQ"

# 💾 गूगल शीट से डेटा लोड करना (बिना किसी st.rerun() लूप के)
def load_data_from_gsheet():
    shipper_db = {}
    master_rules_template = {}
    
    try:
        master_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Global_Masters"
        df_m = pd.read_csv(master_url)
        if not df_m.empty:
            df_m.columns = df_m.columns.str.strip()
            for _, row in df_m.iterrows():
                if "FieldName" in df_m.columns and pd.notna(row["FieldName"]):
                    f_name = str(row["FieldName"]).strip()
                    master_rules_template[f_name] = {
                        "keyword": row["Keyword"] if "Keyword" in df_m.columns and pd.notna(row["Keyword"]) else "",
                        "position": row["Position"] if "Position" in df_m.columns and pd.notna(row["Position"]) else "Right (आगे)",
                        "cell": row["Cell"] if "Cell" in df_m.columns and pd.notna(row["Cell"]) else "",
                        "match_mode": row["MatchMode"] if "MatchMode" in df_m.columns and pd.notna(row["MatchMode"]) else "Exact Word",
                        "stop_kw": row["StopKw"] if "StopKw" in df_m.columns and pd.notna(row["StopKw"]) else "",
                        "filter": row["Filter"] if "Filter" in df_m.columns and pd.notna(row["Filter"]) else "None",
                        "logic": row["Logic"] if "Logic" in df_m.columns and pd.notna(row["Logic"]) else "None"
                    }
    except Exception:
        pass

    try:
        rules_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Rules"
        df_rules = pd.read_csv(rules_url)
        if not df_rules.empty:
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
                                "cell": row["Cell"] if "Cell" in df_rules.columns and pd.notna(row["Cell"]) else "",
                                "match_mode": row["MatchMode"] if "MatchMode" in df_rules.columns and pd.notna(row["MatchMode"]) else "Exact Word",
                                "stop_kw": row["StopKw"] if "StopKw" in df_rules.columns and pd.notna(row["StopKw"]) else "",
                                "filter": row["Filter"] if "Filter" in df_rules.columns and pd.notna(row["Filter"]) else "None",
                                "logic": row["Logic"] if "Logic" in df_rules.columns and pd.notna(row["Logic"]) else "None"
                            }
    except Exception:
        pass

    try:
        files_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Files"
        df_files = pd.read_csv(files_url)
        if not df_files.empty:
            df_files.columns = df_files.columns.str.strip()
            for _, row in df_files.iterrows():
                if "ShipperName" in df_files.columns and pd.notna(row["ShipperName"]):
                    s_name = str(row["ShipperName"]).strip()
                    if s_name not in shipper_db:
                        shipper_db[s_name] = {"allowed_uploads": ["Full Job Excel Format File"], "uploaded_files": {}, "mapping_rules": {}}
                    if "FileBase64" in df_files.columns and pd.notna(row["FileBase64"]):
                        shipper_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = base64.b64decode(str(row["FileBase64"]).strip())
    except Exception:
        pass
                    
    return shipper_db, master_rules_template

# --- डेटाबेस और वेरिएबल्स लोड करना (बिना st.rerun() के) ---
if "shipper_database" not in st.session_state or "master_rules_template" not in st.session_state:
    db, m_template = load_data_from_gsheet()
    st.session_state["shipper_database"] = db
    st.session_state["master_rules_template"] = m_template
    st.session_state["master_types"] = ["Full Job Excel Format File"]

if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if "processed_file_ready" not in st.session_state:
    st.session_state["processed_file_ready"] = None

# --- 🛠️ साइडबार कॉन्फ़िगरेशन (बिना किसी खराब CSS के) ---
st.sidebar.title("⚙️ Control Panel")
st.sidebar.write("---")

# 🔒 एडमिन पैनल एक्सेस बॉक्स
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
    sub_menu = st.sidebar.radio(
        "📋 एडमिन सेटिंग्स (Master Data)",
        [
            "i. 🏢 Add Shipper Name & Setup",
            "iii. 🌍 Global Masters & Common Dictionaries"
        ]
    )
    
    st.title("🚢 CK Export Processor - Admin Mode")
    st.write("---")
    
    from shipper_data import render_shipper_data
    from global_masters import render_global_masters
    
    if sub_menu == "i. 🏢 Add Shipper Name & Setup":
        render_shipper_data()
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
