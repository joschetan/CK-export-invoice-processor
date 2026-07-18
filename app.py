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

# 📊 आपकी गूगल शीट का आईडी और लिंक्स
SPREADSHEET_ID = "182qRuH7R0jZqWVKHCg_oAG1SK5CUSkQpxVPxH2O8QUQ"

# डेटाबेस सिंक करने के लिए हम Google Apps Script या डायरेक्ट HTTP मेथड्स का सपोर्ट लेते हैं
# लेकिन बिना किसी कोडिंग/सेटअप के डायरेक्ट रीड करने का सबसे तेज़ तरीका:
def load_data_from_gsheet():
    try:
        # Rules Sheet लोड करना
        rules_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Rules"
        df_rules = pd.read_csv(rules_url)
        
        # Files Sheet लोड करना
        files_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_Files"
        df_files = pd.read_csv(files_url)
        
        # ऐप के पुराने डिक्शनरी फॉर्मेट में री-बिल्ड करना
        shipper_db = {}
        
        # पहले शिपर प्रोफाइल्स तैयार करना
        if not df_rules.empty and "ShipperName" in df_rules.columns:
            for _, row in df_rules.iterrows():
                s_name = row["ShipperName"]
                if s_name not in shipper_db:
                    shipper_db[s_name] = {"allowed_uploads": ["Full Job Excel Format File"], "uploaded_files": {}, "mapping_rules": {}}
                
                # नियम जोड़ना
                field = row["FieldName"]
                shipper_db[s_name]["mapping_rules"][field] = {
                    "keyword": row["Keyword"] if pd.notna(row["Keyword"]) else "",
                    "position": row["Position"] if pd.notna(row["Position"]) else "Right (आगे)",
                    "cell": row["Cell"] if pd.notna(row["Cell"]) else ""
                }
        
        # अपलोडेड टेम्पलेट फाइल्स को रिकवर करना
        if not df_files.empty and "ShipperName" in df_files.columns:
            for _, row in df_files.iterrows():
                s_name = row["ShipperName"]
                if s_name in shipper_db and pd.notna(row["FileBase64"]):
                    # Base64 स्ट्रिंग को वापस ओरिजिनल बाइनरी बाइट्स में बदलना
                    file_bytes = base64.b64decode(row["FileBase64"])
                    shipper_db[s_name]["uploaded_files"]["Full Job Excel Format File"] = file_bytes
                    
        return shipper_db
    except Exception as e:
        # अगर शीट खाली है या पहली बार चल रही है
        return {}

# 💾 गूगल शीट में डेटा हमेशा के लिए राइट (सेव) करने का बैकअप फंक्शन
# नोट: रीयल-टाइम में बिना क्रेडेंशियल शीट में लिखने के लिए एक 2-लाइन का गूगल मैक्रो स्क्रिप्ट बेस्ट होता है
# अभी के लिए हम सेशन स्टेट बैकअप इनेबल रख रहे हैं जब तक हम मैक्रो लिंक न जोड़ें
def save_data_to_gsheet():
    # यह आपके डेटा को सुरक्षित रखने के लिए बैकअप लॉजिक है
    pass

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

# 🔒 एडमिन पैनल एक्सेस बॉक्स
with st.sidebar.expander("🛠️ Admin Settings Access"):
    if not st.session_state["admin_authenticated"]:
        pwd = st.text_input("एड敏न पासवर्ड डालें:", type="password", key="admin_pwd")
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
