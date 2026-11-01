"""Student notice library and admin workflow for the existing Streamlit reader."""
from __future__ import annotations

from datetime import date
import logging
from typing import Any
from urllib.parse import urlparse

from demo.product import initial_analysis
from indicnotice.schemas.eligibility import Comparator, Condition, ConditionGroup, EvalStatus
from services.auth.notices import (
    DuplicateNotice, NoticeLibrary, NoticeUnavailable, evaluate_notice,
    has_reviewable_eligibility_coverage, has_supported_review_coverage,
)
from services.auth.store import AuthorizationError, AuthStore
from services.auth.notifications import NotificationService
from services.nlp.semantic.canonical import iter_conditions


UI = {
    "notifications": ("Notifications", "నోటిఫికేషన్లు", "सूचनाएँ"),
    "notifications_empty": ("You have no notifications yet.", "మీకు ఇంకా నోటిఫికేషన్లు లేవు.", "अभी आपके पास कोई सूचना नहीं है।"),
    "notification_new": ("A published notice may match your reviewed profile requirements.", "ప్రచురించిన నోటీసు మీ సమీక్షించిన ప్రొఫైల్ ప్రమాణాలకు సరిపోవచ్చు.", "प्रकाशित सूचना आपकी समीक्षित प्रोफ़ाइल शर्तों से मेल खा सकती है।"),
    "notification_more": ("More information is needed to assess this notice.", "ఈ నోటీసును అంచనా వేయడానికి మరింత సమాచారం అవసరం.", "इस सूचना का आकलन करने के लिए अधिक जानकारी चाहिए।"),
    "notification_deadline": ("Application deadline in {days} days.", "దరఖాస్తు గడువుకు ఇంకా {days} రోజులు.", "आवेदन की अंतिम तिथि {days} दिन में है।"),
    "deadline_date": ("Deadline date: {date}", "గడువు తేదీ: {date}", "अंतिम तिथि: {date}"),
    "mark_read": ("Mark as read", "చదివినట్లు గుర్తించండి", "पढ़ा हुआ चिह्नित करें"),
    "mark_all_read": ("Mark all as read", "అన్నింటినీ చదివినట్లు గుర్తించండి", "सभी को पढ़ा हुआ चिह्नित करें"),
    "notification_preferences": ("Notification preferences", "నోటిఫికేషన్ ప్రాధాన్యతలు", "सूचना प्राथमिकताएँ"),
    "pref_relevant": ("Notices matching reviewed requirements", "సమీక్షించిన ప్రమాణాలకు సరిపోయే నోటీసులు", "समीक्षित शर्तों से मेल खाती सूचनाएँ"),
    "pref_more": ("Notices needing more profile information", "మరింత ప్రొఫైల్ సమాచారం అవసరమైన నోటీసులు", "अधिक प्रोफ़ाइल जानकारी चाहने वाली सूचनाएँ"),
    "pref_7": ("Remind me 7 days before", "7 రోజుల ముందు గుర్తుచేయండి", "7 दिन पहले याद दिलाएँ"),
    "pref_3": ("Remind me 3 days before", "3 రోజుల ముందు గుర్తుచేయండి", "3 दिन पहले याद दिलाएँ"),
    "pref_1": ("Remind me 1 day before", "1 రోజు ముందు గుర్తుచేయండి", "1 दिन पहले याद दिलाएँ"),
    "save_preferences": ("Save preferences", "ప్రాధాన్యతలను భద్రపరచండి", "प्राथमिकताएँ सहेजें"),
    "saved_preferences": ("Notification preferences saved.", "నోటిఫికేషన్ ప్రాధాన్యతలు భద్రపరచబడ్డాయి.", "सूचना प्राथमिकताएँ सहेजी गईं।"),
    "read": ("Read a notice", "నోటీసు చదవండి", "सूचना पढ़ें"),
    "explore": ("Explore Notices", "నోటీసులను అన్వేషించండి", "सूचनाएँ खोजें"),
    "for_you": ("Notices for Me", "నా కోసం నోటీసులు", "मेरे लिए सूचनाएँ"),
    "details": ("Notice Details", "నోటీసు వివరాలు", "सूचना का विवरण"),
    "admin": ("Admin Notice Management", "నిర్వాహక నోటీసు నిర్వహణ", "व्यवस्थापक सूचना प्रबंधन"),
    "no_notices": ("There are no published notices yet.", "ప్రచురించిన నోటీసులు ఇంకా లేవు.", "अभी कोई प्रकाशित सूचना नहीं है।"),
    "search": ("Search notices", "నోటీసులను వెతకండి", "सूचनाएँ खोजें"),
    "filter_language": ("Notice language", "నోటీసు భాష", "सूचना की भाषा"),
    "filter_issuer": ("Issuing organization", "జారీ చేసిన సంస్థ", "जारी करने वाली संस्था"),
    "deadline_before": ("Deadline on or before", "గడువు తేదీ", "अंतिम तिथि"),
    "all_languages": ("All languages", "అన్ని భాషలు", "सभी भाषाएँ"),
    "all_issuers": ("All organizations", "అన్ని సంస్థలు", "सभी संस्थाएँ"),
    "open_details": ("View notice", "నోటీసును చూడండి", "सूचना देखें"),
    "issuer": ("Issued by", "జారీ చేసిన సంస్థ", "जारीकर्ता"),
    "deadline": ("Application deadline", "దరఖాస్తు గడువు", "आवेदन की अंतिम तिथि"),
    "published": ("Published", "ప్రచురించబడింది", "प्रकाशित"),
    "read_pdf": ("Download original notice PDF", "అసలు నోటీసు PDF డౌన్‌లోడ్ చేయండి", "मूल सूचना PDF डाउनलोड करें"),
    "application_link": ("Open application link", "దరఖాస్తు లింక్ తెరవండి", "आवेदन लिंक खोलें"),
    "fees": ("Fees stated in the notice", "నోటీసులో పేర్కొన్న ఫీజులు", "सूचना में दिए गए शुल्क"),
    "documents": ("Documents stated in the notice", "నోటీసులో పేర్కొన్న పత్రాలు", "सूचना में बताए गए दस्तावेज़"),
    "eligibility": ("Eligibility requirements stated in the notice", "నోటీసులో పేర్కొన్న అర్హత ప్రమాణాలు", "सूचना में दी गई पात्रता शर्तें"),
    "evidence": ("Source evidence", "మూల ఆధారం", "स्रोत प्रमाण"),
    "page": ("Page", "పేజీ", "पृष्ठ"),
    "not_stated": ("Not stated in the extracted notice details.", "సేకరించిన నోటీసు వివరాల్లో పేర్కొనలేదు.", "निकाले गए सूचना विवरण में नहीं बताया गया।"),
    "for_you_intro": ("Every published notice remains available in Explore Notices, including notices that do not match your profile.", "మీ ప్రొఫైల్‌కు సరిపోని నోటీసులతో సహా అన్ని ప్రచురిత నోటీసులు అన్వేషణలో అందుబాటులో ఉంటాయి.", "आपकी प्रोफ़ाइल से मेल न खाने वाली सूचनाएँ भी खोज में उपलब्ध रहेंगी।"),
    "profile_empty": ("Add the profile details you know to check published notices. Missing facts will stay unknown.", "ప్రచురిత నోటీసులను సరిపోల్చడానికి మీకు తెలిసిన ప్రొఫైల్ వివరాలను జోడించండి. లేని వివరాలు తెలియనివిగానే ఉంటాయి.", "प्रकाशित सूचनाएँ जाँचने के लिए ज्ञात प्रोफ़ाइल विवरण जोड़ें। अनुपलब्ध जानकारी अज्ञात ही रहेगी।"),
    "update_profile": ("Update my profile", "నా ప్రొఫైల్‌ను నవీకరించండి", "मेरी प्रोफ़ाइल अपडेट करें"),
    "match_reviewed": ("All reviewed and cited requirements passed. This is not an official eligibility decision; verify the full notice with its issuer.", "సమీక్షించి ఆధారాలు జతచేసిన అన్ని ప్రమాణాలు సరిపోయాయి. ఇది అధికారిక అర్హత నిర్ణయం కాదు; పూర్తి నోటీసును జారీ చేసిన సంస్థతో నిర్ధారించండి.", "समीक्षित और उद्धृत सभी शर्तें पूरी हुईं। यह आधिकारिक पात्रता निर्णय नहीं है; पूरी सूचना जारीकर्ता से जाँचें।"),
    "match_partial": ("The extracted requirements checked so far are met. Verify any remaining conditions in the notice.", "ఇప్పటివరకు సేకరించి తనిఖీ చేసిన ప్రమాణాలు సరిపోయాయి. మిగిలిన షరతులను నోటీసులో పరిశీలించండి.", "अब तक निकाली और जाँची गई शर्तें पूरी हैं। सूचना में बाकी शर्तें भी जाँचें।"),
    "match_fail": ("At least one stated requirement was not met. Other requirements may still need review.", "పేర్కొన్న కనీసం ఒక ప్రమాణం సరిపోలలేదు. ఇతర ప్రమాణాలను ఇంకా సమీక్షించాల్సి ఉండవచ్చు.", "बताई गई कम से कम एक शर्त पूरी नहीं हुई। अन्य शर्तों की समीक्षा बाकी हो सकती है।"),
    "match_unknown": ("More information is needed, or the notice does not state enough reviewed eligibility rules. This is not a pass.", "మరింత సమాచారం అవసరం లేదా నోటీసులో సమీక్షించిన అర్హత ప్రమాణాలు సరిపోవు. ఇది ఉత్తీర్ణత కాదు.", "अधिक जानकारी चाहिए, या सूचना में पर्याप्त समीक्षित पात्रता शर्तें नहीं हैं। इसे पास न मानें।"),
    "all_requirements": ("Requirement", "ప్రమాణం", "शर्त"),
    "candidate_value": ("Your saved value", "మీరు భద్రపరిచిన విలువ", "आपका सहेजा मान"),
    "result": ("Assessment", "సరిపోలిక", "आकलन"),
    "eligibility_uncertain": ("Eligibility review is incomplete or unsupported. Review the source before relying on this match.", "అర్హత సమీక్ష అసంపూర్ణంగా ఉంది లేదా మద్దతు లేదు. ఈ సరిపోలికపై ఆధారపడే ముందు మూలాన్ని పరిశీలించండి.", "पात्रता समीक्षा अधूरी या अप्रमाणित है। इस मिलान पर भरोसा करने से पहले स्रोत देखें।"),
    "admin_only": ("Administrator access is required for notice management.", "నోటీసుల నిర్వహణకు నిర్వాహక అనుమతి అవసరం.", "सूचना प्रबंधन के लिए व्यवस्थापक अनुमति आवश्यक है।"),
    "admin_upload": ("Upload a genuine notice PDF", "నిజమైన నోటీసు PDF అప్‌లోడ్ చేయండి", "वास्तविक सूचना PDF अपलोड करें"),
    "display_title": ("Notice title as shown in the PDF", "PDFలో ఉన్న నోటీసు శీర్షిక", "PDF में दिया गया सूचना शीर्षक"),
    "analyze_save": ("Analyze and save as draft", "విశ్లేషించి ముసాయిదాగా భద్రపరచండి", "विश्लेषण कर मसौदे के रूप में सहेजें"),
    "draft_saved": ("The notice was analyzed and saved privately as a draft.", "నోటీసు విశ్లేషించబడి ప్రైవేట్ ముసాయిదాగా భద్రపరచబడింది.", "सूचना का विश्लेषण करके निजी मसौदे के रूप में सहेजा गया।"),
    "admin_review": ("Review extracted facts and cited requirements before publishing.", "ప్రచురించే ముందు సేకరించిన వివరాలు మరియు ఆధారాలను సమీక్షించండి.", "प्रकाशित करने से पहले निकाले गए तथ्य और उद्धृत शर्तें जाँचें।"),
    "review_complete": ("I checked the extracted conditions and page citations against the full notice.", "సేకరించిన అర్హత ప్రమాణాలను, పేజీ ఆధారాలను పూర్తి నోటీసుతో సరిపోల్చి చూశాను.", "मैंने निकाली गई शर्तों और पृष्ठ उद्धरणों को पूरी सूचना से मिलाकर जाँचा है।"),
    "save_review": ("Save completeness review", "సంపూర్ణత సమీక్షను భద్రపరచండి", "पूर्णता समीक्षा सहेजें"),
    "review_saved": ("Completeness review recorded by {reviewer} on {reviewed_at}.", "సంపూర్ణత సమీక్షను {reviewer} {reviewed_at}న నమోదు చేశారు.", "पूर्णता समीक्षा {reviewer} द्वारा {reviewed_at} को दर्ज की गई।"),
    "publish": ("Publish notice", "నోటీసును ప్రచురించండి", "सूचना प्रकाशित करें"),
    "unpublish": ("Unpublish notice", "నోటీసు ప్రచురణను నిలిపివేయండి", "सूचना अप्रकाशित करें"),
    "remove": ("Remove notice", "నోటీసును తొలగించండి", "सूचना हटाएँ"),
    "confirm_remove": ("Confirm notice removal", "నోటీసు తొలగింపును నిర్ధారించండి", "सूचना हटाने की पुष्टि करें"),
    "reanalyze": ("Reanalyze stored PDF", "భద్రపరిచిన PDFను మళ్లీ విశ్లేషించండి", "सहेजी PDF का फिर से विश्लेषण करें"),
    "no_eligibility": ("No eligibility conditions were extracted. The personalized result stays unknown.", "అర్హత ప్రమాణాలు సేకరించబడలేదు. వ్యక్తిగత ఫలితం తెలియనిదిగానే ఉంటుంది.", "पात्रता शर्तें नहीं निकाली गईं। व्यक्तिगत परिणाम अज्ञात रहेगा।"),
    "no_application_link": ("No application link was extracted from this notice.", "ఈ నోటీసు నుంచి దరఖాస్తు లింక్ సేకరించబడలేదు.", "इस सूचना से आवेदन लिंक नहीं मिला।"),
    "no_matches": ("No published notices match these search filters. Clear a filter or browse all notices.", "ఈ శోధన వడపోతలకు సరిపోయే ప్రచురిత నోటీసులు లేవు. వడపోతను తొలగించి చూడండి.", "इन फ़िल्टर से मेल खाती प्रकाशित सूचनाएँ नहीं हैं। फ़िल्टर हटाकर खोजें।"),
    "choose_notice": ("Choose a notice from Explore Notices to view its details.", "వివరాలు చూడటానికి అన్వేషణ నుంచి నోటీసును ఎంచుకోండి.", "विवरण देखने के लिए खोज से सूचना चुनें।"),
    "publication_date": ("Publication date", "ప్రచురణ తేదీ", "प्रकाशन तिथि"),
    "status_draft": ("Private draft", "ప్రైవేట్ ముసాయిదా", "निजी मसौदा"),
    "status_published": ("Published", "ప్రచురితమైంది", "प्रकाशित"),
    "duplicate": ("This exact PDF is already in the library.", "ఈ PDF ఇప్పటికే లైబ్రరీలో ఉంది.", "यह PDF पहले से लाइब्रेरी में है।"),
    "analysis_failed": ("This PDF could not be analyzed. Check that it is readable and try again.", "ఈ PDFను విశ్లేషించలేకపోయాం. చదవగలిగే PDFతో మళ్లీ ప్రయత్నించండి.", "इस PDF का विश्लेषण नहीं हो सका। पढ़ने योग्य PDF के साथ फिर कोशिश करें।"),
    "save_failed": ("The notice could not be saved. No public notice was created.", "నోటీసును భద్రపరచలేకపోయాం. ప్రజలకు నోటీసు సృష్టించబడలేదు.", "सूचना सहेजी नहीं जा सकी। कोई सार्वजनिक सूचना नहीं बनी।"),
    "marked_complete": ("Reviewed eligibility conditions", "సమీక్షించిన అర్హత ప్రమాణాలు", "समीक्षित पात्रता शर्तें"),
}
LOG = logging.getLogger(__name__)


