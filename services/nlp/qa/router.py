"""Small deterministic English/Hindi/Telugu question router."""

from __future__ import annotations

import re

from services.nlp.language_id import ScriptHeuristicDetector
from services.nlp.qa.types import QuestionIntent, QuestionRoute


_RULES: tuple[tuple[QuestionIntent, re.Pattern[str]], ...] = (
    (QuestionIntent.TITLE, re.compile(r"notice title|title of (?:the )?notice|सूचना.*शीर्षक|नोटिस.*शीर्षक|शीर्षक.*(?:सूचना|नोटिस)|నోటీసు.*శీర్షిక|శీర్షిక.*నోటీసు", re.I)),
    (QuestionIntent.ELIGIBILITY, re.compile(r"\beligib|can i apply|why am i not|information is missing|पात्र|योग्य|क्या मैं आवेदन|कौन सी जानकारी.*(?:चाहिए|कम)|అర్హ|దరఖాస్తు చేసుకోవచ్చా|ఏ సమాచారం.*అవసరం", re.I)),
    (QuestionIntent.DEADLINE, re.compile(r"last date|application deadline|closing date|अंतिम तिथि|आवेदन.*(?:अंतिम|तक)|చివరి తేదీ|దరఖాస్తు.*గడువు", re.I)),
    (QuestionIntent.FEE, re.compile(r"\bfees?\b|application charge|शुल्क|फीस|రుసుము|ఫీజు", re.I)),
    (QuestionIntent.DOCUMENTS, re.compile(r"documents?|certificates?|दस्तावेज|प्रमाण.?पत्र|कागजात|పత్రాలు|ధృవీకరణ పత్రాలు|సర్టిఫికెట్లు", re.I)),
    (QuestionIntent.AUTHORITY, re.compile(r"who issued|issuing authority|issued by|किसने जारी|जारीकर्ता|कौन सा विभाग|ఎవరు జారీ|జారీ చేసిన సంస్థ", re.I)),
    (QuestionIntent.URL, re.compile(r"application (?:link|url|portal)|where.*apply|website|वेबसाइट|लिंक|कहाँ.*आवेदन|లింక్|వెబ్.?సైట్|ఎక్కడ.*దరఖాస్తు", re.I)),
    (QuestionIntent.QUALIFICATION, re.compile(r"qualification|degree|required course|योग्यता|डिग्री|अर्हता|అర్హత|డిగ్రీ", re.I)),
    (QuestionIntent.PROCEDURE, re.compile(r"how (?:do|to).*apply|what.*first|comes after|procedure|steps?|आवेदन कैसे|पहले क्या|प्रक्रिया|దరఖాస్తు ఎలా|మొదట|విధానం", re.I)),
    (QuestionIntent.ACTION, re.compile(r"what (?:do i|must i) do|actions?|क्या करना|करना होगा|ఏం చేయాలి|చేయవలసిన", re.I)),
    (QuestionIntent.BENEFIT, re.compile(r"benefit|scholarship amount|stipend|लाभ|छात्रवृत्ति राशि|ప్రయోజనం|ఉపకార వేతనం", re.I)),
    (QuestionIntent.VENUE, re.compile(r"venue|where is (?:the )?(?:exam|interview)|स्थान|कहाँ.*(?:परीक्षा|साक्षात्कार)|వేదిక|ఎక్కడ.*(?:పరీక్ష|ఇంటర్వ్యూ)", re.I)),
    (QuestionIntent.DATE, re.compile(r"exam date|interview date|when is|date of|परीक्षा.*(?:तिथि|तारीख)|साक्षात्कार.*(?:तिथि|तारीख)|इंटरव्यू.*(?:तिथि|तारीख)|कब|పరీక్ష.*తేదీ|ఇంటర్వ్యూ.*తేదీ|ఎప్పుడు", re.I)),
)


def _language(question: str) -> str:
    label, _ = ScriptHeuristicDetector().detect_primary(question)
    if label in {"hi", "te", "en"}:
        return label
    if label == "mixed":
        if re.search(r"[\u0c00-\u0c7f]", question):
            return "te"
        if re.search(r"[\u0900-\u097f]", question):
            return "hi"
    return "en"


