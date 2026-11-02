"""Task-oriented, session-private Streamlit notice reader."""
from __future__ import annotations
import logging
from hashlib import sha256
from datetime import date
from demo.i18n import LANGUAGES, tr
from demo.pipeline import evidence_for, profile_field_specs, eligibility_outcome
from demo.product import session_analysis, clear_notice, eligibility_display_state, ADVANCED_MODE
from demo import presentation
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
                st.caption(tr("original_source", lang))
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
                st.write(presentation.condition_label(child, lang))
                if child.applies_when:
                    st.caption(tr("conditional", lang))
                    rules(st, child.applies_when, result, lang)
                presentation.view_source(st, result.analysis, child.evidence_ids, lang)


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
        presentation.render_facts(st, a, "overview", lang)
    elif page == "dates":
        presentation.render_facts(st, a, "dates", lang)
    elif page == "fees":
        presentation.render_application(st, a, lang)
    elif page == "documents":
        presentation.render_facts(st, a, "documents", lang)
    elif page == "rules":
        presentation.render_facts(st, a, "rules", lang)
    elif page == "check":
        profile_form(st, result, lang, saved_profile=saved_profile, account_id=account_id)
    elif page == "ask":
        st.caption(tr("question_help", lang))
        with st.form("question-form"):
            question = st.text_input(tr("question", lang), max_chars=2000)
            ask = st.form_submit_button(tr("ask", lang))
        if ask and question.strip():
            try:
                st.session_state["qa_response"] = answer_notice(question, result, st.session_state.get("candidate_profile", saved_profile))
                st.session_state["qa_input"] = question
            except Exception:
                LOG.exception("Question answering failed")
                st.error(tr("qa_error", lang))
        elif ask:
            st.info(tr("question_empty", lang))
        if response := st.session_state.get("qa_response"):
            st.text(response.answer_text)
            for citation in response.citations:
                with st.expander(f'{tr("page", lang)} {citation.page_number}'):
                    st.caption(tr("original_source", lang))
                    st.text(citation.text)
    elif page == "sources":
        presentation.render_facts(st, a, "sources", lang)


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
    top_left, top_lang, top_account = st.columns([6, 2, 1])
    with top_left:
        st.title("IndicNotice")
        st.caption(tr("tagline", lang))
    with top_lang:
        labels = list(LANGUAGES)
        preferred = next((label for label, code in LANGUAGES.items() if code == account["preferred_language"]), labels[0])
        chosen = st.selectbox(tr("language", lang), labels, index=labels.index(preferred), key="header-language")
        selected_lang = LANGUAGES[chosen]
        if selected_lang != account["preferred_language"]:
            auth_store.update_language(account["account_id"], selected_lang)
            account["preferred_language"] = selected_lang
            st.rerun()
    lang = account.get("preferred_language", "en")
    with top_account:
        with st.popover(tr("account", lang), use_container_width=True):
            st.link_button(tr("my_profile", lang), "/account/profile", use_container_width=True)
            st.link_button(tr("account_settings", lang), "/account/settings", use_container_width=True)
            st.link_button(tr("logout", lang), "/auth/logout", use_container_width=True)
    nav_labels = {"read": tr("understand", lang), "explore": notice_text("explore", lang),
                  "for_you": notice_text("for_you", lang), "notifications": notice_text("notifications", lang),
                  "details": notice_text("details", lang), "admin": notice_text("admin", lang)}
    selected_section = st.segmented_control(
        "IndicNotice", sections,
        format_func=lambda key: f'{nav_labels[key]} ({unread_count})' if key == "notifications" and unread_count else nav_labels[key],
        key="library_page", label_visibility="collapsed", selection_mode="single")
    section = selected_section or st.session_state.get("library_page") or "read"
    if section != "read":
        notice_library = NoticeLibrary(auth_store)
        render_notice_page(st, section, notice_library, auth_store, account, saved_profile, lang)
        return
    st.header(tr("welcome", lang) if st.session_state.get("demo_result") is None else tr("upload_another", lang))
    st.write(tr("intro", lang))
    uploaded = st.file_uploader(tr("upload", lang), type=["pdf"], key=f'notice-upload-{st.session_state.get("upload_epoch", 0)}')
    digest = sha256(uploaded.getvalue()).hexdigest() if uploaded else None
    if st.session_state.get("upload_digest") and st.session_state["upload_digest"] != digest:
        clear_notice(st.session_state)
    analyze = st.button(tr("analyze", lang), type="primary", disabled=uploaded is None)
    if st.button(tr("clear", lang)):
        clear_notice(st.session_state)
        st.session_state["upload_epoch"] = st.session_state.get("upload_epoch", 0) + 1
        st.rerun()
    if analyze and uploaded:
        try:
            with st.spinner(tr("working", lang)):
                session_analysis(st.session_state, uploaded.getvalue(), uploaded.name)
        except Exception:
            LOG.exception("Upload analysis failed")
            st.error(tr("error", lang))
    result = st.session_state.get("demo_result")
    if result is None:
        return
    status = "review_partial" if result.analysis.warnings else "reviewed"
    if result.mode == ADVANCED_MODE and not any(
        decision.promoted and decision.origin.value == "contextual"
        for decision in result.hybrid_diagnostics.decisions
    ):
        status = "review_no_additions"
    st.info(tr(status if result.mode == ADVANCED_MODE else "verify_source", lang))
    st.caption(tr("partial", lang))
    pages = ("overview", "dates", "fees", "documents", "rules", "check", "ask", "sources")
    selected_page = st.segmented_control(
        tr("notice_sections", lang), pages,
        default=st.session_state.get("notice_detail_selected", "overview"),
        format_func=lambda key: tr(key, lang), key="notice-detail-page",
        label_visibility="collapsed", selection_mode="single")
    if selected_page is not None:
        st.session_state["notice_detail_selected"] = selected_page
    page = selected_page or st.session_state.get("notice_detail_selected", "overview")
    render(st, result, page, lang, saved_profile=saved_profile, account_id=account["account_id"])
