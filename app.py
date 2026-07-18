import streamlit as st
import pickle
import os
from global_masters import render_global_masters
from manage_buttons import render_manage_buttons
from shipper_data import render_shipper_data
from processor import render_processor

# --- मुख्य विंडो सेटिंग्स ---
st.set_page_config(page_title="CK Export Invoice Processor", layout="wide")

DB_FILE = "database.pkl"

# 💾 डेटाबेस को फाइल से लोड और सेव करने के फंक्शन्स
def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return {"shipper_database": {}, "master_types": ["Full Job Excel Format File", "DEEC File", "Packing List"], "global_dictionaries": {}}

def save_database():
    db_to_save = {
        "shipper_database": st.session_state["shipper_database"],
        "master_types": st.session_state["master_types"],
        "global_dictionaries": st.session_state["global_dictionaries"]
    }
    with open(DB_FILE, "wb") as f:
        pickle.dump(db_to_save, f)

# --- डेटाबेस और वेरिएबल्स को सेशन में लोड करना ---
if "db_loaded" not in st.session_state:
    data = load_database()
    st.session_state["shipper_database"] = data.get("shipper_database", {})
    st.session_state["master_types"] = data.get("master_types", ["Full Job Excel Format File", "DEEC File", "Packing List"])
    st.session_state["global_dictionaries"] = data.get("global_dictionaries", {})
    st.session_state["db_loaded"] = True

# 🔒 एड敏न पैनल वेरिएबल्स की शुरुआती घोषणा (ताकि NameError न आए)
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if "processed_file_ready" not in st.session_state:
    st.session_state["processed_file_ready"] = None

# --- साइडबार नेविगेशन ---
st.sidebar.title("📌 Navigation")

# डिफ़ॉल्ट रूप से यूजर सीधे प्रोसेसिंग पेज पर रहेगा
main_menu = st.sidebar.radio(
    "मुख्य मेनू (Main Menu)",
    ["📄 Upload & Process Invoice"]
)

st.sidebar.write("---")

# 🔒 एडमिन पैनल लॉक/अनलॉक एक्सपैंडर
with st.sidebar.expander("🛠️ Admin Panel Access"):
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

# --- मुख्य स्क्रीन का डिस्प्ले (सही ऑर्डर में कंडीशन्स) ---
if st.session_state["admin_authenticated"]:
    st.sidebar.write("---")
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
        save_database()
    elif sub_menu == "ii. ⚙️ Manage Specific Upload Buttons":
        render_manage_buttons()
        save_database()
    elif sub_menu == "iii. 🌍 Global Masters & Common Dictionaries":
        render_global_masters()
        save_database()
else:
    st.title("🚢 CK Export Invoice Processor Pro")
    st.write("---")
    if main_menu == "📄 Upload & Process Invoice":
        render_processor()
        save_database()
