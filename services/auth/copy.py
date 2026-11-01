"""Small English, Telugu and Hindi authentication/profile interface copy."""
from __future__ import annotations

COPY = {
    "app_name": ("IndicNotice", "IndicNotice", "IndicNotice"),
    "signin": ("Sign in", "సైన్ ఇన్", "साइन इन"),
    "register": ("Create account", "ఖాతా సృష్టించండి", "खाता बनाएँ"),
    "register_title": ("Create your IndicNotice account", "మీ IndicNotice ఖాతాను సృష్టించండి", "अपना IndicNotice खाता बनाएँ"),
    "email": ("Email address", "ఇమెయిల్ చిరునామా", "ईमेल पता"),
    "password": ("Password", "పాస్‌వర్డ్", "पासवर्ड"),
    "confirm_password": ("Confirm password", "పాస్‌వర్డ్‌ను నిర్ధారించండి", "पासवर्ड की पुष्टि करें"),
    "password_help": ("Use at least 12 characters.", "కనీసం 12 అక్షరాలు ఉపయోగించండి.", "कम से कम 12 अक्षर रखें।"),
    "new_here": ("New to IndicNotice?", "IndicNotice కు కొత్తవారా?", "IndicNotice पर नए हैं?"),
    "have_account": ("Already have an account?", "ఇప్పటికే ఖాతా ఉందా?", "पहले से खाता है?"),
    "logout": ("Sign out", "సైన్ అవుట్", "साइन आउट"),
    "my_profile": ("My Profile", "నా ప్రొఫైల్", "मेरी प्रोफ़ाइल"),
    "account_settings": ("Account settings", "ఖాతా సెట్టింగ్‌లు", "खाता सेटिंग"),
    "profile_title": ("Student profile", "విద్యార్థి ప్రొఫైల్", "छात्र प्रोफ़ाइल"),
    "profile_intro": ("Save only details you choose to provide. IndicNotice uses matching profile fields only when an extracted notice rule asks for them.", "మీరు అందించాలని ఎంచుకున్న వివరాలను మాత్రమే సేవ్ చేయండి. నోటీసులో సేకరించిన నిబంధన అడిగినప్పుడే IndicNotice సంబంధిత ప్రొఫైల్ ఫీల్డ్‌లను ఉపయోగిస్తుంది.", "केवल वही विवरण सहेजें जिन्हें आप देना चाहते हैं। IndicNotice प्रोफ़ाइल के संबंधित फ़ील्ड का उपयोग तभी करेगा जब निकाली गई सूचना की शर्त उन्हें माँगेगी।"),
    "profile_saved": ("Your profile was saved.", "మీ ప్రొఫైల్ సేవ్ చేయబడింది.", "आपकी प्रोफ़ाइल सहेजी गई।"),
    "profile_empty": ("No profile details are saved yet.", "ప్రొఫైల్ వివరాలు ఇంకా సేవ్ కాలేదు.", "अभी कोई प्रोफ़ाइल विवरण सहेजा नहीं गया है।"),
    "education_level": ("Education level", "విద్యా స్థాయి", "शिक्षा स्तर"),
    "current_class": ("Current class", "ప్రస్తుత తరగతి", "वर्तमान कक्षा"),
    "previous_class": ("Previous class", "మునుపటి తరగతి", "पिछली कक्षा"),
    "marks_percentage": ("Marks / percentage", "మార్కులు / శాతం", "अंक / प्रतिशत"),
    "date_of_birth": ("Date of birth", "పుట్టిన తేదీ", "जन्म तिथि"),
    "age": ("Age", "వయస్సు", "आयु"),
    "state_region": ("State / region", "రాష్ట్రం / ప్రాంతం", "राज्य / क्षेत्र"),
    "current_school_type": ("Current school type", "ప్రస్తుత పాఠశాల రకం", "वर्तमान विद्यालय का प्रकार"),
    "previous_school_type": ("Previous school type", "మునుపటి పాఠశాల రకం", "पिछले विद्यालय का प्रकार"),
    "annual_family_income_inr": ("Annual family income (₹) — optional sensitive detail", "వార్షిక కుటుంబ ఆదాయం (₹) — ఐచ్ఛిక సున్నితమైన వివరము", "वार्षिक पारिवारिक आय (₹) — वैकल्पिक संवेदनशील जानकारी"),
    "category": ("Category", "వర్గం", "श्रेणी"),
    "gender": ("Gender", "లింగం", "लिंग"),
    "attempt_count": ("Number of attempts", "ప్రయత్నాల సంఖ్య", "प्रयासों की संख्या"),
    "disability_status": ("Disability status (optional)", "వైకల్య స్థితి (ఐచ్ఛికం)", "दिव्यांगता स्थिति (वैकल्पिक)"),
    "include_income": ("I choose to save annual family income", "వార్షిక కుటుంబ ఆదాయాన్ని సేవ్ చేయడానికి నేను ఎంచుకుంటున్నాను", "मैं वार्षिक पारिवारिक आय सहेजना चाहता/चाहती हूँ"),
    "custom_attribute": ("Additional attribute key", "అదనపు లక్షణం పేరు", "अतिरिक्त विशेषता का नाम"),
    "custom_value": ("Additional attribute value", "అదనపు లక్షణం విలువ", "अतिरिक्त विशेषता का मान"),
    "custom_value_type": ("Value type", "విలువ రకం", "मान का प्रकार"),
    "type_text": ("Text", "వచనం", "पाठ"),
    "type_number": ("Number", "సంఖ్య", "संख्या"),
    "type_date": ("Date", "తేదీ", "तिथि"),
    "type_boolean": ("Yes / no", "అవును / కాదు", "हाँ / नहीं"),
    "add_attribute_help": ("Use a canonical rule attribute such as `language_preference`, or add a field only when a notice requires it.", "`language_preference` వంటి canonical rule attribute ఉపయోగించండి లేదా నోటీసుకు అవసరమైనప్పుడు మాత్రమే ఫీల్డ్ జోడించండి.", "`language_preference` जैसी canonical rule विशेषता चुनें, या केवल सूचना की आवश्यकता पर फ़ील्ड जोड़ें।"),
    "save_profile": ("Save profile", "ప్రొఫైల్ సేవ్ చేయండి", "प्रोफ़ाइल सहेजें"),
    "delete_profile": ("Delete profile details", "ప్రొఫైల్ వివరాలను తొలగించండి", "प्रोफ़ाइल विवरण हटाएँ"),
    "profile_deleted": ("Profile details deleted.", "ప్రొఫైల్ వివరాలు తొలగించబడ్డాయి.", "प्रोफ़ाइल विवरण हटा दिए गए।"),
    "preferred_language": ("Preferred language", "ఇష్టమైన భాష", "पसंदीदा भाषा"),
    "settings_saved": ("Account settings saved.", "ఖాతా సెట్టింగ్‌లు సేవ్ చేయబడ్డాయి.", "खाता सेटिंग सहेजी गईं।"),
    "current_password": ("Current password", "ప్రస్తుత పాస్‌వర్డ్", "वर्तमान पासवर्ड"),
    "new_password": ("New password", "కొత్త పాస్‌వర్డ్", "नया पासवर्ड"),
    "change_password": ("Change password", "పాస్‌వర్డ్ మార్చండి", "पासवर्ड बदलें"),
    "password_changed": ("Password changed. Sign in again with your new password.", "పాస్‌వర్డ్ మార్చబడింది. కొత్త పాస్‌వర్డ్‌తో మళ్లీ సైన్ ఇన్ చేయండి.", "पासवर्ड बदल गया। नए पासवर्ड से फिर साइन इन करें।"),
    "delete_account": ("Delete account and all saved profile details", "ఖాతా మరియు సేవ్ చేసిన ప్రొఫైల్ వివరాలను తొలగించండి", "खाता और सभी सहेजे गए प्रोफ़ाइल विवरण हटाएँ"),
    "delete_confirm": ("Type DELETE to confirm account deletion", "ఖాతా తొలగింపును నిర్ధారించడానికి DELETE అని టైప్ చేయండి", "खाता हटाने की पुष्टि के लिए DELETE टाइप करें"),
    "account_deleted": ("Your account and saved profile details were deleted.", "మీ ఖాతా మరియు ప్రొఫైల్ వివరాలు తొలగించబడ్డాయి.", "आपका खाता और सहेजे गए प्रोफ़ाइल विवरण हटा दिए गए।"),
    "duplicate_account": ("An account already exists for this email address.", "ఈ ఇమెయిల్ చిరునామాతో ఇప్పటికే ఖాతా ఉంది.", "इस ईमेल पते के लिए पहले से खाता मौजूद है।"),
    "invalid_login": ("Email or password is incorrect.", "ఇమెయిల్ లేదా పాస్‌వర్డ్ తప్పు.", "ईमेल या पासवर्ड गलत है।"),
    "rate_limited": ("Too many attempts. Please wait before trying again.", "చాలా ప్రయత్నాలు జరిగాయి. మళ్లీ ప్రయత్నించే ముందు వేచి ఉండండి.", "बहुत अधिक प्रयास हुए। फिर कोशिश करने से पहले प्रतीक्षा करें।"),
    "csrf_error": ("This form expired. Reload the page and try again.", "ఈ ఫారమ్ గడువు ముగిసింది. పేజీని మళ్లీ లోడ్ చేసి ప్రయత్నించండి.", "यह फ़ॉर्म समाप्त हो गया। पृष्ठ फिर से खोलकर प्रयास करें।"),
    "validation_error": ("Check the highlighted fields and try again.", "హైలైట్ చేసిన ఫీల్డ్‌లను తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.", "चिह्नित फ़ील्ड जाँचकर फिर प्रयास करें।"),
    "signed_out": ("You have been signed out.", "మీరు సైన్ అవుట్ అయ్యారు.", "आप साइन आउट हो गए हैं।"),
    "authenticated_notice": ("Signed in as", "సైన్ ఇన్ చేసిన ఖాతా", "इस खाते से साइन इन"),
    "privacy": ("Your account and profile are private to this sign-in.", "మీ ఖాతా మరియు ప్రొఫైల్ ఈ సైన్ ఇన్‌కే పరిమితం.", "आपका खाता और प्रोफ़ाइल इसी साइन-इन तक सीमित हैं।"),
    "delete_help": ("This permanently removes your account and profile attributes.", "ఇది మీ ఖాతా మరియు ప్రొఫైల్ లక్షణాలను శాశ్వతంగా తొలగిస్తుంది.", "इससे आपका खाता और प्रोफ़ाइल विशेषताएँ स्थायी रूप से हट जाएँगी।"),
    "home": ("Open IndicNotice", "IndicNotice తెరవండి", "IndicNotice खोलें"),
    "not_signed_in": ("Sign in to use IndicNotice.", "IndicNotice ఉపయోగించడానికి సైన్ ఇన్ చేయండి.", "IndicNotice उपयोग करने के लिए साइन इन करें।"),
    "invalid_profile_value": ("Enter a valid value for each profile field.", "ప్రతి ప్రొఫైల్ ఫీల్డ్‌కు సరైన విలువ నమోదు చేయండి.", "हर प्रोफ़ाइल फ़ील्ड के लिए मान्य मान दर्ज करें।"),
    "bad_custom_key": ("Use a lowercase key with letters, numbers and underscores only.", "చిన్న అక్షరాలు, సంఖ్యలు, అండర్‌స్కోర్ మాత్రమే ఉన్న key ఉపయోగించండి.", "केवल छोटे अक्षर, अंक और अंडरस्कोर वाला key उपयोग करें।"),
}


COPY.update({
    "custom_section": ("Additional notice-specific information", "నోటీసుకు సంబంధించిన అదనపు సమాచారం", "सूचना से जुड़ी अतिरिक्त जानकारी"),
    "income_storage_help": ("Optional and stored only when selected.", "ఐచ్ఛికం; మీరు ఎంచుకున్నప్పుడే భద్రపరచబడుతుంది.", "वैकल्पिक; चुनने पर ही सहेजी जाएगी।"),
})


def tr(key: str, language: str = "en") -> str:
    values = COPY.get(key, COPY["validation_error"])
    return values[{"en": 0, "te": 1, "hi": 2}.get(language, 0)]


PROFILE_FIELDS = (
    ("education_level", "text"), ("current_class", "number"),
    ("previous_class", "number"), ("marks_percentage", "number"),
    ("date_of_birth", "date"), ("age", "number"),
    ("state_region", "text"), ("current_school_type", "text"),
    ("previous_school_type", "text"), ("annual_family_income_inr", "income"),
    ("category", "text"), ("gender", "text"),
    ("attempt_count", "number"), ("disability_status", "text"),
)