def text(key: str, language: str) -> str:
    return UI.get(key, UI["analysis_failed"])[{"en": 0, "te": 1, "hi": 2}.get(language, 0)]


def _open_notice_page(notice_id: str) -> None:
    """Run navigation before Streamlit re-instantiates the bound radio widget."""
    import streamlit as st
    st.session_state["selected_library_notice"] = notice_id
    st.session_state["library_page"] = "details"


def render_notice_page(st: Any, page: str, library: NoticeLibrary, store: AuthStore,
                       account: dict, profile: dict[str, object], language: str) -> None:
    if page == "explore":
        _explore(st, library, account, language)
    elif page == "for_you":
        _for_you(st, library, account, profile, language)
    elif page == "details":
        _details(st, library, account, profile, language)
    elif page == "admin":
        _admin(st, library, store, account, language)
    elif page == "notifications":
        _notifications(st, library, account, language)


def _notifications(st, library: NoticeLibrary, account: dict, language: str) -> None:
    service = NotificationService(library.store)
    account_id = account["account_id"]
    st.header(text("notifications", language))
    entries = service.list_for_user(account_id)
    if entries:
        if service.unread_count(account_id):
            if st.button(text("mark_all_read", language), key="notifications-mark-all-read"):
                service.mark_all_read(account_id)
                st.rerun()
        for item in entries:
            with st.container(border=True):
                if item["read_at"] is None:
                    st.markdown("**● " + item["title"] + "**")
                else:
                    st.markdown(item["title"])
                if item["event_type"] == "deadline":
                    message = text("notification_deadline", language).format(days=item["reminder_days"])
                    import json
                    dates = json.loads(item["deadlines_json"])
                    due = next((entry["value"] for entry in dates if entry.get("date_type") == "application_deadline" and entry.get("value")), None)
                    if due:
                        st.caption(text("deadline_date", language).format(date=due))
                else:
                    message = text("notification_new" if item["event_type"] == "relevant_notice" else "notification_more", language)
                st.write(message)
                left, right = st.columns([1, 4])
                left.button(text("open_details", language), key=f"notification-open-{item['notification_id']}",
                            on_click=_open_notice_page, args=(item["notice_id"],))
                if item["read_at"] is None and right.button(text("mark_read", language), key=f"notification-read-{item['notification_id']}"):
                    service.mark_read(account_id, item["notification_id"])
                    st.rerun()
    else:
        st.info(text("notifications_empty", language))
    st.subheader(text("notification_preferences", language))
    prefs = service.preferences(account_id)
    fields = (("relevant_notices", "pref_relevant"), ("more_information", "pref_more"),
              ("reminder_7_days", "pref_7"), ("reminder_3_days", "pref_3"), ("reminder_1_day", "pref_1"))
    values = {key: st.checkbox(text(label, language), value=prefs[key], key=f"pref-{key}") for key, label in fields}
    if st.button(text("save_preferences", language), key="save-notification-preferences"):
        service.save_preferences(account_id, values)
        st.success(text("saved_preferences", language))


