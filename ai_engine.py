def ask_local_ai(messages):
    """
    Google Gemini API के माध्यम से डेटा एक्सट्रैक्ट करने का सुपर-फास्ट इंजन।
    """
    api_key = load_gemini_api_key()
    if not api_key:
        return "❌ Error: Gemini API Key सेट नहीं है। कृपया UI में जाकर अपनी API Key दर्ज करें।"

    try:
        genai.configure(api_key=api_key)
        # यहाँ मॉडल को 'gemini-2.0-flash' कर दिया गया है
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        full_prompt = ""
        if isinstance(messages, list):
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                full_prompt += f"\n[{role.upper()}]: {content}\n"
        else:
            full_prompt = str(messages)

        response = model.generate_content(full_prompt)
        if response and response.text:
            return response.text.strip()
        else:
            return "❌ Error: Gemini से खाली रिस्पॉन्स मिला।"
    except Exception as e:
        return f"❌ Gemini API Error: {str(e)}"
