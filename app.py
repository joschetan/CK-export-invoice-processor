# अगर एडमिन लॉग इन है, तभी मास्टर डेटा के विकल्प दिखेंगे
if st.session_state["admin_authenticated"]:
    st.sidebar.write("---")
    
    # यहाँ हमने क्रम को उल्टा (Reverse) कर दिया है
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
    
    # नीचे कंडीशंस (If-Else) को भी नए क्रम के अनुसार सेट कर दिया है
    if sub_menu == "i. 🏢 Add Shipper Name & Setup":
        render_shipper_data()
        save_database()
    elif sub_menu == "ii. ⚙️ Manage Specific Upload Buttons":
        render_manage_buttons()
        save_database()
    elif sub_menu == "iii. 🌍 Global Masters & Common Dictionaries":
        render_global_masters()
        save_database()