def _explore(st, library: NoticeLibrary, account: dict, language: str) -> None:
    st.header(text("explore", language))
    notices = library.list_published()
    if not notices:
        st.info(text("no_notices", language))
        return
    issuers = sorted({notice.issuing_authority for notice in notices if notice.issuing_authority})
    left, middle, right, final = st.columns([2, 1, 1, 1])
    query = left.text_input(text("search", language), key="published_notice_search")
    lang_choice = middle.selectbox(text("filter_language", language), ["", "en", "te", "hi", "mixed"],
                                  format_func=lambda code: _language_name(code, language), key="notice_language_filter")
    issuer_choice = right.selectbox(text("filter_issuer", language), [""] + issuers,
                                   format_func=lambda value: value or text("all_issuers", language), key="notice_issuer_filter")
    cutoff = final.date_input(text("deadline_before", language), value=None, key="notice_deadline_filter")
    filtered = library.list_published(query=query, language=lang_choice, issuer=issuer_choice,
                                      deadline_before=cutoff.isoformat() if isinstance(cutoff, date) else "")
    if not filtered:
        st.info(text("no_matches", language))
        return
    for notice in filtered:
        with st.container(border=True):
            st.subheader(notice.title)
            if notice.issuing_authority:
                st.caption(f"{text('issuer', language)}: {notice.issuing_authority}")
            _deadline_line(st, notice, language)
            _date_citations(st, notice, notice.analysis.metadata.title_evidence_ids, language)
            st.button(text("open_details", language), key=f"open-notice-{notice.notice_id}",
                      on_click=_open_notice_page, args=(notice.notice_id,))


