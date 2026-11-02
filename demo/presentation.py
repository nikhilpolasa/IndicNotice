"""Conservative product facts and localized views; research extraction stays unchanged."""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from difflib import SequenceMatcher
import re
from urllib.parse import urlparse

from demo.i18n import tr
from services.nlp.semantic.canonical import iter_conditions

ORG = re.compile(r"^(.{3,110}?\b(?:Sangathan|University|Council|Board|Department|Ministry|Commission|Directorate|Society|Institute|Authority))(?:\s*\([A-Z0-9 .&-]{2,16}\))?(?=\s*(?:Admission|Recruitment|Notice|Notification|Schedule|Examination|$))", re.I)
HEADER_AUTHORITY = re.compile(r"^\(?([A-Z]{2,10}(?:\s+[A-Z][A-Z]+){1,3}(?:,\s*[A-Z][A-Z]+){0,2})\)?$")


def resolve_metadata(analysis):
    """Resolve only a named organization explicitly present in title evidence."""
    if analysis.metadata.issuing_authority:
        return analysis
    ids = set(analysis.metadata.title_evidence_ids)
    for span in analysis.evidence:
        match = ORG.match(" ".join(span.text.split()))
        if span.evidence_id in ids and match:
            metadata = analysis.metadata.model_copy(update={
                "issuing_authority": match.group(0).strip(),
                "issuing_authority_evidence_ids": [span.evidence_id],
            })
            return analysis.model_copy(update={"metadata": metadata})
    # Some notices put their office name in a short, explicit masthead instead
    # of repeating it in the title (for example, an acronym and jurisdiction).
    for span in analysis.evidence:
        text = " ".join(span.text.split())
        if len(text) <= 80 and text.startswith("("):
            match = HEADER_AUTHORITY.fullmatch(text)
            if match:
                metadata = analysis.metadata.model_copy(update={
                    "issuing_authority": match.group(1).strip(),
                    "issuing_authority_evidence_ids": [span.evidence_id],
                })
                return analysis.model_copy(update={"metadata": metadata})
    return analysis


def today():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


MONTHS = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "te": ("జనవరి", "ఫిబ్రవరి", "మార్చి", "ఏప్రిల్", "మే", "జూన్", "జూలై", "ఆగస్టు", "సెప్టెంబర్", "అక్టోబర్", "నవంబర్", "డిసెంబర్"),
    "hi": ("जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"),
}


def format_date(value, lang):
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return value or tr("missing", lang)
    return f"{parsed.day} {MONTHS[lang][parsed.month - 1]} {parsed.year}"


def deadline_status(analysis, *, on=None):
    on = on or today()
    values = {}
    for item in analysis.dates:
        if item.date_type.value in {"application_open", "application_deadline"}:
            try:
                values.setdefault(item.date_type.value, []).append(date.fromisoformat(item.value))
            except (ValueError, TypeError):
                pass
    deadlines = values.get("application_deadline", [])
    starts = values.get("application_open", [])
    if not deadlines or len(set(deadlines)) > 1:
        return "status_unknown"
    if deadlines[0] < on:
        return "status_closed"
    if starts and min(starts) > on:
        return "status_upcoming"
    if starts and min(starts) <= on:
        return "status_open"
    return "status_unknown"


def spans_for(analysis, ids):
    ids = set(ids)
    output, keys = [], []
    for span in analysis.evidence:
        if span.evidence_id not in ids:
            continue
        key = re.sub(r"\W+", "", span.text.casefold())
        if any(key == previous or (len(key) > 60 and SequenceMatcher(None, key, previous).ratio() > .94) for previous in keys):
            continue
        keys.append(key)
        output.append(span)
    return output


def view_source(st, analysis, ids, lang):
    spans = spans_for(analysis, ids)
    if not spans:
        return
    with st.expander(tr("view_source", lang)):
        st.caption(tr("original_source", lang))
        for span in spans:
            st.caption(f'{tr("page", lang)} {span.page_number}')
            st.text(span.text)


def referral_ids(analysis):
    return [s.evidence_id for s in analysis.evidence
            if re.search(r"eligibility|admission.{0,30}guideline|guideline.{0,30}admission|అర్హత|पात्रता", s.text, re.I)
            and re.search(r"visit|guidelines|website|మార్గదర్శక|సందర్శించ|दिशानिर्देश|देखें", s.text, re.I)]


def condition_label(condition, lang):
    operators = {">": "more_than", ">=": "at_least", "<": "less_than", "<=": "at_most",
                 "==": "equals", "!=": "not_equals", "in": "one_of", "not_in": "not_one_of",
                 "between": "between", "exists": "must_provide", "not_exists": "must_not_provide"}
    op = condition.comparator.value
    value = condition.value
    def label(v):
        return tr(v, lang) if isinstance(v, str) else str(v)
    shown = ", ".join(label(v) for v in value) if isinstance(value, (list, tuple)) else "" if value is None else label(value)
    output = f'{tr(condition.attribute, lang)} {tr(operators.get(op, op), lang)} {shown}'.strip()
    if condition.reference_date:
        output += f' · {tr("as_on", lang)} {format_date(condition.reference_date, lang)}'
    return output


