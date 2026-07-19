import streamlit as st
import pandas as pd
import requests
import json
import base64

st.set_page_config(
    page_title="CK Export Invoice Processor", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"
SPREADSHEET_ID = "182qRuH7R0jZqWVKHCg_oAG1SK5CUSkQpxVPxH2O8QUQ"

def load_data_from_gsheet():
    shipper_db = {}
    
    # 1. पहले रूल्स लोड करें
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
                                "logic": row["Logic"] if "Logic" in df_rules.columns and pd.notna(row["Logic"]) else ""
                            }
    except Exception:
        pass

    # 2. अब अपलोडेड फाइल्स लोड करें
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
                        try:
                            file_bytes = base64.b64decode(str(row["FileBase64"]).strip())
                            shipper_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = file_bytes
                        except Exception:
                            pass
    except Exception:
        pass
                    
    return shipper_db

# 全 डेटाबेस लोड करने का मैकेनिज्म
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

# --- SideBar Config ---
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

# 🛡️ 💾 डेटाबेस बैकअप और रीस्टोर ज़ोन (केवल एडमिन के लॉगिन होने पर ही दिखेगा)
if st.session_state["admin_authenticated"]:
    st.sidebar.write("---")
    st.sidebar.subheader("📦 System Backup & Restore")
    
    # 📥 1. बैकअप एक्सपोर्ट (डाउनलोड) करने का लॉजिक
    # एक्सेल फाइल्स (बाइनरी) को JSON में सीधे टेक्स्ट बनाने के लिए बेस64 एनकोडिंग करेंगे
    export_db = {}
    for s_name, s_data in st.session_state["shipper_database"].items():
        export_db[s_name] = {
            "mapping_rules": s_data.get("mapping_rules", {}),
            "uploaded_files": {}
        }
        # अगर कोई टेम्पलेट एक्सेल अपलोडेड है तो उसे स्ट्रिंग में बदलना
        if "Full Job Excel Format File" in s_data.get("uploaded_files", {}):
            b_data = s_data["uploaded_files"]["Full Job Excel Format File"]
            export_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = base64.b64encode(b_data).decode("utf-8")
            
    json_str = json.dumps(export_db, indent=4)
    
    st.sidebar.download_button(
        label="📥 Download Full System Backup",
        data=json_str,
        file_name="CK_System_Permanent_Backup.json",
        mime="application/json",
        use_container_width=True
    )
    
    # 📤 2. बैकअप इम्पोर्ट (रीस्टोर) करने का लॉजिक
    uploaded_backup = st.sidebar.file_uploader("📂 Restore System from Backup", type=["json"], help="अपनी डाउनलोड की हुई .json बैकअप फ़ाइल यहाँ अपलोड करें")
    
    if uploaded_backup:
        if st.sidebar.button("⚡ Confirm Restore Now", type="primary", use_container_width=True):
            try:
                backup_data = json.load(uploaded_backup)
                
                # वापस बाइनरी डेटा रिकवर करना
                imported_db = {}
                rules_payload = []
                
                for s_name, s_data in backup_data.items():
                    imported_db[s_name] = {
                        "allowed_uploads": ["Full Job Excel Format File"],
                        "uploaded_files": {},
                        "mapping_rules": s_data.get("mapping_rules", {})
                    }
                    
                    # फाइल वापस बाइट्स में बदलना
                    if "Full Job Excel Format File" in s_data.get("uploaded_files", {}):
                        b64_str = s_data["uploaded_files"]["Full Job Excel Format File"]
                        imported_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = base64.b64decode(b64_str)
                        
                        # लाइव गूगल शीट में भी फाइल पुश करने के लिए
                        payload_file = {"action": "save_file", "shipper": s_name, "file_base64": b64_str}
                        requests.post(WEB_APP_URL, data=json.dumps(payload_file))
                        
                    # गूगल शीट पेलोड के लिए रूल्स एरे तैयार करना
                    for f_name, r_info in s_data.get("mapping_rules", {}).items():
                        rules_payload.append({
                            "shipper": s_name,
                            "field": f_name,
                            "keyword": r_info.get("keyword", ""),
                            "position": r_info.get("position", "Right (आगे)"),
                            "cell": r_info.get("cell", ""),
                            "logic": r_info.get("logic", "")
                        })
                        
                # 1. स्थानीय सेशन स्टेट अपडेट करें
                st.session_state["shipper_database"] = imported_db
                
                # 2. लाइव गूगल शीट में रूल्स राइट करें
                payload_rules = {"action": "save_rules", "rules": rules_payload}
                requests.post(WEB_APP_URL, data=json.dumps(payload_rules))
                
                st.sidebar.success("🎉 सिस्टम सफलतापूर्वक पुराने बैकअप पर रीस्टोर हो गया है!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"रीस्टोर फेल हुआ: {str(e)}")

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