def _for_you(st, library: NoticeLibrary, account: dict, profile: dict[str, object], language: str) -> None:
    st.header(text("for_you", language))
    st.caption(text("for_you_intro", language))
    if not profile:
        st.warning(text("profile_empty", language))
        st.link_button(text("update_profile", language), "/account/profile")
    notices = library.list_published()
    if not notices:
        st.info(text("no_notices", language))
        return
    groups = (
        ("reviewed_requirements_met", "match_reviewed"),
        ("requirements_met_so_far", "match_partial"),
        ("needs_information", "match_unknown"),
        ("does_not_meet", "match_fail"),
    )
    results = [evaluate_notice(notice, profile) for notice in notices]
    for status, summary_key in groups:
        matching = [result for result in results if result.status == status]
        if not matching:
            continue
        st.subheader(text(summary_key, language))
        for result in matching:
            _match_card(st, library, result, account, language)


def _match_card(st, library: NoticeLibrary, result, account: dict, language: str) -> None:
    notice = result.notice
    with st.container(border=True):
        st.markdown(f"**{notice.title}**")
        if notice.issuing_authority:
            st.caption(f"{text('issuer', language)}: {notice.issuing_authority}")
        st.write(text({
            "reviewed_requirements_met": "match_reviewed",
            "requirements_met_so_far": "match_partial",
            "does_not_meet": "match_fail",
            "needs_information": "match_unknown",
        }[result.status], language))
        if not result.coverage_complete and result.status in {"requirements_met_so_far", "needs_information"}:
            st.caption(text("eligibility_uncertain", language))
        _condition_explanations(st, result, language)
        _deadline_line(st, notice, language)
        st.button(text("open_details", language), key=f"for-you-details-{notice.notice_id}",
                  on_click=_open_notice_page, args=(notice.notice_id,))


