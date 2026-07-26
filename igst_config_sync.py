import streamlit as st
from google_sheet_sync import fetch_all_from_sheet, push_all_to_sheet, get_val_case_insensitive

def fetch_igst_config_from_sheet(shipper_name):
    try:
        data = fetch_all_from_sheet()
        if not data:
            return {"lut_keywords": "", "paid_keywords": ""}
            
        rules_list = data.get("rules", data.get("data", [])) if isinstance(data, dict) else data
        config = {"lut_keywords": "", "paid_keywords": ""}
        
        if isinstance(rules_list, list):
            for row in rules_list:
                if isinstance(row, dict):
                    s_name = get_val_case_insensitive(row, "ShipperName", "shipper", "shippername")
                    rule_kind = get_val_case_insensitive(row, "RuleKind", "kind", default="header").lower()
                    f_name = get_val_case_insensitive(row, "FieldName", "field", "fieldname")
                    
                    if "welspun" in s_name.lower() and (rule_kind == "igst_config" or f_name.lower() in ["lut_keywords", "paid_keywords"]):
                        kw = get_val_case_insensitive(row, "Keyword", "keyword", "kw")
                        if f_name.lower() == "lut_keywords":
                            config["lut_keywords"] = kw
                        elif f_name.lower() == "paid_keywords":
                            config["paid_keywords"] = kw
                            
        return config
    except Exception:
        return {"lut_keywords": "", "paid_keywords": ""}

def save_igst_config_to_sheet(shipper_name, lut_val, paid_val):
    try:
        data = fetch_all_from_sheet()
        rules_list = data.get("rules", data.get("data", [])) if isinstance(data, dict) else data
        
        updated_rules = []
        if isinstance(rules_list, list):
            for row in rules_list:
                if isinstance(row, dict):
                    s_name = get_val_case_insensitive(row, "ShipperName", "")
                    f_name = get_val_case_insensitive(row, "FieldName", "")
                    r_kind = get_val_case_insensitive(row, "RuleKind", "").lower()
                    
                    # पुराने igst_config हटाकर नए UI वाले फ्रेश कीवर्ड्स सेव करेंगे
                    if "welspun" in s_name.lower() and (r_kind == "igst_config" or f_name.lower() in ["lut_keywords", "paid_keywords"]):
                        continue
                    updated_rules.append(row)
                    
        # UI बॉक्स में यूजर द्वारा लिखे गए नए कीवर्ड्स गूगल शीट में जोड़े जा रहे हैं
        updated_rules.append({
            "ShipperName": shipper_name, "FieldName": "lut_keywords", "Keyword": lut_val,
            "Position": "Right (आगे)", "Cell": "", "MatchMode": "Config", "StopKw": "",
            "Filter": "None", "Logic": "None", "Fallback": "", "RuleKind": "igst_config"
        })
        updated_rules.append({
            "ShipperName": shipper_name, "FieldName": "paid_keywords", "Keyword": paid_val,
            "Position": "Right (आगे)", "Cell": "", "MatchMode": "Config", "StopKw": "",
            "Filter": "None", "Logic": "None", "Fallback": "", "RuleKind": "igst_config"
        })
        
        success = push_all_to_sheet(updated_rules, [])
        return success
    except Exception:
        return False
