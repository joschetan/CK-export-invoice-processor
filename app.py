import streamlit as st

# 📌 1. मुख्य पेज कॉन्फ़िगरेशन
st.set_page_config(
    page_title="CK Export Invoice Processor Pro", 
    page_icon="🚢",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 📌 2. सेशन स्टेट इनिशियलाइज़ेशन (ग्लोबल ऐप लॉक के लिए)
if "app_authenticated" not in st.session_state:
    st.session_state["app_authenticated"] = False

# 🔒 यदि ऐप अनलॉक नहीं है, तो पहले पासवर्ड स्क्रीन दिखाएँ
if not st.session_state["app_authenticated"]:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>🚢 CK Export Invoice Processor Pro</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>कृपया आगे बढ़ने के लिए ऐप का पासवर्ड दर्ज करें।</p>", unsafe_allow_html=True)
        
        with st.form(key="login_form"):
            pass_input = st.text_input("पासवर्ड दर्ज करें:", type="password", key="global_lock_pwd")
            submit_button = st.form_submit_button("Unlock App", use_container_width=True, type="primary")
            
            if submit_button:
                if pass_input == "CK":
                    st.session_state["app_authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ गलत पासवर्ड! कृपया सही पासवर्ड दर्ज करें।")
    st.stop()

# ==========================================
# 🚀 पासवर्ड सही होने के बाद दिखने वाला मुख्य ऐप कोड
# ==========================================

st.markdown("""
    <style>
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        .creator-card {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 15px;
            border-radius: 12px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .creator-name {
            font-size: 18px;
            font-weight: 700;
            margin-top: 8px;
            margin-bottom: 2px;
        }
        .creator-title {
            font-size: 12px;
            color: #d1d8e0;
            letter-spacing: 1px;
            text-transform: uppercase;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    try:
        st.image("ck_photo.jpg", use_container_width=True)
    except:
        st.info("Photo loading...")
        
    st.markdown("""
        <div class="creator-card">
            <div class="creator-name">Chetan Joshi</div>
            <div class="creator-title">📞 +91 98253 06898</div>
            <hr style="border-color: rgba(255,255,255,0.2); margin: 8px 0;">
            <p style='font-size: 11px; color: #f1f2f6; margin: 0;'>
                <b>CK Export Invoice Pro v2.0</b><br>
                Engineered for Enterprise Automation & Precision.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔒 Lock App", use_container_width=True):
        st.session_state["app_authenticated"] = False
        st.rerun()
        
    st.markdown("---")

import pandas as pd
import requests
import json
import base64

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwEsmWdnkVW3H7_fD99vPMrqhvmY6iJHP1ZooKuwDlj2VE4cht_FBgFyem9xDRFlbjuNw/exec"
SPREADSHEET_ID = "182qRuH7R0jZqWVKHCg_oAG1SK5CUSkQpxVPxH2O8QUQ"

@st.cache_data(show_spinner=False)
def load_data_from_gsheet():
    """सीधे 'Shipper_JSON_Database' शीट से सारा डेटा लोड करता है"""
    shipper_db = {}
    master_rules_template = {}
    
    try:
        json_db_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Shipper_JSON_Database"
        df_json = pd.read_csv(json_db_url)
        if not df_json.empty:
            df_json.columns = df_json.columns.str.strip()
            for _, row in df_json.iterrows():
                if "ShipperName" in df_json.columns and pd.notna(row["ShipperName"]):
                    s_name = str(row["ShipperName"]).strip()
                    if s_name and s_name.lower() != "nan":
                        shipper_json_str = row["ShipperJSON"] if "ShipperJSON" in df_json.columns and pd.notna(row["ShipperJSON"]) else "{}"
                        try:
                            shipper_db[s_name] = json.loads(shipper_json_str)
                        except:
                            shipper_db[s_name] = {
                                "allowed_uploads": ["Full Job Excel Format File"],
                                "uploaded_files": {},
                                "mapping_rules": {},
                                "item_table_rules": {},
                                "item_table_rule_name": "parser_welspun",
                                "igst_config": {"lut_keywords": "", "paid_keywords": ""}
                            }
    except Exception as e:
        st.error(f"Error loading Shipper_JSON_Database: {e}")
        
    return shipper_db, master_rules_template

# 🔄 डेटा लोड इंजन
if "shipper_database" not in st.session_state or "master_rules_template" not in st.session_state:
    db, m_template = load_data_from_gsheet()
    st.session_state["shipper_database"] = db
    st.session_state["master_rules_template"] = m_template
    st.session_state["master_types"] = ["Full Job Excel Format File"]

if "admin_authenticated" not in st.session_state: st.session_state["admin_authenticated"] = False
if "processed_file_ready" not in st.session_state: st.session_state["processed_file_ready"] = None

# ==========================================
# 🖥️ MAIN PAGE ROUTING DISPLAY
# ==========================================
if st.session_state["admin_authenticated"]:
    top_col1, top_col2 = st.columns([8, 2])
    with top_col1:
        st.title("🚢 CK Export Processor - Admin Mode")
    with top_col2:
        if st.button("🚪 Log Out Admin", type="primary", use_container_width=True):
            st.session_state["admin_authenticated"] = False
            st.rerun()
            
    st.write("---")
    
    sub_menu = st.radio(
        "📋 एडमिन सेटिंग्स चुनें:", 
        ["i. 🏢 Add Shipper Name & Setup", "iii. 🌍 Global Masters & Common Dictionaries"],
        horizontal=True
    )
    st.write("---")
    
    from shipper_data import render_shipper_data
    from global_masters import render_global_masters
    
    if sub_menu == "i. 🏢 Add Shipper Name & Setup": 
        render_shipper_data()
    elif sub_menu == "iii. 🌍 Global Masters & Common Dictionaries": 
        render_global_masters()

else:
    from processor import render_processor
    
    col_l, col_c, col_r = st.columns([1, 5, 1])
    with col_c:
        st.title("🚢 CK Export Invoice Processor Pro")
        st.write("---")
        render_processor()
        
        st.write("---")
        st.write("---")
        
        with st.expander("🛠️ Admin Settings Access"):
            pwd = st.text_input("एडमिन पासवर्ड दर्ज करें:", type="password", key="main_admin_pwd")
            if st.button("लॉगिन करें"):
                if pwd == "CK@SOHAM":
                    st.session_state["admin_authenticated"] = True
                    st.rerun()
                else:
                    st.error("गलत पासवर्ड!")