def _details(st, library: NoticeLibrary, account: dict, profile: dict[str, object], language: str) -> None:
    notice_id = st.session_state.get("selected_library_notice")
    if not notice_id:
        st.info(text("choose_notice", language))
        return
    try:
        notice = library.get_for_account(account["account_id"], notice_id)
        pdf_bytes = library.get_pdf_for_account(account["account_id"], notice_id)
    except NoticeUnavailable:
        st.info(text("choose_notice", language))
        st.session_state.pop("selected_library_notice", None)
        return
    st.header(text("details", language))
    st.title(notice.title)
    if notice.issuing_authority:
        st.write(f"**{text('issuer', language)}:** {notice.issuing_authority}")
    if notice.publication_date:
        st.write(f"**{text('publication_date', language)}:** {notice.publication_date}")
    _date_citations(st, notice, notice.analysis.metadata.title_evidence_ids, language)
    _deadline_line(st, notice, language, expanded=True)
    st.download_button(text("read_pdf", language), pdf_bytes, file_name="notice.pdf",
                       mime="application/pdf", key=f"download-notice-{notice.notice_id}")
    _application_links(st, notice, language)
    if notice.analysis.fees:
        st.subheader(text("fees", language))
        for fee in notice.analysis.fees:
            fee_label = text(fee.fee_type, language) if fee.fee_type in UI else fee.fee_type.replace("_", " ").title()
            fee_value = fee.source_text or (f"₹{fee.amount_inr:,.2f}" if fee.amount_inr is not None else text("not_stated", language))
            st.write(f"{fee_label}: {fee_value}")
            if fee.applies_to_category:
                st.caption(f"{fee.applies_to_category}")
            if fee.waived_for:
                st.caption(f"{fee.waived_for}")
            _show_evidence(st, notice, fee.evidence_ids, language)
    if notice.analysis.required_documents:
        st.subheader(text("documents", language))
        for document in notice.analysis.required_documents:
            st.write(f"{document.source_name or document.canonical_name} — {document.requirement_type.value}")
            _show_evidence(st, notice, document.evidence_ids, language)
    st.subheader(text("eligibility", language))
    match = evaluate_notice(notice, profile)
    st.write(text({
        "reviewed_requirements_met": "match_reviewed",
        "requirements_met_so_far": "match_partial",
        "does_not_meet": "match_fail",
        "needs_information": "match_unknown",
    }[match.status], language))
    _condition_explanations(st, match, language)
    if notice.analysis.eligibility is None:
        st.info(text("no_eligibility", language))
    if not match.coverage_complete:
        st.caption(text("eligibility_uncertain", language))


