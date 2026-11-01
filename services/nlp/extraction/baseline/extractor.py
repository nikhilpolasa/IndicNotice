"""Interpretable Telugu/Hindi/English rule baseline for actionable notices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Iterable, Sequence
from urllib.parse import urlparse

from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.benefits import BenefitItem
from indicnotice.schemas.common import ReviewState
from indicnotice.schemas.dates import DatePrecision, DateRole, TypedDate
from indicnotice.schemas.document import Document
from indicnotice.schemas.documents_required import DocumentRequirement, RequirementType
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup
from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.fees import FeeItem
from indicnotice.schemas.links import LinkItem
from indicnotice.schemas.notice import (
    AnalysisWarning,
    NoticeAnalysis,
    NoticeCategory,
    NoticeMetadata,
)
from services.nlp.extraction.baseline.evidence import (
    EvidenceRecord,
    evidence_from_document,
    index_evidence,
)
from services.nlp.extraction.baseline.types import BaselineExtractionResult, RuleTrace
from services.nlp.ingestion.types import IngestionResult
from services.nlp.validation.normalizers import normalize_inr, normalize_percentage
from services.nlp.validation.validator import validate_analysis
from services.nlp.validation.urls import URL_TOKEN, canonicalize_url


EXTRACTOR_VERSION = "regex-baseline-nlp2-v1"


_NOTICE_TERMS = re.compile(
    r"(?:notification|notice|advertisement|admission|recruitment|scholarship|exam(?:ination)?|"
    r"अधिसूचना|सूचना|विज्ञापन|प्रवेश|भर्ती|छात्रवृत्ति|छात्रव[ृु]?त{1,2}(?:ि|ी)?|परीक्षा|"
    r"నోటిఫికేషన్|ప్రకటన|ప్రవేశ|నియామక|ఉపకార\s*వేతన|పరీక్ష)",
    re.IGNORECASE,
)
_AUTHORITY_TERMS = re.compile(
    r"(?:government|govt\.?|ministry|department|directorate|commission|board|university|college|"
    r"office of|agency|council|society|भारत सरकार|राज्य सरकार|मंत्रालय|विभाग|कार्यालय|आयोग|"
    r"परिषद|विश्वविद्यालय|विद्यालय|महाविद्यालय|ప్రభుత్వ|మంత్రిత్వ|శాఖ|కార్యాలయ|కమిషన్|"
    r"బోర్డు|విశ్వవిద్యాలయ|విద్యాలయ|కళాశాల)",
    re.IGNORECASE,
)
_NOTICE_NUMBER = re.compile(
    r"(?:notice|notification|advertisement|reference|ref\.?|rc\.?|file|memo|"
    r"सूचना|अधिसूचना|विज्ञापन|संदर्भ|पत्र|क्रमांक|संख्या|"
    r"నోటిఫికేషన్|ప్రకటన|సూచన|రిఫరెన్స్|ఆర్\.?సి\.?|మెమో|క్రమ\s*సంఖ్య|సంఖ్య)"
    r"\s*(?:(?:no\.?|number|नं\.?|सं\.?|సం\.?|నెం\.?)\s*[:\-]?|[:\-])\s*"
    r"([A-Z0-9][A-Z0-9._()\-/]{2,})",
    re.IGNORECASE,
)
_GENERIC_REFERENCE = re.compile(r"(?<![A-Z0-9/])([A-Z]{2,}(?:/[A-Z0-9._-]+){2,})(?![A-Z0-9/])")

_NUMERIC_DATE = re.compile(r"(?<!\d)(\d{1,2})([./-])(\d{1,2})\2(\d{4})(?!\d)")
_ISO_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_MONTH_NAMES = {
    "january": 1, "jan": 1, "जनवरी": 1, "జనవరి": 1,
    "february": 2, "feb": 2, "फरवरी": 2, "ఫిబ్రవరి": 2,
    "march": 3, "mar": 3, "मार्च": 3, "మార్చి": 3,
    "april": 4, "apr": 4, "अप्रैल": 4, "ఏప్రిల్": 4,
    "may": 5, "मई": 5, "మే": 5,
    "june": 6, "jun": 6, "जून": 6, "జూన్": 6,
    "july": 7, "jul": 7, "जुलाई": 7, "జూలై": 7,
    "august": 8, "aug": 8, "अगस्त": 8, "ఆగస్టు": 8,
    "september": 9, "sep": 9, "sept": 9, "सितंबर": 9, "सितम्बर": 9, "సెప్టెంబర్": 9,
    "october": 10, "oct": 10, "अक्टूबर": 10, "अक्तूबर": 10, "అక్టోబర్": 10,
    "november": 11, "nov": 11, "नवंबर": 11, "नवम्बर": 11, "నవంబర్": 11,
    "december": 12, "dec": 12, "दिसंबर": 12, "दिसम्बर": 12, "డిసెంబర్": 12,
}
_MONTH_PATTERN = "|".join(sorted((re.escape(item) for item in _MONTH_NAMES), key=len, reverse=True))
_NAMED_DATE = re.compile(
    rf"(?<!\w)(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_PATTERN})[,]?\s+(\d{{4}})(?!\d)",
    re.IGNORECASE,
)
_TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)\s*(?:hours?|hrs?\.?|बजे|గంటలకు|గం\.?)?", re.IGNORECASE)

_DATE_ROLE_RULES: tuple[tuple[str, DateRole, re.Pattern[str]], ...] = (
    ("NLP2.DATE.ROLE.FEE_DEADLINE", DateRole.FEE_PAYMENT_DEADLINE, re.compile(r"(?:fee|शुल्क|फीस|రుసుము|ఫీజు).{0,45}(?:last|deadline|अंतिम|చివరి|గడువు)|(?:last|deadline|अंतिम|చివరి|గడువు).{0,45}(?:fee|शुल्क|ఫీజు|రుసుము)", re.I | re.S)),
    ("NLP2.DATE.ROLE.CORRECTION_DEADLINE", DateRole.CORRECTION_DEADLINE, re.compile(r"(?:correction|सुधार|संशोधन|సవరణ).{0,45}(?:last|end|अंतिम|చివరి|ముగింపు)", re.I | re.S)),
    ("NLP2.DATE.ROLE.CORRECTION_START", DateRole.CORRECTION_START_DATE, re.compile(r"(?:correction|सुधार|संशोधन|సవరణ).{0,45}(?:start|open|प्रारंभ|आरंभ|ప్రారంభ)", re.I | re.S)),
    ("NLP2.DATE.ROLE.APPLICATION_DEADLINE", DateRole.APPLICATION_DEADLINE, re.compile(r"(?:application|registration|form|submit|आवेदन|पंजीकरण|फॉर्म|जमा|దరఖాస్తు|నమోదు|సమర్పించ).{0,65}(?:last|clos(?:ing|es?|ed)\b|deadline|by|before|अंतिम|अंतिम तिथि|तक|చివరి|ముగింపు|గడువు|లోపు)|(?:last date|closing date|deadline|अंतिम तिथि|చివరి తేదీ|గడువు).{0,65}(?:application|registration|आवेदन|దరఖాస్తు|నమోదు)", re.I | re.S)),
    ("NLP2.DATE.ROLE.APPLICATION_OPEN", DateRole.APPLICATION_OPEN, re.compile(r"(?:application|registration|आवेदन|पंजीकरण|దరఖాస్తు|నమోదు).{0,65}(?:start|open|commence|प्रारंभ|आरंभ|शुरू|ప్రారంభ)|(?:start|open|commence|प्रारंभ|आरंभ|ప్రారంభ).{0,65}(?:application|registration|आवेदन|దరఖాస్తు|నమోదు)", re.I | re.S)),
    ("NLP2.DATE.ROLE.ADMIT_CARD", DateRole.ADMIT_CARD_DATE, re.compile(r"(?:admit card|hall ticket|प्रवेश.?पत्र|హాల్\s*టికెట్|ప్రవేశ\s*పత్ర)", re.I)),
    ("NLP2.DATE.ROLE.INTERVIEW", DateRole.INTERVIEW_DATE, re.compile(r"(?:interview|साक्षात्कार|ఇంటర్వ్యూ)", re.I)),
    ("NLP2.DATE.ROLE.VERIFICATION", DateRole.DOCUMENT_VERIFICATION_DATE, re.compile(r"(?:document|certificate|दस्तावेज|प्रमाण.?पत्र|పత్ర|ధృవీకరణ).{0,30}(?:verification|सत्यापन|जाँच|వెరిఫికేషన్|ధృవీకరణ)", re.I | re.S)),
    ("NLP2.DATE.ROLE.COUNSELING", DateRole.COUNSELING_DATE, re.compile(r"(?:counsell?ing|काउंसलिंग|కౌన్సెలింగ్)", re.I)),
    ("NLP2.DATE.ROLE.RESULT", DateRole.RESULT_DATE, re.compile(r"(?:result|परिणाम|ఫలిత)", re.I)),
    ("NLP2.DATE.ROLE.ELIGIBILITY_CUTOFF", DateRole.ELIGIBILITY_CUTOFF_DATE, re.compile(r"(?:age|eligibility|आयु|पात्रता|వయస్సు|అర్హత).{0,35}(?:as on|reckon|के अनुसार|నాటికి|ప్రకారం)", re.I | re.S)),
    ("NLP2.DATE.ROLE.EXAM", DateRole.EXAM_DATE, re.compile(r"(?:exam(?:ination)?|test|परीक्षा|परीक्षण|పరీక్ష)", re.I)),
    ("NLP2.DATE.ROLE.PUBLICATION", DateRole.PUBLICATION_DATE, re.compile(r"(?:published|publication|issued|dated|date\s*:|प्रकाशित|जारी|दिनांक\s*:|తేదీ\s*:|జారీ)", re.I)),
)

_URL = URL_TOKEN
_MONEY = re.compile(
    r"(?:(?:₹|Rs\.?|INR|रु\.?|रुपये|రూ\.?|రూపాయలు)\s*)"
    r"(\d[\d,]*(?:\.\d+)?\s*(?:crores?|lakhs?|lacs?|करोड़|लाख|కోట్లు|కోటి|లక్షలు|లక్ష|हजार|వేలు)?)"
    r"|"
    r"(\d[\d,]*(?:\.\d+)?\s*(?:crores?|lakhs?|lacs?|करोड़|लाख|కోట్లు|కోటి|లక్షలు|లక్ష|हजार|వేలు))"
    r"\s*(?:₹|Rs\.?|INR|रु\.?|रुपये|రూ\.?|రూపాయలు)?",
    re.IGNORECASE,
)
_FEE_CUE = re.compile(r"(?:application fee|exam(?:ination)? fee|processing fee|late fee|fee payable|शुल्क|फीस|రుసుము|ఫీజు)", re.I)
_NOT_FEE = re.compile(r"(?:salary|pay scale|remuneration|income|benefit|scholarship|stipend|वेतन|मानदेय|आय|छात्रवृत्ति|लाभ|జీతం|వేతనం|ఆదాయం|ఉపకార\s*వేతనం|స్కాలర్.?షిప్|ప్రయోజనం)", re.I)
_BENEFIT_CUE = re.compile(r"(?:scholarship|stipend|financial assistance|छात्रवृत्ति|वजीफा|सहायता|ఉపకార\s*వేతనం|స్కాలర్.?షిప్|ఆర్థిక సహాయం)", re.I)
_ZERO_FEE = re.compile(r"(?:\bno\s+(?:application\s+)?fee\b|fee is nil|free of cost|शुल्क नहीं|कोई शुल्क नहीं|निःशुल्क|नि:शुल्क|ఎటువంటి రుసుము లేదు|రుసుము లేదు|ఫీజు లేదు)", re.I)

_DOCUMENT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("income_certificate", re.compile(r"income certificate|आय प्रमाण.?पत्र|ఆదాయ ధృవీకరణ పత్రం|ఆదాయ సర్టిఫికెట్", re.I)),
    ("caste_certificate", re.compile(r"caste|community certificate|जाति प्रमाण.?पत्र|కుల ధృవీకరణ పత్రం|కమ్యూనిటీ సర్టిఫికెట్", re.I)),
    ("residence_certificate", re.compile(r"residence|domicile certificate|निवास प्रमाण.?पत्र|నివాస ధృవీకరణ పత్రం", re.I)),
    ("birth_certificate", re.compile(r"birth certificate|date of birth certificate|जन्म प्रमाण.?पत्र|పుట్టిన తేదీ ధృవీకరణ పత్రం|జనన ధృవీకరణ", re.I)),
    ("marksheet_10th", re.compile(r"(?:10th|ssc|matric).{0,20}(?:mark.?sheet|memo|certificate)|दसवीं.{0,20}(?:अंक|प्रमाण)|పదవ.{0,20}(?:మార్కుల|మెమో|సర్టిఫికెట్)", re.I)),
    ("marksheet_12th", re.compile(r"(?:12th|intermediate|10\+2).{0,20}(?:mark.?sheet|memo|certificate)|बारहवीं.{0,20}(?:अंक|प्रमाण)|ఇంటర్మీడియట్.{0,20}(?:మార్కుల|మెమో|సర్టిఫికెట్)", re.I)),
    ("qualification_certificate", re.compile(r"qualification.{0,15}(?:certificate|degree)|शैक्षिक.{0,15}प्रमाण|అర్హత.{0,15}(?:సర్టిఫికెట్|ధృవీకరణ)", re.I)),
    ("identity_proof", re.compile(r"aadhaar|aadhar|identity proof|photo id|आधार|पहचान पत्र|ఆధార్|గుర్తింపు పత్రం", re.I)),
    ("passport_photo", re.compile(r"passport.?size photo|photograph|पासपोर्ट.{0,10}फोटो|फोटोग्राफ|పాస్.?పోర్ట్.{0,10}ఫోటో|ఫోటోగ్రాఫ్", re.I)),
    ("disability_certificate", re.compile(r"disability|pwd|ph certificate|दिव्यांग|अशक्तता प्रमाण|వికలాంగ|దివ్యాంగ.{0,15}(?:పత్రం|సర్టిఫికెట్)", re.I)),
    ("experience_certificate", re.compile(r"experience certificate|अनुभव प्रमाण|అనుభవ ధృవీకరణ పత్రం|ఎక్స్.?పీరియన్స్ సర్టిఫికెట్", re.I)),
)
_DOCUMENT_RULES = (*_DOCUMENT_RULES,
    ("income_certificate", re.compile(r"आय\s+का\s+प्रमाण[-\s]*पत्र", re.I)),
    ("caste_certificate", re.compile(r"जाति\s+का\s+प्रमाण[-\s]*पत्र", re.I)),
    ("disability_certificate", re.compile(r"(?:दिव्यांग|अशक).{0,30}प्रमाण[-\s]*पत्र", re.I)),
)
_DOCUMENT_CONTEXT = re.compile(r"(?:required|mandatory|enclose|attach|upload|submit|documents?|certificates?|आवश्यक|अनिवार्य|संलग्न|अपलोड|जमा|दस्तावेज|प्रमाण.?पत्र|అవసర|తప్పనిసరి|జత|అప్.?లోడ్|సమర్పించ|పత్రాలు|సర్టిఫికెట్లు)", re.I)
_OPTIONAL = re.compile(r"(?:optional|if available|वैकल्पिक|यदि उपलब्ध|ఐచ్ఛిక|అందుబాటులో ఉంటే)", re.I)
_CONDITIONAL = re.compile(r"(?:if applicable|whichever is applicable|जहाँ लागू|यदि लागू|వర్తిస్తే|అర్హత మేరకు)", re.I)

_EXAMPLE = re.compile(r"(?:example|illustration|उदाहरण|ఉదాహరణ)", re.I)
_ELIGIBILITY_CUE = re.compile(r"(?:eligib|qualification|criteria|age|income|marks|पात्र|योग्यता|आयु|उम्र|आय|अंक|अर्ह|అర్హత|వయస్సు|ఆదాయం|మార్కులు|విద్యార్హత)", re.I)
_AGE_CUE = re.compile(r"(?:age|आयु|उम्र|వయస్సు)", re.I)
_INCOME_CUE = re.compile(r"(?:annual|family|parent).{0,20}income|income|वार्षिक.{0,15}आय|पारिवारिक आय|माता.?पिता.{0,20}आय|వార్షిక.{0,15}ఆదాయం|కుటుంబ ఆదాయం|తల్లిదండ్రుల.{0,20}ఆదాయం", re.I | re.S)
_MARKS_CUE = re.compile(r"(?:marks|percentage|अंक|प्रतिशत|మార్కులు|శాతం)", re.I)
_QUALIFICATIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("B.Tech", re.compile(r"B\.?\s*Tech", re.I)),
    ("B.E.", re.compile(r"B\.?\s*E\.?(?!\w)", re.I)),
    ("Postgraduate", re.compile(r"post.?graduat|master.?s degree|स्नातकोत्तर|పోస్ట్.?గ్రాడ్యుయేట్", re.I)),
    ("Graduate", re.compile(r"graduat(?:e|ion)|bachelor.?s degree|स्नातक|గ్రాడ్యుయేట్|డిగ్రీ", re.I)),
    ("Intermediate/12th", re.compile(r"intermediate|10\s*\+\s*2|12th|बारहवीं|इंटरमीडिएट|ఇంటర్మీడియట్", re.I)),
    ("10th/SSC", re.compile(r"10th|matric|ssc|दसवीं|मैट्रिक|పదవ తరగతి|ఎస్\.?ఎస్\.?సి", re.I)),
)
_OR_CUE = re.compile(r"(?:\bor\b|या|अथवा|లేదా)", re.I)

_ACTION_RULES: tuple[tuple[str, ActionType, re.Pattern[str]], ...] = (
    ("NLP2.ACTION.REGISTER", ActionType.REGISTER, re.compile(r"(?:register|registration|पंजीकरण|निमोदन|నమోదు చేస)", re.I)),
    ("NLP2.ACTION.PAY_FEE", ActionType.PAY_FEE, re.compile(r"(?:pay|payment|भुगतान|जमा).{0,25}(?:fee|शुल्क|फीस)|(?:ఫీజు|రుసుము).{0,25}(?:చెల్లించ|జమ)", re.I | re.S)),
    ("NLP2.ACTION.UPLOAD_DOCUMENT", ActionType.UPLOAD_DOCUMENT, re.compile(r"(?:upload|अपलोड|అప్.?లోడ్).{0,40}(?:document|certificate|दस्तावेज|प्रमाण|పత్ర|సర్టిఫికెట్)", re.I | re.S)),
    ("NLP2.ACTION.SUBMIT", ActionType.SUBMIT_APPLICATION, re.compile(r"(?:submit|send|जमा|प्रेषित|समर्पित|సమర్పించ|పంపించ).{0,45}(?:application|form|आवेदन|फॉर्म|దరఖాస్తు|ఫారం)|(?:application|form|आवेदन|फॉर्म|దరఖాస్తు|ఫారం).{0,45}(?:submit|send|जमा|సమర్పించ|పంపించ)", re.I | re.S)),
    ("NLP2.ACTION.DOWNLOAD_ADMIT", ActionType.DOWNLOAD_ADMIT_CARD, re.compile(r"(?:download|डाउनलोड|డౌన్.?లోడ్).{0,30}(?:admit card|hall ticket|प्रवेश.?पत्र|హాల్ టికెట్)", re.I | re.S)),
    ("NLP2.ACTION.CORRECTION", ActionType.CORRECTION, re.compile(r"(?:correct|correction|edit|सुधार|संशोधन|సవరణ)", re.I)),
    ("NLP2.ACTION.ATTEND_EXAM", ActionType.ATTEND_EXAM, re.compile(r"(?:appear|attend).{0,25}(?:exam|test)|परीक्षा.{0,20}(?:उपस्थित|सम्मिलित)|పరీక్ష.{0,20}(?:హాజరు|పాల్గొన)", re.I | re.S)),
    ("NLP2.ACTION.ATTEND_INTERVIEW", ActionType.ATTEND_INTERVIEW, re.compile(r"(?:attend|appear).{0,20}interview|साक्षात्कार.{0,20}(?:उपस्थित|सम्मिलित)|ఇంటర్వ్యూ.{0,20}హాజరు", re.I | re.S)),
    ("NLP2.ACTION.VERIFY_DOCUMENTS", ActionType.VERIFY_DOCUMENTS, re.compile(r"(?:document|certificate|दस्तावेज|प्रमाण|పత్ర).{0,30}(?:verification|सत्यापन|जाँच|ధృవీకరణ|వెరిఫికేషన్)", re.I | re.S)),
    ("NLP2.ACTION.OBTAIN_DOCUMENT", ActionType.OBTAIN_DOCUMENT, re.compile(r"(?:obtain|get|बनवा|प्राप्त|పొంద|తీసుకో).{0,30}(?:certificate|document|प्रमाण|दस्तावेज|సర్టిఫికెట్|పత్రం)", re.I | re.S)),
)
_EXPLICIT_AFTER = re.compile(r"(?:after|only after|इसके बाद|के बाद|తర్వాత|అనంతరం)", re.I)


@dataclass(frozen=True, slots=True)
class _DateCandidate:
    text: str
    start: int
    end: int
    value: str | None
    ambiguous: bool


class RegexBaselineExtractor:
    """Frozen-interface implementation plus an evidence-aware service entry point."""

    def __init__(self, evidence: Sequence[EvidenceSpan] | None = None):
        self._provided_evidence = tuple(evidence) if evidence is not None else None

    def extract(self, doc: Document) -> NoticeAnalysis:
        """Implement StructuredExtractor using block evidence reconstructed from Document."""
        evidence = self._provided_evidence or evidence_from_document(doc)
        return self.extract_with_trace(doc, evidence).analysis

    def extract_ingestion(self, result: IngestionResult) -> BaselineExtractionResult:
        return self.extract_with_trace(result.document, result.evidence)

    def extract_with_trace(
        self,
        doc: Document,
        evidence: Sequence[EvidenceSpan],
    ) -> BaselineExtractionResult:
        spans = tuple(span for span in evidence if span.document_id == doc.document_id)
        records = index_evidence(spans)
        traces: list[RuleTrace] = []
        warnings: list[AnalysisWarning] = []

        category = self._category(records, traces)
        metadata = self._metadata(doc, records, traces)
        dates = self._dates(records, traces, warnings)
        publication = next(
            (item for item in dates if item.date_type == DateRole.PUBLICATION_DATE and item.value),
            None,
        )
        if publication is not None:
            metadata = metadata.model_copy(
                update={
                    "publication_date": publication.value,
                    "publication_date_evidence_ids": publication.evidence_ids,
                }
            )
        links = self._links(records, traces)
        if metadata.source_url is None and links:
            metadata = metadata.model_copy(update={"source_url": links[0].url})
        fees, benefits = self._money(records, dates, traces)
        documents = self._documents(records, traces)
        eligibility = self._eligibility(records, traces)
        actions = self._actions(records, dates, fees, documents, links, traces)

        analysis = NoticeAnalysis(
            analysis_id=f"nlp2:{doc.document_id}",
            document_id=doc.document_id,
            source_language=doc.detected_language,
            category=category,
            category_confidence=None,
            metadata=metadata,
            dates=dates,
            fees=fees,
            benefits=benefits,
            required_documents=documents,
            eligibility=eligibility,
            actions=actions,
            links=links,
            evidence=list(spans),
            warnings=warnings,
            extractor_model=EXTRACTOR_VERSION,
            extraction_timestamp=None,
        )
        return BaselineExtractionResult(validate_analysis(analysis), tuple(traces))

    @staticmethod
    def _category(records: tuple[EvidenceRecord, ...], traces: list[RuleTrace]) -> NoticeCategory | None:
        text = "\n".join(record.span.text for record in records[:40])
        rules = (
            (NoticeCategory.SCHOLARSHIP, re.compile(r"scholarship|छात्रवृत्ति|छात्रव[ृु]?त{1,2}(?:ि|ी)?|उपकार.?वेतन|ఉపకార\s*వేతన|స్కాలర్.?షిప్", re.I), "NLP2.CATEGORY.SCHOLARSHIP"),
            (NoticeCategory.RECRUITMENT, re.compile(r"recruitment|vacanc|भर्ती|नियुक्ति|रिक्त|నియామక|ఉద్యోగ|ఖాళీ", re.I), "NLP2.CATEGORY.RECRUITMENT"),
            (NoticeCategory.ADMISSION, re.compile(r"admission|प्रवेश|ప్రవేశ|అడ్మిషన్", re.I), "NLP2.CATEGORY.ADMISSION"),
            (NoticeCategory.EXAMINATION, re.compile(r"exam(?:ination)?|test|परीक्षा|పరీక్ష", re.I), "NLP2.CATEGORY.EXAMINATION"),
        )
        for category, pattern, rule_id in rules:
            if pattern.search(text):
                evidence_ids = tuple(record.span.evidence_id for record in records[:40] if pattern.search(record.span.text))[:3]
                traces.append(RuleTrace(rule_id, "category", evidence_ids))
                return category
        # Some legacy Hindi PDFs expose custom-font glyphs for the heading but
        # retain readable table labels. Require multiple recruitment-specific
        # labels instead of guessing from the word "application" alone.
        if re.search(r"पद(?:ों| का नाम)", text) and re.search(r"वेतन", text) and re.search(r"आवेदन", text):
            evidence_ids = tuple(record.span.evidence_id for record in records[:40] if re.search(r"पद(?:ों| का नाम)|वेतन|आवेदन", record.span.text))[:3]
            traces.append(RuleTrace("NLP2.CATEGORY.RECRUITMENT.TABLE_CUES", "category", evidence_ids))
            return NoticeCategory.RECRUITMENT
        return NoticeCategory.OTHER if _NOTICE_TERMS.search(text) else None

    @staticmethod
    def _metadata(doc: Document, records: tuple[EvidenceRecord, ...], traces: list[RuleTrace]) -> NoticeMetadata:
        page_one = [record for record in records if record.span.page_number == 1]
        generic_titles = {
            "notice", "notification", "advertisement", "सूचना", "नोटिस",
            "నోటీసు", "ప్రకటన",
        }
        title_candidates: list[tuple[float, str, tuple[EvidenceRecord, ...]]] = []
        for index, record in enumerate(page_one[:20]):
            compact = " ".join(record.span.text.split())
            variants = [(compact, (record,))]
            if _NOTICE_TERMS.search(compact) and index + 1 < min(len(page_one), 20):
                following = " ".join(page_one[index + 1].span.text.split())
                if (
                    len(compact) <= 140
                    and len(following) <= 140
                    and not _NOTICE_NUMBER.search(following)
                ):
                    variants.append((f"{compact} {following}", (record, page_one[index + 1])))
            for value, sources in variants:
                if not (5 <= len(value) <= 280):
                    continue
                normalized = value.casefold().strip(" .:-")
                score = max(0, 40 - index * 2)
                score += 55 if _NOTICE_TERMS.search(value) else 0
                score += min(len(value.split()), 18)
                score -= 130 if normalized in generic_titles else 0
                score -= max(0, len(value) - 160)
                score -= 35 if len(value) > 180 and re.search(r"[.!?]", value) else 0
                title_candidates.append((score, value, sources))
        if title_candidates:
            _, title, title_records = max(title_candidates, key=lambda item: item[0])
            title_record = title_records[0]
        else:
            title = None
            title_records = ()
            title_record = None

        authority_record = next(
            (
                record
                for record in page_one[:18]
                if 4 <= len(" ".join(record.span.text.split())) <= 260
                and _AUTHORITY_TERMS.search(record.span.text)
                and not _NOTICE_TERMS.fullmatch(record.span.text.strip())
            ),
            None,
        )
        number_record: EvidenceRecord | None = None
        number: str | None = None
        for record in records[:80]:
            match = _NOTICE_NUMBER.search(record.span.text)
            if match:
                number = match.group(1).rstrip(".,;:")
                number_record = record
                break
        if number_record is None:
            for record in records[:30]:
                match = _GENERIC_REFERENCE.search(record.span.text)
                if match:
                    number = match.group(1).rstrip(".,;:")
                    number_record = record
                    break

        if title_record:
            traces.append(RuleTrace("NLP2.METADATA.TITLE.CUE", "metadata.title", (title_record.span.evidence_id,)))
        if authority_record:
            traces.append(RuleTrace("NLP2.METADATA.AUTHORITY.TOP", "metadata.issuing_authority", (authority_record.span.evidence_id,)))
        if number_record:
            number_rule = "NLP2.METADATA.NOTICE_NUMBER" if _NOTICE_NUMBER.search(number_record.span.text) else "NLP2.METADATA.NOTICE_NUMBER.GENERIC_REFERENCE"
            traces.append(RuleTrace(number_rule, "metadata.notice_number", (number_record.span.evidence_id,)))

        source_url = doc.source_path if doc.source_path and urlparse(doc.source_path).scheme in {"http", "https"} else None
        authority = None
        if authority_record:
            matching_lines = [" ".join(line.split()) for line in authority_record.span.text.splitlines() if _AUTHORITY_TERMS.search(line)]
            authority = max(matching_lines, key=len) if matching_lines else " ".join(authority_record.span.text.split())
        return NoticeMetadata(
            title=title,
            issuing_authority=authority,
            notice_number=number,
            source_url=source_url,
            title_evidence_ids=[item.span.evidence_id for item in title_records],
            issuing_authority_evidence_ids=[authority_record.span.evidence_id] if authority_record else [],
            notice_number_evidence_ids=[number_record.span.evidence_id] if number_record else [],
        )

    @staticmethod
    def _parse_dates(text: str) -> list[_DateCandidate]:
        found: list[_DateCandidate] = []
        occupied: list[tuple[int, int]] = []
        for match in _ISO_DATE.finditer(text):
            try:
                parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                continue
            found.append(_DateCandidate(match.group(0), match.start(), match.end(), parsed.isoformat(), False))
            occupied.append((match.start(), match.end()))
        for match in _NUMERIC_DATE.finditer(text):
            if any(start <= match.start() < end for start, end in occupied):
                continue
            day, month, year = int(match.group(1)), int(match.group(3)), int(match.group(4))
            ambiguous = day <= 12 and month <= 12
            try:
                parsed = date(year, month, day)
            except ValueError:
                continue
            found.append(_DateCandidate(match.group(0), match.start(), match.end(), None if ambiguous else parsed.isoformat(), ambiguous))
        for match in _NAMED_DATE.finditer(text):
            month = _MONTH_NAMES[match.group(2).lower()]
            try:
                parsed = date(int(match.group(3)), month, int(match.group(1)))
            except ValueError:
                continue
            found.append(_DateCandidate(match.group(0), match.start(), match.end(), parsed.isoformat(), False))
        return sorted(found, key=lambda item: (item.start, item.end))

    def _dates(
        self,
        records: tuple[EvidenceRecord, ...],
        traces: list[RuleTrace],
        warnings: list[AnalysisWarning],
    ) -> list[TypedDate]:
        results: list[TypedDate] = []
        seen: set[tuple[DateRole, str | None, str]] = set()
        for record in records:
            candidates = self._parse_dates(record.span.text)
            if not candidates:
                continue
            for position, candidate in enumerate(candidates):
                local_start = max(0, candidate.start - 100)
                local_end = min(len(record.span.text), candidate.end + 100)
                local = record.span.text[local_start:local_end]
                neighborhood = "\n".join(
                    part
                    for part in (record.previous_text[-120:], local, record.next_text[:120])
                    if part
                )
                context = local
                role = DateRole.OTHER
                rule_id = "NLP2.DATE.ROLE.OTHER"
                # Explicit two-date application windows: first is open, second is deadline.
                if len(candidates) == 2 and re.search(r"(?:to|through|से|तक|నుండి|వరకు|–|-)", record.span.text[candidates[0].end:candidates[1].start], re.I) and re.search(r"application|registration|आवेदन|पंजीकरण|దరఖాస్తు|నమోదు", record.span.text, re.I):
                    role = DateRole.APPLICATION_OPEN if position == 0 else DateRole.APPLICATION_DEADLINE
                    rule_id = "NLP2.DATE.ROLE.APPLICATION_WINDOW"
                else:
                    for role_context in (local, neighborhood):
                        for candidate_rule, candidate_role, pattern in _DATE_ROLE_RULES:
                            if pattern.search(role_context):
                                role, rule_id = candidate_role, candidate_rule
                                break
                        if role != DateRole.OTHER:
                            break
                if role == DateRole.OTHER and not re.search(r"date|dated|दिनांक|तिथि|तारीख|తేదీ", neighborhood, re.I):
                    continue
                key = (role, candidate.value, candidate.text)
                if key in seen:
                    continue
                seen.add(key)
                time_value = None
                time_match = _TIME.search(record.span.text[candidate.end:candidate.end + 45])
                if time_match and candidate.value is not None:
                    time_value = f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}"
                review = ReviewState.NEEDS_REVIEW if candidate.ambiguous or role == DateRole.OTHER else ReviewState.AUTO_EXTRACTED
                date_id = f"date_{len(results) + 1:03d}"
                results.append(
                    TypedDate(
                        date_id=date_id,
                        date_type=role,
                        value=candidate.value,
                        time=time_value,
                        source_text=candidate.text,
                        precision=DatePrecision.UNCERTAIN if candidate.ambiguous else (DatePrecision.DATETIME if time_value else DatePrecision.DATE_ONLY),
                        evidence_ids=[record.span.evidence_id],
                        review_state=review,
                    )
                )
                outcome = "needs_review" if review == ReviewState.NEEDS_REVIEW else "accepted"
                traces.append(RuleTrace(rule_id, f"dates[{len(results) - 1}]", (record.span.evidence_id,), outcome, candidate.text))
                if candidate.ambiguous:
                    warnings.append(
                        AnalysisWarning(
                            code="ambiguous_numeric_date",
                            message=f"Numeric date {candidate.text!r} is ambiguous; no locale was guessed.",
                            severity="warning",
                            field_path=f"dates[{len(results) - 1}].value",
                            evidence_ids=[record.span.evidence_id],
                        )
                    )
        return results

    @staticmethod
    def _links(records: tuple[EvidenceRecord, ...], traces: list[RuleTrace]) -> list[LinkItem]:
        links: list[LinkItem] = []
        seen: set[tuple[str, str]] = set()
        for record in records:
            for match in _URL.finditer(record.span.text):
                source = match.group(1)
                url = canonicalize_url(source)
                context = record.span.text
                if re.search(r"result|परिणाम|ఫలిత", context, re.I):
                    link_type = "results_page"
                elif re.search(r"pay|payment|शुल्क|फीस|ఫీజు", context, re.I):
                    link_type = "payment_gateway"
                elif re.search(r"apply|application|registration|आवेदन|पंजीकरण|దరఖాస్తు|నమోదు", context, re.I):
                    link_type = "application_portal"
                else:
                    link_type = "other"
                key = (url, link_type)
                if key in seen:
                    continue
                seen.add(key)
                line = next(
                    (candidate.strip() for candidate in record.span.text.splitlines() if source in candidate),
                    source,
                )
                links.append(LinkItem(url=url, link_type=link_type, description=" ".join(line.split()), evidence_ids=[record.span.evidence_id]))
                traces.append(RuleTrace("NLP2.URL.HTTP_OR_WWW", f"links[{len(links) - 1}]", (record.span.evidence_id,), detail=source))
        return links

    @staticmethod
    def _amount_value(source: str) -> float | None:
        value = normalize_inr(source)
        if value is not None:
            return value
        cleaned = re.sub(r"^(?:₹|Rs\.?|INR|रु\.?|रुपये|రూ\.?|రూపాయలు)\s*", "", source.strip(), flags=re.I)
        cleaned = re.sub(r"\s*(?:₹|Rs\.?|INR|रु\.?|रुपये|రూ\.?|రూపాయలు)$", "", cleaned, flags=re.I)
        multiplier = 1.0
        scales = ((r"crores?|करोड़|కోట్లు|కోటి", 10_000_000.0), (r"lakhs?|lacs?|लाख|లక్షలు|లక్ష", 100_000.0), (r"thousands?|हजार|వేలు", 1_000.0))
        for pattern, factor in scales:
            if re.search(pattern, cleaned, re.I):
                multiplier = factor
                cleaned = re.sub(pattern, "", cleaned, flags=re.I)
                break
        number = re.search(r"\d[\d,]*(?:\.\d+)?", cleaned)
        return float(number.group(0).replace(",", "")) * multiplier if number else None

    def _money(
        self,
        records: tuple[EvidenceRecord, ...],
        dates: list[TypedDate],
        traces: list[RuleTrace],
    ) -> tuple[list[FeeItem], list[BenefitItem]]:
        fees: list[FeeItem] = []
        benefits: list[BenefitItem] = []
        fee_seen: set[tuple[float | None, str]] = set()
        benefit_seen: set[tuple[float | None, str]] = set()
        fee_deadline = next((item.date_id for item in dates if item.date_type == DateRole.FEE_PAYMENT_DEADLINE), None)
        for record in records:
            zero_match = _ZERO_FEE.search(record.span.text)
            if zero_match and (0.0, zero_match.group(0).casefold()) not in fee_seen:
                fee_seen.add((0.0, zero_match.group(0).casefold()))
                fees.append(
                    FeeItem(
                        fee_id=f"fee_{len(fees)+1:03d}",
                        fee_type="application_fee",
                        amount_inr=0.0,
                        source_text=zero_match.group(0),
                        payment_deadline_ref=fee_deadline,
                        evidence_ids=[record.span.evidence_id],
                    )
                )
                traces.append(RuleTrace("NLP2.MONEY.ZERO_FEE", f"fees[{len(fees)-1}]", (record.span.evidence_id,), detail=zero_match.group(0)))
            for match in _MONEY.finditer(record.span.text):
                source = match.group(0).strip()
                window = record.span.text[max(0, match.start() - 100):min(len(record.span.text), match.end() + 100)]
                value = self._amount_value(source)
                if _BENEFIT_CUE.search(window) and not re.search(r"salary|वेतन|జీతం|వేతనం", window, re.I):
                    key = (value, source)
                    if key not in benefit_seen:
                        benefit_seen.add(key)
                        benefits.append(BenefitItem(benefit_id=f"benefit_{len(benefits)+1:03d}", benefit_type="scholarship_amount" if re.search(r"scholarship|छात्रवृत्ति|ఉపకార", window, re.I) else "stipend", amount_inr=value, source_text=source, description=" ".join(window.split()), evidence_ids=[record.span.evidence_id]))
                        traces.append(RuleTrace("NLP2.MONEY.BENEFIT_CUE", f"benefits[{len(benefits)-1}]", (record.span.evidence_id,), detail=source))
                    continue
                if not _FEE_CUE.search(window):
                    continue
                if _NOT_FEE.search(window):
                    traces.append(RuleTrace("NLP2.MONEY.FEE_NEGATIVE_CONTEXT", "fees", (record.span.evidence_id,), "rejected", source))
                    continue
                key = (value, source)
                if key in fee_seen:
                    continue
                fee_seen.add(key)
                if re.search(r"late|विलंब|ఆలస్య", window, re.I):
                    fee_type = "late_fee"
                elif re.search(r"exam|परीक्षा|పరీక్ష", window, re.I):
                    fee_type = "examination_fee"
                elif re.search(r"process|प्रसंस्करण|ప్రాసెసింగ్", window, re.I):
                    fee_type = "processing_fee"
                else:
                    fee_type = "application_fee"
                categories = [name for name in ("SC", "ST", "OBC", "EWS", "BC") if re.search(rf"(?<![A-Z]){name}(?![A-Z])", window, re.I)]
                waived_for = "/".join(categories) if categories and re.search(r"(?:exempt|waiv|छूट|माफ|మినహాయింపు)", window, re.I) else None
                applies_to = "/".join(categories) if categories and waived_for is None else None
                if re.search(r"(?:online|नेट.?बैंकिंग|ఆన్.?లైన్)", window, re.I):
                    payment_mode = "online"
                elif re.search(r"(?:challan|चालान|చలాన్)", window, re.I):
                    payment_mode = "challan"
                elif re.search(r"(?:demand draft|डिमांड ड्राफ्ट|డిమాండ్ డ్రాఫ్ట్)", window, re.I):
                    payment_mode = "demand_draft"
                else:
                    payment_mode = None
                fees.append(FeeItem(fee_id=f"fee_{len(fees)+1:03d}", fee_type=fee_type, amount_inr=value, source_text=source, applies_to_category=applies_to, waived_for=waived_for, payment_mode=payment_mode, is_refundable=bool(re.search(r"refundable|वापसी योग्य|తిరిగి చెల్లించ", window, re.I)), payment_deadline_ref=fee_deadline, evidence_ids=[record.span.evidence_id]))
                traces.append(RuleTrace("NLP2.MONEY.FEE_LOCAL_CUE", f"fees[{len(fees)-1}]", (record.span.evidence_id,), detail=source))
        return fees, benefits

    @staticmethod
    def _category_guard(text: str, evidence_id: str, identifier: str) -> ConditionGroup | None:
        categories = [name for name in ("SC", "ST", "OBC", "EWS", "BC") if re.search(rf"(?<![A-Z]){name}(?![A-Z])", text, re.I)]
        if re.search(r"अनुसूचित\s*जाति", text) and "SC" not in categories:
            categories.append("SC")
        if re.search(r"(?:अनुसूचित\s*जनजाति|గిరిజన)", text) and "ST" not in categories:
            categories.append("ST")
        if not categories:
            return None
        return ConditionGroup(
            group_id=f"guard_{identifier}",
            operator="OR",
            children=[Condition(condition_id=f"guard_{identifier}_category", attribute="category", comparator=Comparator.IN, value=categories, source_text=text, evidence_ids=[evidence_id])],
            evidence_ids=[evidence_id],
        )

    @classmethod
    def _document_guard(
        cls,
        text: str,
        evidence_id: str,
        identifier: str,
        *,
        selection_context: str | None = None,
        canonical_name: str | None = None,
    ) -> ConditionGroup | None:
        children: list[Condition] = []
        category = cls._category_guard(text, evidence_id, identifier)
        if category is not None:
            children.extend(child for child in category.children if isinstance(child, Condition))
        elif canonical_name == "caste_certificate":
            children.append(Condition(
                condition_id=f"guard_{identifier}_category",
                attribute="category",
                comparator=Comparator.NOT_IN,
                value=["GENERAL"],
                source_text=text,
                evidence_ids=[evidence_id],
            ))
        if re.search(r"(?:disab|pwd|divyang|दिव्यांग|अशक|à¤¦à¤¿à¤µà¥à¤¯à¤¾à¤‚à¤—|à¤…à¤¶à¤•à¥à¤¤|à°µà°¿à°•à°²à°¾à°‚à°—|à°¦à°¿à°µà±à°¯à°¾à°‚à°—)", text, re.I):
            children.append(Condition(
                condition_id=f"guard_{identifier}_disability",
                attribute="disability_status",
                comparator=Comparator.EQ,
                value="PwD",
                source_text=text,
                evidence_ids=[evidence_id],
            ))
        if re.search(r"(?:selected|shortlisted|merit list|चयनित|मेरिट|मेररट|à¤šà¤¯à¤¨à¤¿à¤¤|à¤®à¥‡à¤°à¤¿à¤Ÿ|à°Žà°‚à°ªà°¿à°•|à°®à±†à°°à°¿à°Ÿà±)", selection_context or text, re.I):
            children.append(Condition(
                condition_id=f"guard_{identifier}_selection",
                attribute="selection_status",
                comparator=Comparator.EQ,
                value="selected",
                source_text=text,
                evidence_ids=[evidence_id],
            ))
        if not children:
            return None
        return ConditionGroup(
            group_id=f"guard_{identifier}",
            operator="AND",
            children=children,
            evidence_ids=[evidence_id],
        )

    def _documents(self, records: tuple[EvidenceRecord, ...], traces: list[RuleTrace]) -> list[DocumentRequirement]:
        from services.nlp.semantic.canonical import canonical_document

        documents: list[DocumentRequirement] = []
        positions: dict[tuple[object, ...], int] = {}
        for record in records:
            context = record.local_context
            if not _DOCUMENT_CONTEXT.search(context):
                continue
            for canonical, pattern in _DOCUMENT_RULES:
                joins_split_token = bool(re.search(r"[-–]\s*$", record.span.text))
                match_text = "\n".join(
                    part for part in (
                        record.span.text,
                        record.next_text if joins_split_token else "",
                    ) if part
                )
                match = pattern.search(match_text)
                if not match:
                    continue
                source = match.group(0)
                identifier = f"doc_{len(documents)+1:03d}"
                if _OPTIONAL.search(context):
                    requirement = RequirementType.OPTIONAL
                    guard = None
                else:
                    guard = self._document_guard(
                        record.span.text,
                        record.span.evidence_id,
                        identifier,
                        selection_context=context if canonical == "income_certificate" else record.span.text,
                        canonical_name=canonical,
                    )
                    if _CONDITIONAL.search(context) or guard is not None:
                        requirement = RequirementType.CONDITIONAL
                    else:
                        requirement = RequirementType.MANDATORY
                evidence_ids = [record.span.evidence_id]
                if joins_split_token and match.end() > len(record.span.text) and record.next_text:
                    next_record = records[record.index + 1]
                    evidence_ids.append(next_record.span.evidence_id)
                candidate = DocumentRequirement(doc_req_id=identifier, canonical_name=canonical, source_name=source, requirement_type=requirement, applies_when=guard, notes="Conditional wording is preserved in evidence." if requirement == RequirementType.CONDITIONAL else None, evidence_ids=evidence_ids, review_state=ReviewState.NEEDS_REVIEW if requirement == RequirementType.CONDITIONAL and guard is None else ReviewState.AUTO_EXTRACTED)
                marker = canonical_document(candidate)
                if marker in positions:
                    position = positions[marker]
                    prior = documents[position]
                    documents[position] = prior.model_copy(update={
                        "evidence_ids": list(dict.fromkeys([*prior.evidence_ids, *candidate.evidence_ids]))
                    })
                    continue
                positions[marker] = len(documents)
                documents.append(candidate)
                traces.append(RuleTrace("NLP2.DOCUMENT.LOCAL_REQUIREMENT", f"required_documents[{len(documents)-1}]", (record.span.evidence_id,), "needs_review" if documents[-1].review_state == ReviewState.NEEDS_REVIEW else "accepted", source))
        return documents

    @staticmethod
    def _comparator(text: str, default: Comparator) -> Comparator:
        rules = (
            (Comparator.LTE, r"not (?:more|greater) than|at most|up to|maximum|does not exceed|से अधिक नहीं|अधिकतम|तक|మించకూడదు|గరిష్ట|వరకు"),
            (Comparator.LT, r"less than|below|under|से कम|కంటే తక్కువ"),
            (Comparator.GTE, r"at least|not less than|minimum|से कम नहीं|न्यूनतम|కనీస|తక్కువ కాకుండా"),
            (Comparator.GT, r"more than|greater than|above|से अधिक|కంటే ఎక్కువ"),
        )
        for comparator, pattern in rules:
            if re.search(pattern, text, re.I):
                return comparator
        return default

    def _eligibility(self, records: tuple[EvidenceRecord, ...], traces: list[RuleTrace]) -> ConditionGroup | None:
        children: list[Condition | ConditionGroup] = []
        seen: set[tuple[str, str, str]] = set()
        for record in records:
            text = record.span.text
            context = record.local_context
            if not _ELIGIBILITY_CUE.search(context) or _EXAMPLE.search(context):
                if _EXAMPLE.search(context):
                    traces.append(RuleTrace("NLP2.ELIGIBILITY.EXAMPLE_GUARD", "eligibility", (record.span.evidence_id,), "rejected"))
                continue
            if _AGE_CUE.search(text):
                range_match = re.search(r"(?:between\s*)?(\d{1,3})\s*(?:years?)?\s*(?:to|and|[-–]|से|నుండి)\s*(\d{1,3})\s*(?:years?|वर्ष|साल|ఏళ్లు|సంవత్సరాలు)?", text, re.I)
                if range_match:
                    low, high = int(range_match.group(1)), int(range_match.group(2))
                    if 0 <= low <= high <= 120:
                        self._add_condition(children, seen, traces, record, "age", Comparator.BETWEEN, [low, high], "years", "NLP2.ELIGIBILITY.AGE_INCLUSIVE_RANGE")
                else:
                    age_match = re.search(r"(?:age|आयु|उम्र|వయస్సు).{0,60}?(\d{1,3})\s*(?:years?|वर्ष|साल|ఏళ్లు|సంవత్సరాలు)?", text, re.I | re.S)
                    if age_match and 0 <= int(age_match.group(1)) <= 120:
                        comparator = self._comparator(text, Comparator.LTE)
                        self._add_condition(children, seen, traces, record, "age", comparator, int(age_match.group(1)), "years", "NLP2.ELIGIBILITY.AGE_COMPARATOR")
            if _INCOME_CUE.search(text):
                money_match = _MONEY.search(text)
                if money_match:
                    source = money_match.group(0)
                    amount = self._amount_value(source)
                    if amount is not None:
                        comparator = self._comparator(text, Comparator.LTE)
                        self._add_condition(children, seen, traces, record, "annual_family_income_inr", comparator, amount, "INR", "NLP2.ELIGIBILITY.INCOME_COMPARATOR")
            if _MARKS_CUE.search(text):
                percent_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent|प्रतिशत|శాతం)", text, re.I)
                if percent_match:
                    value = normalize_percentage(percent_match.group(0))
                    if value is not None:
                        comparator = self._comparator(text, Comparator.GTE)
                        self._add_condition(children, seen, traces, record, "marks_percentage", comparator, value, "%", "NLP2.ELIGIBILITY.MARKS_COMPARATOR")
            qualifications = [(name, pattern.search(text)) for name, pattern in _QUALIFICATIONS]
            qualifications = [(name, match) for name, match in qualifications if match]
            if qualifications and re.search(r"qualif|degree|pass|उत्तीर्ण|योग्यता|అర్హత|ఉత్తీర్ణ", context, re.I):
                leaves: list[Condition] = []
                for name, match in qualifications:
                    key = ("education_level", Comparator.EQ.value, name)
                    if key in seen:
                        continue
                    seen.add(key)
                    leaves.append(Condition(condition_id=f"cond_{len(seen):03d}", attribute="education_level", comparator=Comparator.EQ, value=name, source_text=match.group(0), evidence_ids=[record.span.evidence_id]))
                if leaves:
                    if len(leaves) > 1 and _OR_CUE.search(text):
                        children.append(ConditionGroup(group_id=f"group_qualification_{len(children)+1}", operator="OR", children=leaves, evidence_ids=[record.span.evidence_id]))
                        rule_id = "NLP2.ELIGIBILITY.QUALIFICATION_OR"
                    else:
                        children.extend(leaves)
                        rule_id = "NLP2.ELIGIBILITY.QUALIFICATION"
                    traces.append(RuleTrace(rule_id, "eligibility", (record.span.evidence_id,), detail=", ".join(item.value for item in leaves)))
            if re.search(r"(?:eligible|पात्र|అర్హ)", text, re.I):
                categories = [name for name in ("SC", "ST", "OBC", "EWS", "BC") if re.search(rf"(?<![A-Z]){name}(?![A-Z])", text, re.I)]
                if categories:
                    value = sorted(set(categories))
                    self._add_condition(children, seen, traces, record, "category", Comparator.IN, value, None, "NLP2.ELIGIBILITY.CATEGORY_IN")
        if not children:
            return None
        evidence_ids = list(dict.fromkeys(eid for child in children for eid in child.evidence_ids))
        return ConditionGroup(group_id="eligibility_root", operator="AND", label="Explicitly stated eligibility conditions", children=children, evidence_ids=evidence_ids)

    @staticmethod
    def _add_condition(
        children: list[Condition | ConditionGroup],
        seen: set[tuple[str, str, str]],
        traces: list[RuleTrace],
        record: EvidenceRecord,
        attribute: str,
        comparator: Comparator,
        value: object,
        unit: str | None,
        rule_id: str,
    ) -> None:
        key = (attribute, comparator.value, repr(value))
        if key in seen:
            return
        seen.add(key)
        children.append(Condition(condition_id=f"cond_{len(seen):03d}", attribute=attribute, comparator=comparator, value=value, unit=unit, source_text=record.span.text, evidence_ids=[record.span.evidence_id]))
        traces.append(RuleTrace(rule_id, "eligibility", (record.span.evidence_id,), detail=f"{attribute} {comparator.value} {value!r}"))

    @staticmethod
    def _actions(
        records: tuple[EvidenceRecord, ...],
        dates: list[TypedDate],
        fees: list[FeeItem],
        documents: list[DocumentRequirement],
        links: list[LinkItem],
        traces: list[RuleTrace],
    ) -> list[ActionNode]:
        actions: list[ActionNode] = []
        seen: set[tuple[ActionType, str]] = set()
        deadline_types = {item.date_type: item.date_type.value for item in dates}
        for record in records:
            for rule_id, action_type, pattern in _ACTION_RULES:
                match = pattern.search(record.span.text)
                if not match:
                    continue
                local_description = " ".join(record.span.text.split())
                marker = (action_type, local_description.casefold())
                if marker in seen:
                    continue
                if re.search(
                    r"responsibility of (?:the )?(?:school|principal|officer|authority)|"
                    r"जिम्मेवारी.{0,35}(?:विद्यालय|मुखिया|अधिकारी)|"
                    r"బాధ్యత.{0,35}(?:పాఠశాల|అధికారి)",
                    record.span.text,
                    re.I | re.S,
                ) and not re.search(r"applicant|candidate|student|अभ्यर्थी|विद्यार्थी|छात्र|దరఖాస్తుదారు|విద్యార్థి", record.span.text, re.I):
                    continue
                seen.add(marker)
                identifier = f"action_{len(actions)+1:03d}"
                dependencies = [actions[-1].action_id] if actions and _EXPLICIT_AFTER.search(record.span.text) else []
                deadline_ref = None
                if action_type == ActionType.PAY_FEE:
                    deadline_ref = deadline_types.get(DateRole.FEE_PAYMENT_DEADLINE)
                elif action_type in {ActionType.REGISTER, ActionType.SUBMIT_APPLICATION, ActionType.UPLOAD_DOCUMENT}:
                    deadline_ref = deadline_types.get(DateRole.APPLICATION_DEADLINE)
                elif action_type == ActionType.ATTEND_EXAM:
                    deadline_ref = deadline_types.get(DateRole.EXAM_DATE)
                elif action_type == ActionType.ATTEND_INTERVIEW:
                    deadline_ref = deadline_types.get(DateRole.INTERVIEW_DATE)
                required_refs = []
                if action_type == ActionType.UPLOAD_DOCUMENT:
                    direct_refs = [
                        item.doc_req_id
                        for item in documents
                        if record.span.evidence_id in item.evidence_ids
                        or item.source_name.casefold() in record.span.text.casefold()
                    ]
                    nearby_refs = [
                        item.doc_req_id
                        for item in documents
                        if item.source_name.casefold() in record.local_context.casefold()
                    ]
                    required_refs = direct_refs or (nearby_refs if len(nearby_refs) == 1 else [])
                fee_ref = fees[0].fee_id if action_type == ActionType.PAY_FEE and fees else None
                url_ref = None
                if action_type in {ActionType.REGISTER, ActionType.SUBMIT_APPLICATION, ActionType.PAY_FEE, ActionType.DOWNLOAD_ADMIT_CARD}:
                    local_link = next(
                        (
                            item for item in links
                            if record.span.evidence_id in item.evidence_ids
                            or item.url in record.local_context
                            or item.url.removeprefix("https://") in record.local_context
                        ),
                        None,
                    )
                    url_ref = local_link.url if local_link else None
                if re.search(r"online|ऑनलाइन|ఆన్.?లైన్", record.span.text, re.I):
                    channel = "online_portal"
                elif re.search(r"post|डाक|पोस्ट|తపాలా", record.span.text, re.I):
                    channel = "offline_post"
                elif re.search(r"in person|व्यक्तिगत|स्वयं|ప్రత్యక్ష", record.span.text, re.I):
                    channel = "in_person_center"
                else:
                    channel = None
                actions.append(ActionNode(action_id=identifier, action_type=action_type, description=local_description, depends_on=dependencies, required_document_refs=required_refs, fee_ref=fee_ref, deadline_ref=deadline_ref, channel=channel, url_ref=url_ref, evidence_ids=[record.span.evidence_id]))
                traces.append(RuleTrace(rule_id, f"actions[{len(actions)-1}]", (record.span.evidence_id,), detail=action_type.value))
        return actions