def route_question(question: str) -> QuestionRoute:
    normalized = " ".join(question.split())
    language = _language(normalized)
    specific_dates = (
        ("fee_payment_deadline", r"(?:fee|payment|शुल्क|फीस|ఫీజు|రుసుము).*(?:deadline|last date|due|अंतिम|कब तक|गడువు|గడువు|చివరి|ఎప్పటిలోగా)"),
        ("application_open", r"application.*(?:open|start)|(?:आवेदन|దరఖాస్తు).*(?:शुरू|प्रारंभ|ప్రారంభ)|(?:कब से|ఎప్పటి నుండి).*(?:आवेदन|దరఖాస్తు)"),
        ("result_date", r"result.*(?:date|when)|(?:परिणाम|ఫలిత).*(?:कब|तिथि|తేదీ|ఎప్పుడు)"),
        ("correction_deadline", r"correction.*(?:deadline|last date)|(?:सुधार|సవరణ).*(?:अंतिम|చివరి|గడువు)"),
    )
    for role, pattern in specific_dates:
        if re.search(pattern, normalized, re.I):
            return QuestionRoute(intent=QuestionIntent.DATE, language=language, asks_date=True, date_role=role)
    # Common spoken/code-mixed forms, before the more specific legacy rules.
    mixed_rules = (
        (QuestionIntent.DEADLINE, r"\bdeadline\b|last\s+date|aakhri\s+(?:date|tarikh)|antim\s+(?:date|tithi)|chivari\s+(?:date|tedi)|గడువు|आखिरी.*(?:तारीख|तिथि)|कब तक"),
        (QuestionIntent.FEE, r"\b(?:fees?|shulk|rusumu)\b|ఫీజు|फीस"),
        (QuestionIntent.DOCUMENTS, r"\b(?:kagaz|dastavej|patralu)\b|ఏ పత్రాలు|कौन.*कागज"),
        (QuestionIntent.QUALIFICATION, r"qualification|degree|education|शैक्षिक|విద్యార్హత"),
    )
    # Venue/channel questions have their own composite handling below.
    if not re.search(r"where|venue|कहाँ|ఎక్కడ", normalized, re.I):
        for intent, pattern in mixed_rules:
            if re.search(pattern, normalized, re.I):
                return QuestionRoute(intent=intent, language=language)
    asks_venue = bool(re.search(
        r"venue|\u0938\u094d\u0925\u093e\u0928|\u0c35\u0c47\u0c26\u0c3f\u0c15|"
        r"(?:where|\u0915\u0939\u093e\u0901|\u0c0e\u0c15\u0c4d\u0c15\u0c21).*(?:exam|interview|"
        r"\u092a\u0930\u0940\u0915\u094d\u0937\u093e|\u0938\u093e\u0915\u094d\u0937\u093e\u0924\u094d\u0915\u093e\u0930|"
        r"\u0c2a\u0c30\u0c40\u0c15\u0c4d\u0c37|\u0c07\u0c02\u0c1f\u0c30\u0c4d\u0c35\u0c4d\u0c2f\u0c42)",
        normalized,
        re.I,
    ))
    asks_date = bool(re.search(r"when|date|तिथि|कब|तारीख|తేదీ|ఎప్పుడు", normalized, re.I))
    if asks_venue:
        return QuestionRoute(intent=QuestionIntent.VENUE, language=language, asks_date=asks_date, asks_venue=True)
    asks_application_channel = bool(re.search(
        r"where.*apply|apply.*where|application.*where|"
        r"\u0915\u0939\u093e\u0901.*\u0906\u0935\u0947\u0926\u0928|\u0906\u0935\u0947\u0926\u0928.*\u0915\u0939\u093e\u0901|"
        r"\u0c0e\u0c15\u0c4d\u0c15\u0c21.*\u0c26\u0c30\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41|\u0c26\u0c30\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41.*\u0c0e\u0c15\u0c4d\u0c15\u0c21",
        normalized,
        re.I,
    ))
    if asks_application_channel:
        return QuestionRoute(
            intent=QuestionIntent.URL,
            language=language,
            asks_date=asks_date,
            asks_application_channel=True,
        )
    for intent, pattern in _RULES:
        if pattern.search(normalized):
            return QuestionRoute(intent=intent, language=language, asks_date=asks_date, asks_venue=asks_venue)
    return QuestionRoute(intent=QuestionIntent.OTHER_NOTICE_QUESTION, language=language)