def _admin(st, library: NoticeLibrary, store: AuthStore, account: dict, language: str) -> None:
    # Re-check the persisted role every render; a hidden navigation item is not
    # an authorization boundary.
    if not store.is_admin(account["account_id"]):
        st.error(text("admin_only", language))
        return
    st.header(text("admin", language))
    upload_tab, manage_tab = st.tabs([text("admin_upload", language), text("admin", language)])
    with upload_tab:
        uploaded = st.file_uploader(text("admin_upload", language), type=["pdf"], key="admin-notice-pdf")
        default_title = ""
        if uploaded:
            digest_key = __import__("hashlib").sha256(uploaded.getvalue()).hexdigest()
            st.session_state["admin_upload_digest"] = digest_key
            prior = st.session_state.get("admin_analysis")
            if prior and st.session_state.get("admin_analysis_digest") == digest_key:
                default_title = prior.analysis.metadata.title or ""
        title = st.text_input(text("display_title", language), value=default_title, key="admin-notice-title")
        if st.button(text("analyze_save", language), type="primary", disabled=uploaded is None,
                     key="admin-analyze-notice"):
            try:
                with st.spinner(text("analyze_save", language)):
                    analyzed = initial_analysis(uploaded.getvalue(), uploaded.name)
                saved = library.create_draft(account["account_id"], uploaded.getvalue(), analyzed.analysis, title)
                st.session_state["admin_analysis"] = analyzed
                st.session_state["admin_analysis_digest"] = digest_key
                st.session_state["admin_selected_notice"] = saved.notice_id
                st.success(text("draft_saved", language))
            except DuplicateNotice:
                st.info(text("duplicate", language))
            except Exception:
                LOG.exception("Admin notice upload failed")
                st.error(text("analysis_failed", language))
        if analyzed := st.session_state.get("admin_analysis"):
            _admin_preview(st, analyzed.analysis, language)
    with manage_tab:
        try:
            notices = library.list_admin(account["account_id"])
        except AuthorizationError:
            st.error(text("admin_only", language))
            return
        if not notices:
            st.info(text("no_notices", language))
            return
        labels = {notice.notice_id: notice.title for notice in notices}
        selected = st.selectbox(text("details", language), list(labels),
                                format_func=lambda notice_id: labels[notice_id],
                                key="admin_selected_notice")
        notice = next(item for item in notices if item.notice_id == selected)
        st.subheader(notice.title)
        st.caption(text("status_published" if notice.publication_state == "published" else "status_draft", language))
        st.caption(text("admin_review", language))
        try:
            pdf_bytes = library.get_pdf_for_account(account["account_id"], notice.notice_id)
            st.download_button(text("read_pdf", language), pdf_bytes, file_name="notice.pdf",
                               mime="application/pdf", key=f"admin-download-{notice.notice_id}")
        except NoticeUnavailable:
            st.error(text("analysis_failed", language))
        _admin_preview(st, notice.analysis, language)
        if st.button(text("reanalyze", language), key=f"reanalyze-{notice.notice_id}"):
            try:
                fresh = initial_analysis(pdf_bytes, "notice.pdf")
                updated = library.update_analysis(account["account_id"], notice.notice_id,
                                                  fresh.analysis, notice.title)
                st.session_state.pop(f"reviewed-{notice.notice_id}", None)
                st.success(text("draft_saved", language))
                st.rerun()
            except Exception:
                LOG.exception("Admin notice reanalysis failed")
                st.error(text("analysis_failed", language))
        coverage_possible = has_reviewable_eligibility_coverage(notice.analysis)
        checked = st.checkbox(text("review_complete", language), value=notice.eligibility_reviewed,
                              disabled=not coverage_possible, key=f"reviewed-{notice.notice_id}")
        if notice.eligibility_reviewed:
            reviewer = library.store.account_by_id(notice.eligibility_reviewed_by)["email"]
            reviewed_at = notice.eligibility_reviewed_at or ""
            st.caption(text("review_saved", language).format(reviewer=reviewer, reviewed_at=reviewed_at))
        review_button = text("save_review", language)
        if st.button(review_button, disabled=not coverage_possible and checked,
                     key=f"save-review-{notice.notice_id}"):
            try:
                library.set_eligibility_review(account["account_id"], notice.notice_id,
                                               bool(checked and coverage_possible))
                st.rerun()
            except (AuthorizationError, ValueError):
                LOG.exception("Admin eligibility review update failed")
                st.error(text("analysis_failed", language))
        if notice.publication_state == "published":
            if st.button(text("unpublish", language), key=f"unpublish-{notice.notice_id}"):
                library.set_publication(account["account_id"], notice.notice_id, False)
                st.session_state.pop("selected_library_notice", None)
                st.rerun()
        elif st.button(text("publish", language), key=f"publish-{notice.notice_id}"):
            library.set_publication(account["account_id"], notice.notice_id, True)
            st.rerun()
        confirm = st.checkbox(text("confirm_remove", language), key=f"confirm-remove-{notice.notice_id}")
        if st.button(text("remove", language), disabled=not confirm, key=f"remove-{notice.notice_id}"):
            library.remove(account["account_id"], notice.notice_id)
            st.session_state.pop("selected_library_notice", None)
            st.rerun()


