"""Task-oriented, session-private Streamlit notice reader."""
from __future__ import annotations
import logging
from hashlib import sha256
from datetime import date
from demo.i18n import LANGUAGES, tr
from demo.pipeline import evidence_for, profile_field_specs, eligibility_outcome
from demo.product import session_analysis, clear_notice, eligibility_display_state, ADVANCED_MODE
from demo.questions import answer_notice
from demo.notices_ui import UI as NOTICE_UI, render_notice_page, text as notice_text
from services.auth.notices import NoticeLibrary
from services.auth.notifications import NotificationService
from services.nlp.semantic.canonical import iter_conditions
from indicnotice.schemas.eligibility import Comparator, ConditionGroup
from indicnotice.schemas.actions import get_action_execution_order

LOG = logging.getLogger(__name__)
_AUTH_STORE = None


def _auth_store():
    global _AUTH_STORE
    if _AUTH_STORE is None:
        from services.auth.store import AuthStore
        _AUTH_STORE = AuthStore()
    return _AUTH_STORE


def _authenticated_account(st):
    from services.auth.gateway import SESSION_COOKIE
    token = st.context.cookies.get(SESSION_COOKIE)
    return _auth_store().account_for_session(token)


def evidence(st, ids, result, lang):
    spans = evidence_for(ids, result.analysis)
    if spans:
        with st.expander(tr("sources", lang)):
            for span in spans:
                st.caption(f'{tr("page", lang)} {span["page_number"]}')
                st.text(span["text"])


def rules(st, group, result, lang):
    if group is None:
        st.info(tr("missing", lang))
        return
    conjunction = {"en": {"AND": "All of these", "OR": "At least one of these"},
                   "te": {"AND": "ఇవన్నీ", "OR": "వీటిలో కనీసం ఒకటి"},
                   "hi": {"AND": "ये सभी", "OR": "इनमें से कम से कम एक"}}
    st.write(conjunction[lang][group.operator])
    if group.applies_when:
        with st.expander(tr("conditional", lang), expanded=True):
            rules(st, group.applies_when, result, lang)
    for child in group.children:
        with st.container(border=True):
            if isinstance(child, ConditionGroup):
                rules(st, child, result, lang)
            else:
                st.text(child.source_text or f'{tr(child.attribute, lang)} {child.comparator.value} {child.value}')
                if child.applies_when:
                    st.caption(tr("conditional", lang))
                    rules(st, child.applies_when, result, lang)
                evidence(st, child.evidence_ids, result, lang)


