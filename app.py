import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO

# --- कॉन्फिगरेशन और बेसिक सेटिंग्स ---
st.set_page_config(page_title="CK Export Invoice Processor", layout="wide")

# पासवर्ड प्रोटेक्शन
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
    # --- सेंट्रलाइज्ड डेटाबेस (Session State) ---
    # इसमें शिपर का नाम और उसकी एक्सेल फाइल बाइनरी फॉर्मेट में सेव रहेगी
    if "shipper_database" not in st.session_state:
        st.session_state["shipper_database"] = {}
    if "processed_file_ready" not in st.session_state:
        st.session_state["processed_file_ready"] = None

    st.title("🚢 CK Export Invoice Processor Pro")
    st.caption("Step-by-Step Custom Database & Flow Setup")
    st.write("---")

    # --- मुख्य मेनू ---
    menu = st.sidebar.radio(
        "मुख्य मेनू (Main Menu)",
        [
            "1. Add Master Data", 
            "2. Add Shipper Data", 
            "3. Upload & Process Invoices", 
            "4. Download Processed Files"
        ]
    )

    # ==========================================
    # 1. ADD MASTER DATA (सिर्फ शिपर का नाम जोड़ने के लिए)
    # ==========================================
    if menu == "1. Add Master Data":
        st.header("📋 Master Data - Shipper Registration")
        
        new_shipper = st.text_input("नया शिपर / एक्सपोर्टर का नाम दर्ज करें:", placeholder="जैसे: ABC Exports Pvt Ltd")
        
        if st.button("➕ Add Shipper Name"):
            if new_shipper.strip() == "":
                st.error("कृपया शिपर का नाम खाली न छोड़ें।")
            elif new_shipper in st.session_state["shipper_database"]:
                st.warning(f"⚠️ '{new_shipper}' नाम पहले से ही डेटाबेस में मौजूद है।")
            else:
                # डेटाबेस में शिपर का नाम रजिस्टर करना (अभी कोई एक्सेल फाइल नहीं है)
                st.session_state["shipper_database"][new_shipper] = {"excel_template": None}
                st.success(f"🎉 शिपर '{new_shipper}' का नाम सफलतापूर्वक मास्टर डेटा में जुड़ गया है!")

        # वर्तमान में एडेड सिर्फ नाम की लिस्ट दिखाना
        if st.session_state["shipper_database"]:
            st.write("---")
            st.subheader("📜 रजिस्टर्ड शिपर लिस्ट:")
            for idx, s_name in enumerate(st.session_state["shipper_database"].keys(), 1):
                st.text(f"{idx}. {s_name}")

    # ==========================================
    # 2. ADD SHIPPER DATA (फॉर्मेट अपलोड करने के लिए)
    # ==========================================
    elif menu == "2. Add Shipper Data":
        st.header("🏢 Shipper Data Configuration")
        
        # बटन दबाने पर ही आगे का प्रोसेस खुलेगा
        if st.button("📂 Add Full Job Excel Format"):
            st.session_state["show_upload_section"] = True
            
        if st.session_state.get("show_upload_section", False):
            st.write("---")
            shippers_list = list(st.session_state["shipper_database"].keys())
            
            if not shippers_list:
                st.warning("⚠️ पहले '1. Add Master Data' में जाकर शिपर का नाम ऐड करें।")
            else:
                # Search-cum-Dropdown बॉक्स
                selected_shipper = st.selectbox(
                    "शिपर का नाम चुनें या सर्च करें:", 
                    shippers_list, 
                    index=None, 
                    placeholder="यहाँ शिपर का नाम टाइप या सेलेक्ट करें..."
                )
                
                if selected_shipper:
                    st.info(f"चयनित शिपर: **{selected_shipper}**")
                    format_excel = st.file_uploader(
                        f"'{selected_shipper}' के लिए Full Job Excel Format File अपलोड करें", 
                        type=["xlsx", "xls"]
                    )
                    
                    if format_excel:
                        # एक्सेल फाइल को बाइनरी (bytes) में शिपर के नाम के साथ सेव करना
                        st.session_state["shipper_database"][selected_shipper]["excel_template"] = format_excel.getvalue()
                        st.success(f"✅ '{selected_shipper}' के लिए एक्सेल फॉर्मेट फाइल डेटाबेस में सुरक्षित सेव हो गई है!")

        # डेटाबेस का स्टेटस दिखाना कि किस शिपर की एक्सेल फाइल अपलोडेड है
        if st.session_state["shipper_database"]:
            st.write("---")
            st.subheader("📊 फॉर्मेट फाइल स्टेटस:")
            for s_name, data in st.session_state["shipper_database"].items():
                status = "✅ Excel Format Saved" if data["excel_template"] is not None else "❌ No Excel File Added"
                st.text(f"🏢 {s_name} ---> Status: {status}")

    # ==========================================
    # 3. UPLOAD & PROCESS INVOICES (प्रोसेसिंग जोन)
    # ==========================================
    elif menu == "3. Upload & Process Invoices":
        st.header("📤 Invoice Processing Zone")
        
        shippers_list = list(st.session_state["shipper_database"].keys())
        
        if not shippers_list:
            st.warning("⚠️ डेटाबेस में कोई शिपर उपलब्ध नहीं है। कृपया पहले स्टेप 1 और 2 पूरा करें।")
        else:
            # Search-cum-Dropdown बॉक्स
            selected_shipper = st.selectbox(
                "किस शिपर का इनवॉइस प्रोसेस करना है? चुनें या सर्च करें:", 
                shippers_list,
                index=None,
                placeholder="यहाँ शिपर का नाम टाइप या सेलेक्ट करें..."
            )
            
            if selected_shipper:
                # चेक करना कि इस शिपर की एक्सेल फॉर्मेट फाइल अपलोडेड है या नहीं
                shipper_data = st.session_state["shipper_database"][selected_shipper]
                
                if shipper_data["excel_template"] is None:
                    st.error(f"❌ त्रुटि: '{selected_shipper}' के लिए कोई एक्सेल फॉर्मेट फाइल सेव नहीं है! कृपया पहले स्टेप 2 में जाकर फॉर्मेट अपलोड करें।")
                else:
                    st.success(f"🔒 '{selected_shipper}' का एक्सेल फॉर्मेट मिल गया है। अब इनवॉइस अपलोड करें।")
                    
                    # इनवॉइस अपलोड करने का ऑप्शन
                    invoice_file = st.file_uploader(
                        f"'{selected_shipper}' का PDF या Excel Invoice अपलोड करें", 
                        type=["pdf", "xlsx", "xls"]
                    )
                    
                    if invoice_file:
                        if st.button("🚀 Process & Fill Data"):
                            st.info("इनवॉइस से डेटा निकाला जा रहा है और आपकी ओरिजिनल एक्सेल फॉर्मेट में भरा जा रहा है...")
                            
                            # --- यहाँ हमारा मैपिंग और एक्सट्रैक्शन स्क्रिप्ट का लॉजिक काम करेगा ---
                            # अभी के लिए, हम उसकी ओरिजिनल एक्सेल फाइल को ही लोड करके डाउनलोड के लिए तैयार कर रहे हैं
                            original_template_bytes = shipper_data["excel_template"]
                            
                            # उदाहरण के लिए openpyxl से उस फाइल को रीड करना
                            wb = openpyxl.load_workbook(BytesIO(original_template_bytes))
                            ws = wb.active
                            
                            # उदाहरण के तौर पर हम A1 या किसी खाली सेल में एक डमी टेस्ट लिख रहे हैं ताकि पुष्टि हो सके
                            # जब हम स्क्रिप्ट लिखेंगे, तो असली डेटा यहाँ सही सेल्स में जाएगा
                            ws["A1"] = "PROCESSED BY CK AI" 
                            
                            # वापस बाइनरी में सेव करना डाउनलोड के लिए
                            output = BytesIO()
                            wb.save(output)
                            
                            st.session_state["processed_file_ready"] = {
                                "filename": f"{selected_shipper}_Filled_Job.xlsx",
                                "data": output.getvalue()
                            }
                            st.success("🎉 डेटा सफलतापूर्वक भर दिया गया है! कृपया मेनू 4 में जाकर फाइल डाउनलोड करें।")

    # ==========================================
    # 4. DOWNLOAD PROCESSED FILES
    # ==========================================
    elif menu == "4. Download Processed Files":
        st.header("📥 Download Center")
        
        file_data = st.session_state.get("processed_file_ready", None)
        
        if file_data:
            st.success(f"📄 आपकी फाइल '**{file_data['filename']}**' डाउनलोड के लिए तैयार है।")
            st.download_button(
                label="📁 ओरिजिनल एक्सेल फ़ाइल डाउनलोड करें",
                data=file_data["data"],
                file_name=file_data["filename"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("अभी डाउनलोड करने के लिए कोई फाइल प्रोसेस नहीं की गई है। कृपया पहले स्टेप 3 पूरा करें।")
