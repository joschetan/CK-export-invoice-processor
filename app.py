import streamlit as st
import pandas as pd
import requests
import json
import base64

# 📌 1. साइडबार को डिफ़ॉल्ट रूप से छुपाने (Collapsed) के लिए कॉन्फ़िगरेशन
st.set_page_config(
    page_title="CK Export Invoice Processor", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"
SPREADSHEET_ID = "182qRuH7R0jZqWVKHCg_oAG1SK5CUSkQpxVPxH2O8QUQ"

def load_data_from_gsheet():
    shipper_db = {}
    master_rules_template = {}
    
    # 1️⃣ ग्लोबल मास्टर लोड करना (8-Columns Compatible)
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

    # 2️⃣ शिपर्स के रूल्स लोड करना (8-Columns Compatible)
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

    # 3️⃣ टेम्पलेट फाइल्स लोड करना
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

# 🔄 सेशन स्टेट सिंक इंजन
if "shipper_database" not in st.session_state or "master_rules_template" not in st.session_state:
    st.info("🔄 लाइव डेटाबेस और मास्टर बोर्ड सिंक हो रहे हैं...")
    db, m_template = load_data_from_gsheet()
    st.session_state["shipper_database"] = db
    st.session_state["master_rules_template"] = m_template
    st.session_state["master_types"] = ["Full Job Excel Format File"]
    st.session_state["db_loaded"] = True
    st.rerun()

if "admin_authenticated" not in st.session_state: st.session_state["admin_authenticated"] = False
if "processed_file_ready" not in st.session_state: st.session_state["processed_file_ready"] = None

# ==========================================
# ⚙️ SIDEBAR CONTROL PANEL CONFIGURATION
# ==========================================
st.sidebar.title("⚙️ Control Panel")
st.sidebar.write("---")

# 1️⃣ एडमिन मोड एक्टिव होने पर मुख्य बटन
if st.session_state["admin_authenticated"]:
    if st.sidebar.button("↩️ Back to Main Invoice Processor", type="primary", use_container_width=True):
        st.session_state["admin_authenticated"] = False
        st.rerun()
    st.sidebar.write("---")

# 2️⃣ एडमिन रेडियो मेनू
if st.session_state["admin_authenticated"]:
    sub_menu = st.sidebar.radio(
        "📋 एडमिन सेटिंग्स (Master Data)", 
        ["i. 🏢 Add Shipper Name & Setup", "iii. 🌍 Global Masters & Common Dictionaries"]
    )
    st.sidebar.write("---")

# 3️⃣ पासवर्ड एक्सेस ब्लॉक
with st.sidebar.expander("🛠️ Admin Settings Access"):
    if not st.session_state["admin_authenticated"]:
        pwd = st.text_input("एडमिन पासवर्ड डालें:", type="password", key="admin_pwd")
        if st.button("लॉगिन करें"):
            if pwd == "admin":
                st.session_state["admin_authenticated"] = True
                st.rerun()
            else: st.error("गलत पासवर्ड!")
    else:
        st.success("🔒 Admin Mode Active")
        if st.button("Log Out Admin"):
            st.session_state["admin_authenticated"] = False
            st.rerun()

# 4️⃣ बैकअप और रीस्टोर ज़ोन
if st.session_state["admin_authenticated"]:
    st.sidebar.write("---")
    st.sidebar.subheader("📦 System Backup & Restore")
    
    export_db = {}
    for s_name, s_data in st.session_state["shipper_database"].items():
        export_db[s_name] = {"mapping_rules": s_data.get("mapping_rules", {}), "uploaded_files": {}}
        if "Full Job Excel Format File" in s_data.get("uploaded_files", {}):
            export_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = base64.b64encode(s_data["uploaded_files"]["Full Job Excel Format File"]).decode("utf-8")
            
    json_str = json.dumps(export_db, indent=4)
    st.sidebar.download_button(label="📥 Download Full System Backup", data=json_str, file_name="CK_System_Permanent_Backup.json", mime="application/json", use_container_width=True)
    
    uploaded_backup = st.sidebar.file_uploader("📂 Restore System from Backup", type=["json"])
    if uploaded_backup:
        if st.sidebar.button("⚡ Confirm Restore Now", type="primary", use_container_width=True):
            try:
                backup_data = json.load(uploaded_backup)
                imported_db = {}
                rules_payload = []
                for s_name, s_data in backup_data.items():
                    imported_db[s_name] = {"allowed_uploads": ["Full Job Excel Format File"], "uploaded_files": {}, "mapping_rules": s_data.get("mapping_rules", {})}
                    if "Full Job Excel Format File" in s_data.get("uploaded_files", {}):
                        b64_str = s_data["uploaded_files"]["Full Job Excel Format File"]
                        imported_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = base64.b64decode(b64_str)
                        requests.post(WEB_APP_URL, data=json.dumps({"action": "save_file", "shipper": s_name, "file_base64": b64_str}))
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({
                            "shipper": s_name, 
                            "field": f_name, 
                            "keyword": r_info.get("keyword", ""), 
                            "position": r_info.get("position", "Right (आगे)"), 
                            "cell": r_info.get("cell", ""), 
                            "match_mode": r_info.get("match_mode", "Exact Word"),
                            "stop_kw": r_info.get("stop_kw", ""),
                            "filter": r_info.get("filter", "None"),
                            "logic": r_info.get("logic", "None")
                        })
                st.session_state["shipper_database"] = imported_db
                requests.post(WEB_APP_URL, data=json.dumps({"action": "save_rules", "rules": rules_payload}))
                st.sidebar.success("🎉 रीस्टोर सफल!")
                st.rerun()
            except Exception as e: st.sidebar.error(f"फेल: {str(e)}")

# ==========================================
# MAIN PAGE ROUTING DISPLAY
# ==========================================
if st.session_state["admin_authenticated"]:
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
    col_l, col_c, col_r = st.columns([1, 4, 1])
    with col_c:
        st.title("🚢 CK Export Invoice Processor Pro")
        st.write("---")
        render_processor()
