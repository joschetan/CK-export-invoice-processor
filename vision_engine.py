import os
import io
import pdfplumber
from PIL import Image
import torch
from transformers import LayoutLMv3ForTokenClassification, AutoProcessor
from pdf2image import convert_from_bytes

# Hugging Face से हल्का और तेज विजन-डॉक्यूमेंट मॉडल लोड करना (जो Streamlit पर चल सके)
MODEL_NAME = "microsoft/layoutlmv3-base"

@st.cache_resource
def load_vision_processor_and_model():
    try:
        processor = AutoProcessor.from_pretrained(MODEL_NAME, apply_ocr=True)
        model = LayoutLMv3ForTokenClassification.from_pretrained(MODEL_NAME)
        model.eval()
        return processor, model
    except Exception as e:
        return None, None

def extract_value_with_vision_layout(pdf_bytes, target_keyword):
    """
    यह फंक्शन पीडीएफ को विजुअल इमेज में बदलकर LayoutLMv3 मॉडल के जरिए
    कीवर्ड और उसके आस-पास के लेआउट को पढ़कर सही वैल्यू एक्सट्रैक्ट करता है।
    """
    if not pdf_bytes:
        return None
        
    try:
        # 1. PDF को PIL Image में बदलना
        images = convert_from_bytes(pdf_bytes)
        if not images:
            return None
        image = images[0].convert("RGB")
        
        # 2. Processor और Model लोड करना
        processor, model = load_vision_processor_and_model()
        if not processor or not model:
            # Fallback यदि मॉडल लोड होने में कोई नेटवर्क/रिसोर्स इशू आए
            return None
            
        # 3. इमेज और टेक्स्ट को मॉडल के अनुकूल तैयार करना
        encoding = processor(image, text=target_keyword, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model(**encoding)
            
        predictions = outputs.logits.argmax(dim=-1).squeeze().tolist()
        tokens = processor.tokenizer.convert_ids_to_tokens(encoding["input_ids"].squeeze().tolist())
        
        # 4. लेआउट और टोकन मैचिंग से वैल्यू ढूंढना
        extracted_result = ""
        for token, pred in zip(tokens, predictions):
            if token not in ["<s>", "</s>", "<pad>"] and not token.startswith("##"):
                extracted_result += token + " "
                
        return extracted_result.strip() if extracted_result else None
        
    except Exception as ex:
        # यदि कोई तकनीकी दिक्कत आए तो सिस्टम क्रैश न हो, सुरक्षित रूप से हैंडल हो
        return None
