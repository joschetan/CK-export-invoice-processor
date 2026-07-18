import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO

# --- कॉन्फिगरेशन और बेसिक सेटिंग्स ---
st.set_page_config(page_title="CK Export Invoice Processor", layout="wide")

PASSWORD = "admin" 

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
            st.error("गलत पासवर्ड! कृपया दोबारा प्रयास करें।")
else:
    # --- सेंट्रलाइज्ड डेटाबेस मैनेजमेंट ---
    if "shipper_database" not in st.session_state:
        st.session_state["shipper_database"] = {}
    
    # डायनेमिक डॉक्यूमेंट और मास्टर टाइप्स की लिस्ट (शुरुआती डिफ़ॉल्ट वैल्यूज के साथ)
    if "master_types" not in st.session_state:
        st.session_state["master_types"] = ["Full Job Excel Format File", "DEEC File", "Packing List", "Port of Loading Codes", "HS Code & DBK Dictionary"]
        
    if "processed_file_ready" not in st.session_state:
        st.session_state["processed_file_ready"] = None

    st.title("🚢 CK Export Invoice Processor Pro")
    st.caption("Advanced Dynamic Configuration & Seamless Processing")
    st.write("---")

    # --- मुख्य मेनू (अब सिर्फ 3 ऑप्शंस हैं) ---
    menu = st.sidebar.radio(
        "मुख्य मेनू (Main Menu)",
        [
            "1. Add Master Data", 
            "2. Add Shipper Data", 
            "3. Upload & Process Invoices"
        ]
    )

    # ==========================================
    # 1. ADD MASTER DATA (डायनेमिक + बटन के साथ)
    # ==========================================
    if menu == "1. Add Master Data":
        st.header("📋 Master Data & Document Configuration")
        
        # पार्ट A: शिपर का नाम जोड़ना
        st.subheader("🏢 Register New Shipper Name")
        new_shipper = st.text_input("शिपर / एक्सपोर्टर का नाम दर्ज करें:", placeholder="जैसे: ABC Exports Pvt Ltd")
        if st.button("➕ Add Shipper Name"):
            if new_shipper.strip() == "":
                st.error("कृपया शिपर का नाम खाली न छोड़ें।")
            elif new_shipper in st.session_state["shipper_database"]:
                st.warning(f"⚠️ '{new_shipper}' नाम पहले से मौजूद है।")
            else:
                st.session_state["shipper_database"][new_shipper] = {"allowed_uploads": [], "uploaded_files": {}}
                st.success(f"🎉 शिपर '{new_shipper}' का नाम मास्टर डेटा में जुड़ गया है!")

        st.write("---")
        
        # पार्ट B: डायनेमिक डॉक्यूमेंट/डिक्शनरी टाइप्स जोड़ना (+ और ❌ के साथ)
        st.subheader("⚙️ Manage Upload Buttons & Dictionaries")
        st.caption("यहाँ आप जो भी नाम जोड़ेंगे, वह आगे शिपर कॉन्फ़िगरेशन में अपलोड बटन के रूप में दिखाई देगा।")
        
        # नया टाइप जोड़ने के लिए इनपुट और बटन
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            new_type = st.text_input("नया डॉक्यूमेंट या डिक्शनरी का नाम लिखें:", placeholder="जैसे: Port of Discharge Codes, Rodtep Rules")
        with col_btn:
            st.write("##") # अलाइनमेंट के लिए
            if st.button("➕ Add Type"):
                if new_type.strip() != "" and new_type not in st.session_state["master_types"]:
                    st.session_state["master_types"].append(new_type.strip())
                    st.success(f"'{new_type}' लिस्ट में जुड़ गया है!")
                    st.rerun()

        # वर्तमान लिस्ट दिखाना और डिलीट करने का ऑप्शन
        st.write("#### वर्तमान में उपलब्ध ऑप्शंस:")
        for t in st.session_state["master_types"]:
            c1, c2 = st.columns([4, 1])
            c1.text(f"🔹 {t}")
            if c2.button(f"❌ Remove", key=f"del_{t}"):
                st.session_state["master_types"].remove(t)
                st.rerun()

    # ==========================================
    # 2. ADD SHIPPER DATA (शिपर-वाइज बटन डिफाइन करना)
    # ==========================================
    elif menu == "2. Add Shipper Data":
        st.header("🏢 Shipper Upload Controls Setup")
        
        shippers_list = list(st.session_state["shipper_database"].keys())
        
        if not shippers_list:
            st.warning("⚠️ पहले '1. Add Master Data' में जाकर शिपर का नाम रजिस्टर करें।")
        else:
            selected_shipper = st.selectbox("शिपर का नाम चुनें या सर्च करें:", shippers_list, index=None, placeholder="यहाँ शिपर का नाम टाइप या सेलेक्ट करें...")
            
            if selected_shipper:
                st.write(f"### ⚙️ कॉन्फ़िगर करें: **{selected_shipper}**")
                st.info("इस शिपर के लिए कौन-कौन से अपलोड ऑप्शंस एक्टिव करने हैं? टिक करें:")
                
                # सभी मास्टर टाइप्स को चेकबॉक्स के रूप में दिखाना
                selected_uploads = []
                current_allowed = st.session_state["shipper_database"][selected_shipper].get("allowed_uploads", [])
                
                for t in st.session_state["master_types"]:
                    # अगर पहले से अलाउड है तो डिफ़ॉल्ट टिक रहेगा
                    is_checked = t in current_allowed
                    if st.checkbox(t, value=is_checked, key=f"chk_{selected_shipper}_{t}"):
                        selected_uploads.append(t)
                
                if st.button("🔒 सेव शिपर कॉन्फ़िगरेशन"):
                    st.session_state["shipper_database"][selected_shipper]["allowed_uploads"] = selected_uploads
                    st.success(f"✅ '{selected_shipper}' के लिए अपलोड ऑप्शंस अपडेट कर दिए गए हैं!")

                # पार्ट C: जो भी ऑप्शंस टिक किए गए हैं, उनके लिए एक्चुअल फ़ाइल अपलोड करने के बटन दिखाना
                allowed_buttons = st.session_state["shipper_database"][selected_shipper].get("allowed_uploads", [])
                if allowed_buttons:
                    st.write("---")
                    st.subheader("📁 आवश्यक फ़ाइलें / डिक्शनरी अपलोड करें")
                    
                    for btn_name in allowed_buttons:
                        f_upload = st.file_uploader(f"➡️ Upload: {btn_name}", type=["xlsx", "xls", "pdf"], key=f"upload_{selected_shipper}_{btn_name}")
                        if f_upload:
                            # फ़ाइल डेटा को शिपर के डेटाबेस में स्टोर करना
                            st.session_state["shipper_database"][selected_shipper]["uploaded_files"][btn_name] = f_upload.getvalue()
                            st.caption(f"✅ {btn_name} डेटा सुरक्षित सेव्ड।")

    # ==========================================
    # 3. UPLOAD & PROCESS INVOICES (इन-प्लेस डाउनलोड)
    # ==========================================
    elif menu == "3. Upload & Process Invoices":
        st.header("📤 Invoice Processing & Instant Download Zone")
        
        shippers_list = list(st.session_state["shipper_database"].keys())
        
        if not shippers_list:
            st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है। कृपया पहले स्टेप 1 पूरा करें।")
        else:
            selected_shipper = st.selectbox("किस शिपर का इनवॉ送स प्रोसेस करना है?", shippers_list, index=None, placeholder="यहाँ शिपर का नाम टाइप या सेलेक्ट करें...")
            
            if selected_shipper:
                shipper_info = st.session_state["shipper_database"][selected_shipper]
                
                # चेक करना कि क्या कम से कम 'Full Job Excel Format File' अपलोडेड है
                if "Full Job Excel Format File" not in shipper_info["uploaded_files"]:
                    st.error(f"❌ त्रुटि: इस शिपर के लिए मुख्य 'Full Job Excel Format File' अपलोड नहीं की गई है! कृपया पहले स्टेप 2 में जाकर इसे अपलोड करें।")
                else:
                    st.success(f"🔒 '{selected_shipper}' का प्रोफाइल लोड हो गया है।")
                    
                    # इनवॉइस फ़ाइल अपलोडर
                    invoice_file = st.file_uploader(f"'{selected_shipper}' का PDF या Excel Invoice अपलोड करें", type=["pdf", "xlsx", "xls"])
                    
                    if invoice_file:
                        if st.button("🚀 Process & Fill Data"):
                            st.info("डेटा एक्सट्रैक्शन चालू है... कृपया रुकें...")
                            
                            # ओरिजिनल टेम्पलेट लोड करना
                            original_template_bytes = shipper_info["uploaded_files"]["Full Job Excel Format File"]
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            ws = wb.active
                            
                            # डमी एक्सट्रैक्शन मार्कर (इसे बाद में रिप्लेस करेंगे)
                            ws["A1"] = "PROCESSED & FILLED BY CK SMART AUTOMATION" 
                            
                            output = BytesIO()
                            wb.save(output)
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": f"{selected_shipper}_Filled_Job.xlsx",
                                "data": output.getvalue()
                            }
                            st.success("🎉 डेटा सफलतापूर्वक भर दिया गया है!")
                        
                        # अगर फ़ाइल प्रोसेस हो चुकी है, तो डाउनलोड बटन तुरंत यही नीचे दिखाई देगा
                        if st.session_state["processed_file_ready"]:
                            st.write("---")
                            st.download_button(
                                label="📥 प्रोसेस्ड एक्सेल फ़ाइल तुरंत डाउनलोड करें",
                                data=st.session_state["processed_file_ready"]["data"],
                                file_name=st.session_state["processed_file_ready"]["filename"],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