def render_rules(st, analysis, group, lang):
    if group is None:
        st.info(tr("eligibility_missing", lang))
        ids = referral_ids(analysis)
        if ids:
            st.info(tr("guidelines", lang))
            view_source(st, analysis, ids[:1], lang)
        return
    st.caption(tr("all_rules" if group.operator == "AND" else "any_rule", lang))
    if group.applies_when:
        st.caption(tr("conditional", lang))
        render_rules(st, analysis, group.applies_when, lang)
    for child in group.children:
        if hasattr(child, "children"):
            render_rules(st, analysis, child, lang)
        else:
            with st.container(border=True):
                st.write(condition_label(child, lang))
                if child.applies_when:
                    st.caption(tr("conditional", lang))
                    render_rules(st, analysis, child.applies_when, lang)
                view_source(st, analysis, child.evidence_ids, lang)


def portal_label(link, analysis, lang):
    # A label must be adjacent to this exact URL on the same source line.
    for span in spans_for(analysis, link.evidence_ids):
        for line in span.text.splitlines():
            location = line.find(link.url)
            if location < 0:
                location = line.find(link.url.removeprefix("https://").removeprefix("http://"))
            if location < 0:
                continue
            prefix = line[:location].strip(" :?-–—")
            if 0 < len(prefix) <= 60 and ":" in line[:location]:
                match = re.fullmatch(r"Class\s*[-–]?\s*([IVX]+|[0-9]+)", prefix, re.I)
                if match:
                    value = "I" if match[1] == "1" else match[1].upper()
                    return tr("class_portal", lang).format(value=value)
                match = re.fullmatch(r"Balvatika\s*[-–]?\s*([IVX]+|[0-9]+)", prefix, re.I)
                if match:
                    return tr("balvatika_portal", lang).format(value=match[1].upper())
    return tr("application_portal", lang)


def render_links(st, analysis, lang):
    seen = set()
    for link in analysis.links:
        parsed = urlparse(link.url)
        if link.link_type != "application_portal" or link.url in seen:
            continue
        seen.add(link.url)
        if link.suspicious or parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            st.warning(tr("unsafe_link", lang))
            continue
        st.link_button(portal_label(link, analysis, lang), link.url)
        st.caption(parsed.hostname)
        view_source(st, analysis, link.evidence_ids, lang)


def render_fees(st, analysis, lang):
    st.subheader(tr("application_fee", lang))
    if not analysis.fees:
        st.info(tr("fee_missing", lang))
    for fee in analysis.fees:
        st.write(f'{tr(fee.fee_type, lang)}: ' + (f"₹{fee.amount_inr:,.2f}" if fee.amount_inr is not None else tr("fee_missing", lang)))
        if fee.applies_to_category:
            st.caption(f'{tr("applies", lang)}: {tr(fee.applies_to_category, lang)}')
        if fee.waived_for:
            st.caption(f'{tr("waived", lang)}: {tr(fee.waived_for, lang)}')
        view_source(st, analysis, fee.evidence_ids, lang)


def render_application(st, analysis, lang):
    render_fees(st, analysis, lang)
    st.subheader(tr("how_apply", lang))
    seen = set()
    action_signals = {
        "submit_application": r"submit.{0,30}application|application.{0,30}submit|आवेदन.{0,30}(?:जमा|भरें)|(?:जमा|भरें).{0,30}आवेदन|దరఖాస్తు.{0,30}సమర్పి",
        "register": r"\bregister\b|पंजीकरण|पंजीकृत|నమోదు",
        "pay_fee": r"fee|शुल्क|ఫీజు|రుసుము",
        "upload_document": r"upload.{0,40}(?:document|certificate)|(?:document|certificate).{0,40}upload|अपलोड|స్కాన్ చేసి upload|అప్‌లోడ్",
        "obtain_document": r"obtain.{0,30}(?:document|certificate)|प्रमाण.?पत्र.{0,20}बनवा|ధృవీకరణ పత్రం",
        "download_admit_card": r"admit.?card|प्रवेश.?पत्र|హాల్.?టికెట్",
        "correction": r"correction|सुधार|సవరణ",
        "attend_exam": r"attend.{0,20}exam|परीक्षा में शामिल|परीक्षा में उपस्थित|పరీక్షకు హాజరు",
        "attend_interview": r"attend.{0,20}interview|साक्षात्कार में शामिल|ఇంటర్వ్యూకు హాజరు",
        "verify_documents": r"candidate.{0,40}verify|candidate.{0,40}document verification|उम्मीदवार.{0,40}सत्यापन|విద్యార్థి.{0,40}ధృవీకరణ",
    }
    for action in analysis.actions:
        if not action.evidence_ids:
            continue
        # Do not turn institutional verification duties into applicant instructions.
        if re.search(r"responsib|जिम्मे|विद्यालय.{0,35}(?:जिम्मे|सत्यापन)|పాఠశాల.{0,35}ధృవీక|school.*verif", action.description, re.I):
            continue
        signal = action_signals.get(action.action_type.value)
        if not signal or not re.search(signal, action.description, re.I):
            continue
        key = (action.action_type.value, action.applies_when.model_dump_json() if action.applies_when else "")
        if key in seen:
            continue
        seen.add(key)
        st.write(tr("action_" + action.action_type.value, lang))
        if action.applies_when:
            render_rules(st, analysis, action.applies_when, lang)
        if action.is_optional:
            st.caption(tr("optional", lang))
        view_source(st, analysis, action.evidence_ids, lang)
    if not seen:
        st.caption(tr("steps_missing", lang))
    render_links(st, analysis, lang)