def _admin_preview(st, analysis, language: str) -> None:
    if analysis.metadata.issuing_authority:
        st.write(f"{text('issuer', language)}: {analysis.metadata.issuing_authority}")
    _render_conditions(st, analysis, language)


def _render_conditions(st, analysis, language: str) -> None:
    if analysis.eligibility is None:
        st.info(text("no_eligibility", language))
        return
    for condition in iter_conditions(analysis.eligibility):
        st.write(_condition_text(condition, language))
        _show_evidence(st, analysis, condition.evidence_ids, language)


def _condition_explanations(st, result, language: str) -> None:
    if not result.explanation.conditions:
        st.info(text("no_eligibility", language))
        return
    st.markdown(f"**{text('all_requirements', language)}**")
    for item in result.explanation.conditions:
        st.write(f"{_condition_by_id(result.notice.analysis.eligibility, item.condition_id, language)} — {item.status.value}")
        if item.status == EvalStatus.UNKNOWN:
            st.caption(f"{text('candidate_value', language)}: {text('not_stated', language)}")
        _show_evidence(st, result.notice, item.evidence_ids, language)


def _condition_by_id(group, condition_id: str, language: str) -> str:
    return next((_condition_text(condition, language) for condition in iter_conditions(group)
                 if condition.condition_id == condition_id), text("no_eligibility", language))