def profile_form(st, result, lang, *, saved_profile=None, account_id=""):
    if result.analysis.eligibility is None:
        st.info(tr("missing", lang))
        return
    st.caption(tr("partial", lang))
    profile = {}
    eligibility_fingerprint = sha256(result.analysis.eligibility.model_dump_json().encode("utf-8")).hexdigest()[:12]
    profile_fingerprint = sha256(__import__("json").dumps(saved_profile or {}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    widget_scope = f"eligibility-widget-{account_id[:12]}-{result.analysis.document_id[:12]}-{eligibility_fingerprint}-{profile_fingerprint}"
    specs = profile_field_specs(result.analysis.eligibility)
    st.caption(tr("profile_fields_help", lang))
    for attribute, spec in specs.items():
        st.caption(f'{tr(attribute, lang)} · {tr("profile_required", lang)}')
        for source_text in spec["source_texts"]:
            st.text(f'{tr("source_rule", lang)}: {source_text}')
        evidence(st, spec["evidence_ids"], result, lang)
    with st.form("eligibility-profile"):
        for attribute, spec in specs.items():
            label = tr(attribute, lang)
            supplied = st.checkbox(f'{tr("provide", lang)}: {label}', value=attribute in (saved_profile or {}), key=f"{widget_scope}-provide-{attribute}")
            if spec["kind"] == "presence":
                options = [None, True, False]
                value = st.selectbox(label, options, index=options.index((saved_profile or {}).get(attribute)) if (saved_profile or {}).get(attribute) in options else 0, format_func=lambda v: tr("UNKNOWN", lang) if v is None else tr("yes" if v else "no", lang), key=f"{widget_scope}-value-{attribute}")
            elif spec["kind"] == "number":
                value = st.number_input(label, value=(saved_profile or {}).get(attribute), key=f"{widget_scope}-value-{attribute}")
            elif spec["kind"] == "date":
                saved_date = (saved_profile or {}).get(attribute)
                try:
                    saved_date = date.fromisoformat(saved_date) if isinstance(saved_date, str) else saved_date
                except ValueError:
                    saved_date = None
                value = st.date_input(label, value=saved_date, min_value=date(1900, 1, 1), key=f"{widget_scope}-value-{attribute}")
            elif spec["kind"] == "select":
                saved_value = (saved_profile or {}).get(attribute)
                options = [None, *spec["options"]]
                if saved_value is not None and saved_value not in options:
                    options.append(saved_value)
                options.append("__other__")
                selected_index = options.index(saved_value) if saved_value in options else 0
                value = st.selectbox(label, options, index=selected_index, format_func=lambda v: tr("UNKNOWN", lang) if v is None else tr("other", lang) if v == "__other__" else tr(v, lang), key=f"{widget_scope}-value-{attribute}")
                if value == "__other__":
                    value = st.text_input(tr("other", lang), key=f"{widget_scope}-value-other-{attribute}")
            else:
                # Extracted enum values are requirements, not all possible candidate values.
                value = st.text_input(label, key=f"{widget_scope}-value-{attribute}")
            if supplied and value not in (None, ""):
                profile[attribute] = None if spec["kind"] == "presence" and value is False else value.isoformat() if hasattr(value, "isoformat") else value
        submitted = st.form_submit_button(tr("check", lang), type="primary")
    if submitted:
        state, explanation = eligibility_outcome(profile, result.analysis)
        st.session_state["candidate_profile"] = profile
        st.session_state["eligibility_response"] = (state, explanation)
    if response := st.session_state.get("eligibility_response"):
        state, explanation = response
        submitted_profile = st.session_state.get("candidate_profile", {})
        shown = eligibility_display_state(state, result, submitted_profile)
        (st.success if shown == "PASS" else st.warning)(tr(shown, lang))
        lookup = {c.condition_id: c for c in iter_conditions(result.analysis.eligibility)}
        for entry in explanation.conditions:
            rule = lookup[entry.condition_id]
            with st.container(border=True):
                st.text(rule.source_text or tr(rule.attribute, lang))
                status = entry.status.value
                if rule.comparator in {Comparator.EXISTS, Comparator.NOT_EXISTS} and rule.attribute not in submitted_profile:
                    status = "UNKNOWN"
                st.write(tr("matched" if status == "PASS" else status, lang))
                evidence(st, list(entry.evidence_ids), result, lang)


def render(st, result, page, lang, *, saved_profile=None, account_id=""):
    a = result.analysis
    st.header(tr(page, lang))
    if page == "overview":
        st.text(a.metadata.title or tr("missing", lang))
        st.caption(tr("authority", lang))
        st.text(a.metadata.issuing_authority or tr("missing", lang))
        st.caption(f'{tr("page", lang)}: {result.ingestion.document.page_count}')
        evidence(st, a.metadata.title_evidence_ids + a.metadata.issuing_authority_evidence_ids, result, lang)
    elif page == "dates":
        if not a.dates:
            st.info(tr("missing", lang))
        for item in a.dates:
            with st.container(border=True):
                st.caption(tr(item.date_type.value, lang))
                st.text(item.value or item.source_text or tr("missing", lang))
                if item.end_value:
                    st.text(f'{tr("to", lang)} {item.end_value}')
                if item.is_tentative:
                    st.caption(tr("tentative", lang))
                if item.time:
                    st.text(item.time)
                evidence(st, item.evidence_ids, result, lang)
    elif page == "fees":
        if not a.fees:
            st.info(tr("missing", lang))
        for item in a.fees:
            with st.container(border=True):
                st.write(tr(item.fee_type, lang))
                st.subheader(tr("missing", lang) if item.amount_inr is None else f"₹{item.amount_inr:,.2f}")
                if item.applies_to_category:
                    st.text(f'{tr("applies", lang)}: {item.applies_to_category}')
                if item.waived_for:
                    st.text(f'{tr("waived", lang)}: {item.waived_for}')
                evidence(st, item.evidence_ids, result, lang)
        actions_by_id = {item.action_id: item for item in a.actions}
        for action in get_action_execution_order(a.actions):
            with st.container(border=True):
                st.text(action.description)
                for dependency in action.depends_on:
                    st.text(f'{tr("after", lang)}: {actions_by_id[dependency].description}')
                if action.applies_when:
                    rules(st, action.applies_when, result, lang)
                if action.is_optional:
                    st.caption(tr("optional", lang))
                evidence(st, action.evidence_ids, result, lang)
        for link in a.links:
            st.text(link.url)
            evidence(st, link.evidence_ids, result, lang)
    elif page == "documents":
        if not a.required_documents:
            st.info(tr("missing", lang))
        for item in a.required_documents:
            with st.container(border=True):
                st.write(tr(item.canonical_name, lang))
                st.text(item.source_name)
                st.caption(tr(item.requirement_type.value, lang))
                if item.alternatives:
                    st.text(tr("alternatives", lang) + ": " + ", ".join(tr(name, lang) for name in item.alternatives))
                if item.applies_when:
                    rules(st, item.applies_when, result, lang)
                if item.notes:
                    st.text(item.notes)
                evidence(st, item.evidence_ids, result, lang)
    elif page == "rules":
        rules(st, a.eligibility, result, lang)
    elif page == "check":
        profile_form(st, result, lang, saved_profile=saved_profile, account_id=account_id)
    elif page == "ask":
        st.caption(tr("question_help", lang))
        with st.form("question-form"):
            question = st.text_input(tr("question", lang), max_chars=2000)
            ask = st.form_submit_button(tr("ask", lang))
        if ask and question.strip():
            try:
                st.session_state["qa_response"] = answer_notice(question, result, st.session_state.get("candidate_profile", saved_profile), language=lang)
                st.session_state["qa_input"] = question
            except Exception:
                LOG.exception("Question answering failed")
                st.error(tr("qa_error", lang))
        elif ask:
            st.info(tr("question_empty", lang))
        if response := st.session_state.get("qa_response"):
            if response.answer_language != lang and st.session_state.get("qa_input"):
                response = answer_notice(st.session_state["qa_input"], result, st.session_state.get("candidate_profile", saved_profile), language=lang)
                st.session_state["qa_response"] = response
            st.text(response.answer_text)
            for citation in response.citations:
                with st.expander(f'{tr("page", lang)} {citation.page_number}'):
                    st.text(citation.text)
    elif page == "sources":
        for index, span in enumerate(a.evidence, 1):
            with st.expander(f'{tr("page", lang)} {span.page_number} · {index}'):
                st.text(span.text)


def main():
    import streamlit as st
    st.set_page_config(page_title="IndicNotice", page_icon="📄", layout="wide")
    st.markdown("""<style>
    .block-container {max-width: 1120px; padding-top: 2.5rem;}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px;}
    .stButton button[kind="primary"] {background:#126b65; border-color:#126b65;}
    .stButton button[kind="primary"]:disabled {color:#fff; background:#536c69; border-color:#536c69; opacity:1;}
    </style>""", unsafe_allow_html=True)
    account = _authenticated_account(st)
    if account is None:
        st.title("IndicNotice")
        st.info("Sign in to use IndicNotice.")
        st.link_button("Sign in or create an account", "/auth/login")
        st.stop()
    if st.session_state.get("auth_account_id") != account["account_id"]:
        st.session_state.clear()
        st.session_state["auth_account_id"] = account["account_id"]
    auth_store = _auth_store()
    saved_profile = auth_store.get_profile(account["account_id"])
    st.session_state.setdefault("candidate_profile", dict(saved_profile))
    lang = account.get("preferred_language", "en")
    notification_service = NotificationService(auth_store)
    unread_count = notification_service.unread_count(account["account_id"])
    sections = ["read", "explore", "for_you", "notifications", "details"]
    is_admin = auth_store.is_admin(account["account_id"])
    if is_admin:
        sections.append("admin")
    section = st.radio("IndicNotice", sections,
                       format_func=lambda key: (f"🔔 {notice_text(key, lang)} ({unread_count})" if key == "notifications" and unread_count else (f"🔔 {notice_text(key, lang)}" if key == "notifications" else notice_text(key, lang))),
                       horizontal=True, key="library_page", label_visibility="collapsed")
    with st.sidebar:
        st.title("IndicNotice")
        preferred = next((label for label, code in LANGUAGES.items() if code == account["preferred_language"]), "English")
        chosen = st.selectbox(tr("language", "en"), list(LANGUAGES), index=list(LANGUAGES).index(preferred))
        lang = LANGUAGES[chosen]
        if lang != account["preferred_language"]:
            auth_store.update_language(account["account_id"], lang)
            account["preferred_language"] = lang
            # The main navigation is rendered before this sidebar control.
            # Rerender once so every label uses the persisted language choice.
            st.rerun()
        st.caption(tr("privacy", lang))
        st.caption(f'{tr("authenticated_notice", lang)}: {account["email"]}')
        st.link_button(tr("my_profile", lang), "/account/profile")
        st.link_button(tr("account_settings", lang), "/account/settings")
        st.link_button(tr("logout", lang), "/auth/logout")
        uploaded = None
        analyze = False
        if section == "read":
            uploaded = st.file_uploader(tr("upload", lang), type=["pdf"], key=f'notice-upload-{st.session_state.get("upload_epoch", 0)}')
            digest = sha256(uploaded.getvalue()).hexdigest() if uploaded else None
            if st.session_state.get("upload_digest") and st.session_state["upload_digest"] != digest:
                clear_notice(st.session_state)
            analyze = st.button(tr("analyze", lang), type="primary", disabled=uploaded is None)
            if st.button(tr("clear", lang)):
                clear_notice(st.session_state)
                st.session_state["upload_epoch"] = st.session_state.get("upload_epoch", 0) + 1
                st.rerun()
    st.title("IndicNotice")
    st.caption(tr("tagline", lang))
    if section != "read":
        notice_library = NoticeLibrary(auth_store)
        render_notice_page(st, section, notice_library, auth_store, account, saved_profile, lang)
        return
    if analyze and uploaded:
        try:
            with st.spinner(tr("working", lang)):
                session_analysis(st.session_state, uploaded.getvalue(), uploaded.name)
        except Exception:
            LOG.exception("Upload analysis failed")
            st.error(tr("error", lang))
    result = st.session_state.get("demo_result")
    if result is None:
        st.header(tr("welcome", lang))
        st.write(tr("intro", lang))
        return
    status = "review_partial" if result.analysis.warnings else "reviewed"
    if result.mode == ADVANCED_MODE and not any(
        decision.promoted and decision.origin.value == "contextual"
        for decision in result.hybrid_diagnostics.decisions
    ):
        status = "review_no_additions"
    st.info(tr(status if result.mode == ADVANCED_MODE else "initial", lang))
    st.caption(tr("partial", lang))
    pages = ("overview", "dates", "fees", "documents", "rules", "check", "ask", "sources")
    page = st.radio(tr("overview", lang), pages, format_func=lambda key: tr(key, lang), horizontal=True, label_visibility="collapsed")
    render(st, result, page, lang, saved_profile=saved_profile, account_id=account["account_id"])