def render_documents(st, analysis, lang):
    if not analysis.required_documents:
        st.info(tr("documents_missing", lang))
        ids = referral_ids(analysis)
        if ids:
            st.caption(tr("guidelines", lang))
            view_source(st, analysis, ids[:1], lang)
    for document in analysis.required_documents:
        with st.container(border=True):
            st.write(tr(document.canonical_name, lang))
            st.caption(tr(document.requirement_type.value, lang))
            if document.alternatives:
                st.write(tr("alternatives", lang) + ": " + ", ".join(tr(v, lang) for v in document.alternatives))
            if document.applies_when:
                render_rules(st, analysis, document.applies_when, lang)
            view_source(st, analysis, document.evidence_ids, lang)


def detected_languages(analysis):
    text = " ".join(s.text for s in analysis.evidence)
    counts = {"en": len(re.findall(r"[A-Za-z]", text)),
              "te": len(re.findall(r"[\u0c00-\u0c7f]", text)),
              "hi": len(re.findall(r"[\u0900-\u097f]", text))}
    return [code for code, count in counts.items() if count >= 30]


def render_facts(st, analysis, page, lang):
    a = resolve_metadata(analysis)
    if page == "overview":
        st.caption(tr("original_title", lang))
        st.subheader(a.metadata.title or tr("missing", lang))
        view_source(st, a, a.metadata.title_evidence_ids, lang)
        left, right = st.columns(2)
        with left:
            st.caption(tr("authority", lang))
            st.write(a.metadata.issuing_authority or tr("missing", lang))
            view_source(st, a, a.metadata.issuing_authority_evidence_ids, lang)
        with right:
            st.caption(tr("notice_type", lang))
            # The canonical schema does not carry category evidence IDs, so do
            # not present the classifier's label as a source-verified fact.
            st.write(tr("missing", lang))
        st.write(tr(deadline_status(a), lang))
        for item in a.dates:
            if item.date_type.value in {"application_open", "application_deadline"}:
                st.write(f'{tr(item.date_type.value, lang)}: {format_date(item.value, lang)}')
                view_source(st, a, item.evidence_ids, lang)
        st.caption(tr("coverage", lang))
        st.info(tr("partial", lang) if a.eligibility else tr("eligibility_missing", lang))
        st.caption(tr("detected_languages", lang) + ": " + ", ".join(tr("language_" + code, lang) for code in detected_languages(a)))
        render_fees(st, a, lang)
        render_links(st, a, lang)
    elif page == "dates":
        st.info(tr(deadline_status(a), lang))
        if not a.dates:
            st.info(tr("missing", lang))
        for item in a.dates:
            with st.container(border=True):
                st.write(f'{tr(item.date_type.value, lang)}: {format_date(item.value, lang)}')
                if item.end_value:
                    st.caption(tr("to", lang) + " " + format_date(item.end_value, lang))
                if item.time:
                    st.caption(item.time)
                if item.is_tentative:
                    st.caption(tr("tentative", lang))
                view_source(st, a, item.evidence_ids, lang)
        render_application(st, a, lang)
    elif page == "documents":
        render_documents(st, a, lang)
    elif page == "rules":
        render_rules(st, a, a.eligibility, lang)
    elif page == "sources":
        facts = [(tr("title", lang), a.metadata.title_evidence_ids),
                 (tr("authority", lang), a.metadata.issuing_authority_evidence_ids)]
        facts += [(tr(d.date_type.value, lang) + " ? " + format_date(d.value, lang), d.evidence_ids) for d in a.dates]
        facts += [(portal_label(link, a, lang), link.evidence_ids) for link in a.links if link.link_type == "application_portal"]
        facts += [(tr(d.canonical_name, lang), d.evidence_ids) for d in a.required_documents]
        facts += [(condition_label(c, lang), c.evidence_ids) for c in iter_conditions(a.eligibility)]
        facts = [(label, ids) for label, ids in facts if spans_for(a, ids)]
        if facts:
            selected = st.selectbox(tr("source_fact", lang), range(len(facts)), format_func=lambda i: facts[i][0])
            view_source(st, a, facts[selected][1], lang)
        else:
            st.info(tr("no_supported_sources", lang))