def _condition_text(condition: Condition, language: str) -> str:
    attribute_labels = {
        "marks_percentage": ("Marks / percentage", "మార్కులు / శాతం", "अंक / प्रतिशत"),
        "current_class": ("Current class", "ప్రస్తుత తరగతి", "वर्तमान कक्षा"),
        "previous_class": ("Previous class", "మునుపటి తరగతి", "पिछली कक्षा"),
        "current_school_type": ("Current school type", "ప్రస్తుత పాఠశాల రకం", "वर्तमान विद्यालय का प्रकार"),
        "previous_school_type": ("Previous school type", "మునుపటి పాఠశాల రకం", "पिछले विद्यालय का प्रकार"),
        "annual_family_income_inr": ("Annual family income (INR)", "వార్షిక కుటుంబ ఆదాయం (INR)", "वार्षिक पारिवारिक आय (INR)"),
        "attempt_count": ("Number of attempts", "ప్రయత్నాల సంఖ్య", "प्रयासों की संख्या"),
        "age": ("Age", "వయస్సు", "आयु"),
        "date_of_birth": ("Date of birth", "పుట్టిన తేదీ", "जन्म तिथि"),
        "category": ("Category", "వర్గం", "श्रेणी"),
        "education_level": ("Education level", "విద్యా స్థాయి", "शिक्षा स्तर"),
    }
    ops = {
        Comparator.GT: ("is greater than", "కంటే ఎక్కువ", "से अधिक है"),
        Comparator.GTE: ("is at least", "కనీసం", "कम से कम है"),
        Comparator.LT: ("is less than", "కంటే తక్కువ", "से कम है"),
        Comparator.LTE: ("is at most", "గరిష్ఠంగా", "अधिकतम है"),
        Comparator.EQ: ("is", "అంటే", "है"),
        Comparator.NEQ: ("is not", "కాదు", "नहीं है"),
        Comparator.IN: ("is one of", "వీటిలో ఒకటి", "इनमें से एक है"),
        Comparator.NOT_IN: ("is not", "కాదు", "इनमें नहीं है"),
        Comparator.BETWEEN: ("is between", "మధ్య ఉండాలి", "के बीच है"),
        Comparator.EXISTS: ("must be provided", "తప్పనిసరిగా ఇవ్వాలి", "देना आवश्यक है"),
        Comparator.NOT_EXISTS: ("must not be provided", "ఇవ్వకూడదు", "नहीं देना चाहिए"),
    }
    index = {"en": 0, "te": 1, "hi": 2}.get(language, 0)
    label = attribute_labels.get(condition.attribute, (condition.attribute, condition.attribute, condition.attribute))[index]
    comparator = ops[condition.comparator][index]
    value = "" if condition.value is None else f" {condition.value}"
    return f"{label} {comparator}{value}"


def _show_evidence(st, source, evidence_ids, language: str) -> None:
    if not evidence_ids:
        return
    analysis = getattr(source, "analysis", source)
    spans = {item.evidence_id: item for item in analysis.evidence}
    for evidence_id in dict.fromkeys(evidence_ids):
        span = spans.get(evidence_id)
        if span:
            st.caption(f"{text('page', language)} {span.page_number} · {span.text}")


def _date_citations(st, source, evidence_ids, language: str) -> None:
    _show_evidence(st, source, evidence_ids, language)


def _deadline_line(st, notice, language: str, expanded: bool = False) -> None:
    if not notice.deadlines:
        return
    for deadline in notice.deadlines:
        label = text("deadline", language) if deadline["date_type"] == "application_deadline" else deadline["date_type"].replace("_", " ").title()
        st.write(f"**{label}:** {deadline.get('value') or text('not_stated', language)}")
        if expanded:
            _show_evidence(st, notice, deadline.get("evidence_ids", []), language)


def _application_links(st, notice, language: str) -> None:
    links = [link for link in notice.analysis.links if link.link_type == "application_portal" and not link.suspicious]
    if links:
        for index, link in enumerate(links):
            if urlparse(link.url).scheme in {"http", "https"}:
                st.link_button(f"{text('application_link', language)}: {link.description or link.url}", link.url,
                               key=f"application-link-{notice.notice_id}-{index}")
                _show_evidence(st, notice, link.evidence_ids, language)
    else:
        st.caption(text("no_application_link", language))


def _language_name(code: str, language: str) -> str:
    names = {
        "": ("All languages", "అన్ని భాషలు", "सभी भाषाएँ"),
        "en": ("English", "ఇంగ్లీష్", "अंग्रेज़ी"),
        "te": ("Telugu", "తెలుగు", "तेलुगु"),
        "hi": ("Hindi", "హిందీ", "हिंदी"),
        "mixed": ("Mixed", "మిశ్రమం", "मिश्रित"),
    }
    return names.get(code, names[""])[{"en": 0, "te": 1, "hi": 2}.get(language, 0)]
