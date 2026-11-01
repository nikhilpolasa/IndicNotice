"""Same-origin authentication gateway and protected Streamlit reverse proxy."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from hashlib import sha256
from html import escape
import logging
import os
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urlencode

import httpx
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from starlette.background import BackgroundTask
from starlette.middleware.trustedhost import TrustedHostMiddleware
from websockets.asyncio.client import connect as websocket_connect
from websockets.exceptions import ConnectionClosed

from services.auth.copy import PROFILE_FIELDS, tr
from services.auth.store import AuthStore, DuplicateAccount, InvalidCredentials, PasswordPolicyError, SESSION_TTL_SECONDS, normalize_email

LOG = logging.getLogger(__name__)
SESSION_COOKIE = "indicnotice_session"
CSRF_COOKIE = "indicnotice_csrf"
MAX_LOGIN_FAILURES, LOGIN_WINDOW_SECONDS = 5, 900
MAX_REGISTER_ATTEMPTS, REGISTER_WINDOW_SECONDS = 10, 3600
CUSTOM_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
PROFILE_VALIDATORS = {"current_class": (0, 30), "previous_class": (0, 30), "marks_percentage": (0, 100), "age": (0, 125), "annual_family_income_inr": (0, 1_000_000_000), "attempt_count": (0, 100)}


@dataclass(frozen=True)
class GatewaySettings:
    public_origin: str = "http://127.0.0.1:8501"
    streamlit_port: int = 8502
    secure_cookie: bool = False
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost")


def load_settings() -> GatewaySettings:
    return GatewaySettings(
        public_origin=os.environ.get("INDICNOTICE_AUTH_ORIGIN", "http://127.0.0.1:8501").rstrip("/"),
        streamlit_port=int(os.environ.get("INDICNOTICE_STREAMLIT_PORT", "8502")),
        secure_cookie=os.environ.get("INDICNOTICE_AUTH_COOKIE_SECURE", "").casefold() in {"1", "true", "yes"},
        allowed_hosts=tuple(v.strip() for v in os.environ.get("INDICNOTICE_AUTH_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if v.strip()),
    )


def _lang(request: Request, account: dict | None = None) -> str:
    value = request.query_params.get("lang")
    return value if value in {"en", "te", "hi"} else (account or {}).get("preferred_language", "en")


def _safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value and "\r" not in value and "\n" not in value:
        return value
    return "/"


def _form(body: bytes) -> dict[str, str]:
    items = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True, max_num_fields=120)
    return {key: values[-1] for key, values in items.items() if values}


def _bucket(purpose: str, identity: str, remote: str) -> str:
    return sha256(f"{purpose}\0{identity}\0{remote}".encode()).hexdigest()


def _html(title: str, content: str, lang: str, *, csrf: str = "", account: dict | None = None,
          message: str | None = None, success: bool = False) -> HTMLResponse:
    csrf_input = f'<input type="hidden" name="csrf" value="{escape(csrf, quote=True)}">' if csrf else ""
    nav = ""
    if account:
        nav = (f'<a href="/account/profile">{escape(tr("my_profile", lang))}</a> '
               f'<a href="/account/settings">{escape(tr("account_settings", lang))}</a> '
               f'<form method="post" action="/auth/logout" style="display:inline">{csrf_input}<button class="link" type="submit">{escape(tr("logout", lang))}</button></form>')
    language_links = ' · '.join(f'<a href="?lang={code}" lang="{code}">{label}</a>' for code, label in (("en", "English"), ("te", "తెలుగు"), ("hi", "हिन्दी")))
    alert = f'<p role="alert" class="alert {"success" if success else "error"}">{escape(message)}</p>' if message else ""
    page = f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · IndicNotice</title>
<style>
:root{{color-scheme:light;--ink:#17324a;--muted:#526777;--line:#d6e0e6;--brand:#126b65;--surface:#fff;--canvas:#f4f8fa}}*{{box-sizing:border-box}}body{{margin:0;background:var(--canvas);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}header{{padding:18px max(24px,calc((100vw - 1120px)/2));background:#eaf1f4;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:20px;align-items:center}}.brand{{font-size:1.25rem;font-weight:700;text-decoration:none;color:var(--ink)}}nav{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}nav form{{margin:0}}a{{color:#125b65}}button{{font:inherit;background:var(--brand);color:#fff;border:0;border-radius:9px;padding:10px 17px;cursor:pointer}}button.link{{background:transparent;color:var(--brand);padding:4px}}main{{max-width:960px;margin:44px auto;padding:0 20px}}.card{{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:clamp(22px,4vw,40px);box-shadow:0 8px 32px #17324a0b}}h1{{font-size:clamp(1.7rem,4vw,2.2rem);line-height:1.2;margin:0 0 10px}}h2{{font-size:1.2rem;margin:28px 0 12px}}p{{color:var(--muted)}}.narrow{{max-width:520px;margin:auto}}label{{display:block;font-weight:600;margin:14px 0 5px}}input,select{{width:100%;min-height:44px;padding:9px 11px;border:1px solid #aebdc6;border-radius:8px;background:#fff;color:var(--ink);font:inherit}}input:focus,select:focus,button:focus-visible,a:focus-visible{{outline:3px solid #50a9a1;outline-offset:2px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 20px}}.help{{font-size:.9rem;color:var(--muted)}}.alert{{padding:11px 14px;border-radius:8px;background:#fce9e7;color:#84221a}}.alert.success{{background:#e6f5ed;color:#145a37}}.actions{{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}}.danger{{color:#84221a}}.lang{{color:var(--muted);font-size:.92rem;white-space:nowrap}}@media(max-width:640px){{header{{align-items:flex-start;flex-direction:column}}main{{margin:20px auto}}.grid{{grid-template-columns:1fr}}}}
</style></head><body><header><a class="brand" href="/">IndicNotice</a><nav>{nav}</nav><div class="lang" aria-label="Language">{language_links}</div></header><main><section class="card">{alert}{content}</section></main></body></html>'''
    response = HTMLResponse(page)
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin", "Permissions-Policy": "camera=(), microphone=(), geolocation=()", "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"})
    return response


def _csrf(request: Request, response: HTMLResponse, settings: GatewaySettings) -> str:
    token = request.cookies.get(CSRF_COOKIE)
    if not token or len(token) < 32:
        import secrets
        token = secrets.token_urlsafe(32)
    response.set_cookie(CSRF_COOKIE, token, path="/", max_age=SESSION_TTL_SECONDS,
                        secure=settings.secure_cookie, httponly=False, samesite="strict")
    return token


def _valid_csrf(request: Request, form: dict[str, str], settings: GatewaySettings) -> bool:
    import hmac
    token = request.cookies.get(CSRF_COOKIE, "")
    return bool(request.headers.get("origin", "").rstrip("/") == settings.public_origin
                and token and hmac.compare_digest(token, form.get("csrf", "")))


def _set_session(response: Response, token: str, expires: int, settings: GatewaySettings) -> None:
    response.set_cookie(SESSION_COOKIE, token, path="/", max_age=max(0, expires - int(time.time())),
                        secure=settings.secure_cookie, httponly=True, samesite="strict")


def _clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")


def _account(request: Request) -> dict | None:
    store: AuthStore | None = request.app.state.auth_store
    return store.account_for_session(request.cookies.get(SESSION_COOKIE)) if store else None


def _login_redirect(next_path: str = "/") -> RedirectResponse:
    return RedirectResponse("/auth/login?" + urlencode({"next": _safe_next(next_path)}), status_code=303)


def _login_content(lang: str, csrf: str, next_path: str, *, message: str | None = None, success: bool = False) -> str:
    return f'''<div class="narrow"><h1>{escape(tr("signin", lang))}</h1><p>{escape(tr("privacy", lang))}</p>
<form method="post" action="/auth/login"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><input type="hidden" name="next" value="{escape(next_path, quote=True)}">
<label for="email">{escape(tr("email", lang))}</label><input id="email" name="email" type="email" autocomplete="username" maxlength="254" required>
<label for="password">{escape(tr("password", lang))}</label><input id="password" name="password" type="password" autocomplete="current-password" maxlength="1024" required><div class="actions"><button>{escape(tr("signin", lang))}</button></div></form>
<p>{escape(tr("new_here", lang))} <a href="/auth/register?lang={lang}">{escape(tr("register", lang))}</a></p></div>'''


def _login_page(lang: str, csrf: str, next_path: str, settings: GatewaySettings,
                *, message: str | None = None, success: bool = False) -> HTMLResponse:
    body = _login_content(lang, csrf, next_path)
    response = _html(tr("signin", lang), body, lang, message=message, success=success)
    response.set_cookie(CSRF_COOKIE, csrf, path="/", max_age=SESSION_TTL_SECONDS,
                        secure=settings.secure_cookie, httponly=False, samesite="strict")
    return response


def _register_content(lang: str, csrf: str, *, error: str | None = None) -> str:
    return f'''<div class="narrow"><h1>{escape(tr("register_title", lang))}</h1><p>{escape(tr("password_help", lang))}</p>
<form method="post" action="/auth/register"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><input type="hidden" name="lang" value="{lang}">
<label for="email">{escape(tr("email", lang))}</label><input id="email" name="email" type="email" autocomplete="email" maxlength="254" required>
<label for="password">{escape(tr("password", lang))}</label><input id="password" name="password" type="password" autocomplete="new-password" minlength="12" maxlength="1024" required>
<label for="confirm">{escape(tr("confirm_password", lang))}</label><input id="confirm" name="confirm_password" type="password" autocomplete="new-password" minlength="12" maxlength="1024" required>
<div class="actions"><button>{escape(tr("register", lang))}</button></div></form><p>{escape(tr("have_account", lang))} <a href="/auth/login?lang={lang}">{escape(tr("signin", lang))}</a></p></div>'''


def _register_page(lang: str, csrf: str, settings: GatewaySettings, *, error: str | None = None) -> HTMLResponse:
    response = _html(tr("register", lang), _register_content(lang, csrf), lang, message=error)
    response.set_cookie(CSRF_COOKIE, csrf, path="/", max_age=SESSION_TTL_SECONDS,
                        secure=settings.secure_cookie, httponly=False, samesite="strict")
    return response


def _profile_form_data(form: dict[str, str], prior: dict[str, object], lang: str) -> dict[str, object]:
    values: dict[str, object] = {}
    known = {key for key, _ in PROFILE_FIELDS}
    for key, kind in PROFILE_FIELDS:
        raw = form.get(f"profile_{key}", "").strip()
        if kind == "income" and form.get("include_income") != "1":
            continue
        if not raw:
            continue
        if kind in {"number", "income"}:
            try:
                value = float(raw) if key == "marks_percentage" else int(raw)
            except ValueError as exc:
                raise ValueError(tr("invalid_profile_value", lang)) from exc
            low, high = PROFILE_VALIDATORS.get(key, (0, 1_000_000_000))
            if not low <= value <= high:
                raise ValueError(tr("invalid_profile_value", lang))
            values[key] = value
        elif kind == "date":
            from datetime import date
            try:
                values[key] = date.fromisoformat(raw).isoformat()
            except ValueError as exc:
                raise ValueError(tr("invalid_profile_value", lang)) from exc
        else:
            if len(raw) > 120 or any(ord(char) < 32 for char in raw):
                raise ValueError(tr("invalid_profile_value", lang))
            values[key] = raw
    for key in prior:
        if key not in known:
            raw = form.get(f"existing_value_{key}", "").strip()
            if raw:
                values[key] = _typed_custom_value(raw, form.get(f"existing_type_{key}", "text"), lang)
    custom_key, custom_value = form.get("custom_key", "").strip(), form.get("custom_value", "").strip()
    if custom_key or custom_value:
        if not CUSTOM_KEY_RE.fullmatch(custom_key) or custom_key in known:
            raise ValueError(tr("bad_custom_key", lang))
        if custom_value:
            values[custom_key] = _typed_custom_value(custom_value, form.get("custom_value_type", "text"), lang)
    return values


def _typed_custom_value(raw: str, kind: str, lang: str) -> object:
    if len(raw) > 120 or any(ord(char) < 32 for char in raw):
        raise ValueError(tr("invalid_profile_value", lang))
    if kind == "text":
        return raw
    if kind == "number":
        try:
            value = float(raw) if "." in raw else int(raw)
        except ValueError as exc:
            raise ValueError(tr("invalid_profile_value", lang)) from exc
        import math
        if not math.isfinite(value) or abs(value) > 1_000_000_000:
            raise ValueError(tr("invalid_profile_value", lang))
        return value
    if kind == "date":
        from datetime import date
        try:
            return date.fromisoformat(raw).isoformat()
        except ValueError as exc:
            raise ValueError(tr("invalid_profile_value", lang)) from exc
    if kind == "boolean" and raw.casefold() in {"true", "false"}:
        return raw.casefold() == "true"
    raise ValueError(tr("invalid_profile_value", lang))


def _profile_content(account: dict, attributes: dict[str, object], lang: str, csrf: str) -> str:
    known = {key for key, _ in PROFILE_FIELDS}
    inputs = []
    for key, kind in PROFILE_FIELDS:
        label = escape(tr(key, lang))
        value = escape("" if attributes.get(key) is None else str(attributes[key]), quote=True)
        input_type = {"date": "date", "number": "number", "income": "number"}.get(kind, "text")
        bounds = ' min="0" max="100" step="0.01"' if key == "marks_percentage" else ' min="0" max="1000000000" step="1"' if kind == "income" else ' min="0" max="125" step="1"' if key == "age" else ' min="0" max="30" step="1"' if key in {"current_class", "previous_class"} else ' min="0" max="100" step="1"' if key == "attempt_count" else ""
        if kind == "income":
            inputs.append(f'<div><label><input style="width:auto;min-height:auto" type="checkbox" name="include_income" value="1"{" checked" if value else ""}> {escape(tr("include_income", lang))}</label><p class="help">{label}. {escape(tr("income_storage_help", lang))}</p><input aria-label="{label}" name="profile_{key}" type="number" value="{value}"{bounds}></div>')
        else:
            inputs.append(f'<div><label for="profile_{key}">{label}</label><input id="profile_{key}" name="profile_{key}" type="{input_type}" value="{value}" maxlength="120"{bounds}></div>')
    extras = "".join(_custom_attribute_row(key, value, lang) for key, value in sorted(attributes.items()) if key not in known)
    empty_state = f'<p class="alert">{escape(tr("profile_empty", lang))}</p>' if not attributes else ""
    return f'''<h1>{escape(tr("profile_title", lang))}</h1><p>{escape(tr("authenticated_notice", lang))}: <strong>{escape(account["email"])}</strong></p><p>{escape(tr("profile_intro", lang))}</p>{empty_state}
<form method="post" action="/account/profile"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><div class="grid">{''.join(inputs)}</div>
<h2>{escape(tr("custom_section", lang))}</h2><p class="help">{escape(tr("add_attribute_help", lang))}</p>{extras}<div class="grid"><div><label for="custom_key">{escape(tr("custom_attribute", lang))}</label><input id="custom_key" name="custom_key" pattern="[a-z][a-z0-9_]{{1,63}}" maxlength="64"></div><div><label for="custom_value">{escape(tr("custom_value", lang))}</label><input id="custom_value" name="custom_value" maxlength="120"></div><div><label for="custom_type">{escape(tr("custom_value_type", lang))}</label><select id="custom_type" name="custom_value_type">{_custom_type_options(None, lang)}</select></div></div>
<div class="actions"><button>{escape(tr("save_profile", lang))}</button></div></form><form method="post" action="/account/profile/delete"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><div class="actions"><button class="link" type="submit">{escape(tr("delete_profile", lang))}</button></div></form>'''


def _custom_value_kind(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        from datetime import date
        try:
            date.fromisoformat(value)
            return "date"
        except ValueError:
            return "text"
    return "text"


def _custom_type_options(value: object, lang: str) -> str:
    selected = _custom_value_kind(value)
    return "".join(f'<option value="{kind}"{" selected" if selected == kind else ""}>{escape(tr(f"type_{kind}", lang))}</option>'
                   for kind in ("text", "number", "date", "boolean"))


def _custom_attribute_row(key: str, value: object, lang: str) -> str:
    kind = _custom_value_kind(value)
    input_type = "number" if kind == "number" else "date" if kind == "date" else "text"
    shown = "true" if value is True else "false" if value is False else str(value)
    safe_key = escape(key, quote=True)
    return (f'<div class="grid"><div><label>{escape(tr("custom_attribute", lang))}</label><input value="{safe_key}" readonly></div>'
            f'<div><label>{escape(tr("custom_value", lang))}</label><input name="existing_value_{safe_key}" type="{input_type}" value="{escape(shown, quote=True)}" maxlength="120"></div>'
            f'<div><label>{escape(tr("custom_value_type", lang))}</label><select name="existing_type_{safe_key}">{_custom_type_options(value, lang)}</select></div></div>')


def _profile_page(account: dict, attributes: dict[str, object], lang: str, csrf: str,
                  settings: GatewaySettings, *, message: str | None = None, success: bool = False) -> HTMLResponse:
    response = _html(tr("my_profile", lang), _profile_content(account, attributes, lang, csrf), lang,
                     csrf=csrf, account=account, message=message, success=success)
    response.set_cookie(CSRF_COOKIE, csrf, path="/", max_age=SESSION_TTL_SECONDS,
                        secure=settings.secure_cookie, httponly=False, samesite="strict")
    return response


def _settings_content(account: dict, lang: str, csrf: str) -> str:
    options = "".join(f'<option value="{code}"{" selected" if account["preferred_language"] == code else ""}>{name}</option>' for code, name in (("en", "English"), ("te", "తెలుగు"), ("hi", "हिन्दी")))
    return f'''<h1>{escape(tr("account_settings", lang))}</h1><p>{escape(tr("authenticated_notice", lang))}: <strong>{escape(account["email"])}</strong></p>
<form method="post" action="/account/settings"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><label for="language">{escape(tr("preferred_language", lang))}</label><select id="language" name="preferred_language">{options}</select><div class="actions"><button>{escape(tr("save_profile", lang))}</button></div></form>
<h2>{escape(tr("change_password", lang))}</h2><form method="post" action="/account/password"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><label for="current_password">{escape(tr("current_password", lang))}</label><input id="current_password" name="current_password" type="password" autocomplete="current-password" required><label for="new_password">{escape(tr("new_password", lang))}</label><input id="new_password" name="new_password" type="password" minlength="12" autocomplete="new-password" required><div class="actions"><button>{escape(tr("change_password", lang))}</button></div></form>
<h2 class="danger">{escape(tr("delete_account", lang))}</h2><p class="help">{escape(tr("delete_help", lang))}</p><form method="post" action="/account/delete"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><label for="delete_word">{escape(tr("delete_confirm", lang))}</label><input id="delete_word" name="confirmation" required><label for="delete_password">{escape(tr("current_password", lang))}</label><input id="delete_password" name="password" type="password" autocomplete="current-password" required><div class="actions"><button style="background:#84221a">{escape(tr("delete_account", lang))}</button></div></form>'''


def _settings_page(account: dict, lang: str, csrf: str, settings: GatewaySettings,
                   *, message: str | None = None, success: bool = False) -> HTMLResponse:
    response = _html(tr("account_settings", lang), _settings_content(account, lang, csrf), lang,
                     csrf=csrf, account=account, message=message, success=success)
    response.set_cookie(CSRF_COOKIE, csrf, path="/", max_age=SESSION_TTL_SECONDS,
                        secure=settings.secure_cookie, httponly=False, samesite="strict")
    return response


def create_app(*, database_path: str | Path | None = None, settings: GatewaySettings | None = None) -> FastAPI:
    configuration = settings or load_settings()

    @asynccontextmanager
    async def lifespan(instance: FastAPI):
        db_path = database_path or os.environ.get("INDICNOTICE_AUTH_DB")
        if instance.state.auth_store is None:
            instance.state.auth_store = AuthStore(db_path)
        instance.state.proxy_client = httpx.AsyncClient(timeout=None, follow_redirects=False)
        yield
        await instance.state.proxy_client.aclose()

    application = FastAPI(title="IndicNotice account gateway", docs_url=None, redoc_url=None,
                          openapi_url=None, lifespan=lifespan)
    application.state.auth_store = None
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=list(configuration.allowed_hosts))

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.method == "POST" and (request.url.path.startswith("/auth/") or request.url.path.startswith("/account/")):
            content_length = request.headers.get("content-length")
            try:
                too_large = content_length is not None and int(content_length) > 64 * 1024
            except ValueError:
                too_large = True
            if too_large:
                return JSONResponse({"detail": "Form is too large."}, status_code=413,
                                    headers={"Cache-Control": "no-store"})
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if configuration.secure_cookie:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @application.get("/healthz", include_in_schema=False)
    async def health():
        return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})

    @application.get("/auth/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        account = _account(request)
        if account:
            return RedirectResponse(_safe_next(request.query_params.get("next")), status_code=303)
        lang = _lang(request)
        response = _login_page(lang, "", _safe_next(request.query_params.get("next")), configuration)
        csrf = _csrf(request, response, configuration)
        signed_out = request.query_params.get("signed_out") == "1"
        return _login_page(lang, csrf, _safe_next(request.query_params.get("next")), configuration,
                           message=tr("signed_out", lang) if signed_out else None, success=signed_out)

    @application.get("/auth/register", response_class=HTMLResponse)
    async def register_page(request: Request):
        if _account(request):
            return RedirectResponse("/account/profile", status_code=303)
        lang = _lang(request)
        response = _register_page(lang, "", configuration)
        csrf = _csrf(request, response, configuration)
        return _register_page(lang, csrf, configuration)

    @application.post("/auth/register")
    async def register(request: Request):
        form = _form(await request.body())
        lang = form.get("lang", "en") if form.get("lang") in {"en", "te", "hi"} else "en"
        token = request.cookies.get(CSRF_COOKIE, "")
        if not _valid_csrf(request, form, configuration):
            return _register_page(lang, token, configuration, error=tr("csrf_error", lang))
        remote = request.client.host if request.client else "unknown"
        store: AuthStore = request.app.state.auth_store
        bucket = _bucket("register", remote, "")
        if store.is_rate_limited(bucket, limit=MAX_REGISTER_ATTEMPTS, window_seconds=REGISTER_WINDOW_SECONDS):
            return _register_page(lang, token, configuration, error=tr("rate_limited", lang))
        store.record_attempt(bucket, window_seconds=REGISTER_WINDOW_SECONDS)
        if form.get("password") != form.get("confirm_password"):
            return _register_page(lang, token, configuration, error=tr("validation_error", lang))
        try:
            account = store.register(form.get("email", ""), form.get("password", ""))
        except DuplicateAccount:
            return _register_page(lang, token, configuration, error=tr("duplicate_account", lang))
        except PasswordPolicyError as exc:
            return _register_page(lang, token, configuration, error=str(exc))
        except ValueError:
            return _register_page(lang, token, configuration, error=tr("validation_error", lang))
        store.update_language(account["account_id"], lang)
        token, expires = store.create_session(account["account_id"])
        response = RedirectResponse("/account/profile?welcome=1", status_code=303)
        _set_session(response, token, expires, configuration)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.post("/auth/login")
    async def login(request: Request):
        form = _form(await request.body())
        token = request.cookies.get(CSRF_COOKIE, "")
        next_path = _safe_next(form.get("next"))
        if not _valid_csrf(request, form, configuration):
            return _login_page("en", token, next_path, configuration, message=tr("csrf_error"))
        raw_email = form.get("email", "")
        try:
            identity = normalize_email(raw_email)
        except ValueError:
            identity = raw_email.strip().casefold()[:254]
        remote = request.client.host if request.client else "unknown"
        bucket = _bucket("login", identity, remote)
        store: AuthStore = request.app.state.auth_store
        if store.is_rate_limited(bucket, limit=MAX_LOGIN_FAILURES, window_seconds=LOGIN_WINDOW_SECONDS):
            return _login_page("en", token, next_path, configuration, message=tr("rate_limited"))
        try:
            account = store.login(raw_email, form.get("password", ""))
        except (InvalidCredentials, ValueError):
            store.record_attempt(bucket, window_seconds=LOGIN_WINDOW_SECONDS)
            return _login_page("en", token, next_path, configuration, message=tr("invalid_login"))
        store.clear_attempts(bucket)
        token, expires = store.create_session(account["account_id"])
        response = RedirectResponse(next_path, status_code=303)
        _set_session(response, token, expires, configuration)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.post("/auth/logout")
    async def logout(request: Request):
        form = _form(await request.body())
        account = _account(request)
        lang = _lang(request, account)
        if not _valid_csrf(request, form, configuration):
            return _login_page(lang, request.cookies.get(CSRF_COOKIE, ""), "/", configuration, message=tr("csrf_error", lang))
        request.app.state.auth_store.revoke_session(request.cookies.get(SESSION_COOKIE))
        response = RedirectResponse(f"/auth/login?lang={lang}&signed_out=1", status_code=303)
        _clear_session(response)
        return response

    @application.get("/auth/logout", response_class=HTMLResponse)
    async def logout_confirmation(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect("/")
        lang = account["preferred_language"]
        csrf_response = _html("", "", lang)
        csrf = _csrf(request, csrf_response, configuration)
        body = f'<h1>{escape(tr("logout", lang))}</h1><p>{escape(tr("authenticated_notice", lang))}: <strong>{escape(account["email"])}</strong></p><form method="post" action="/auth/logout"><input type="hidden" name="csrf" value="{escape(csrf, quote=True)}"><button type="submit">{escape(tr("logout", lang))}</button></form>'
        response = _html(tr("logout", lang), body, lang, csrf=csrf, account=account)
        response.set_cookie(CSRF_COOKIE, csrf, path="/", max_age=SESSION_TTL_SECONDS,
                            secure=configuration.secure_cookie, httponly=False, samesite="strict")
        return response

    @application.get("/api/session")
    async def api_session(request: Request):
        account = _account(request)
        if not account:
            return JSONResponse({"detail": "Authentication required."}, status_code=401, headers={"Cache-Control": "no-store"})
        return JSONResponse({"email": account["email"], "preferred_language": account["preferred_language"]}, headers={"Cache-Control": "no-store"})

    @application.get("/account/profile", response_class=HTMLResponse)
    async def profile_page(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect(request.url.path)
        store: AuthStore = request.app.state.auth_store
        lang = _lang(request, account)
        csrf_response = _html("", "", lang)
        csrf = _csrf(request, csrf_response, configuration)
        message = None
        success = False
        if request.query_params.get("saved") == "1":
            message, success = tr("profile_saved", lang), True
        elif request.query_params.get("deleted") == "1":
            message, success = tr("profile_deleted", lang), True
        return _profile_page(account, store.get_profile(account["account_id"]), lang, csrf,
                             configuration, message=message, success=success)

    @application.post("/account/profile")
    async def profile_save(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect("/account/profile")
        store: AuthStore = request.app.state.auth_store
        lang = account["preferred_language"]
        form = _form(await request.body())
        prior = store.get_profile(account["account_id"])
        if not _valid_csrf(request, form, configuration):
            return _profile_page(account, prior, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("csrf_error", lang))
        try:
            values = _profile_form_data(form, prior, lang)
            store.replace_profile(account["account_id"], values)
        except ValueError as exc:
            message = str(exc) if str(exc) in {tr("invalid_profile_value", lang), tr("bad_custom_key", lang)} else tr("validation_error", lang)
            return _profile_page(account, prior, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=message)
        return RedirectResponse("/account/profile?saved=1", status_code=303)

    @application.post("/account/profile/delete")
    async def profile_delete(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect("/account/profile")
        form = _form(await request.body())
        lang = account["preferred_language"]
        if not _valid_csrf(request, form, configuration):
            return _profile_page(account, request.app.state.auth_store.get_profile(account["account_id"]), lang,
                                 request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("csrf_error", lang))
        request.app.state.auth_store.delete_profile(account["account_id"])
        return RedirectResponse("/account/profile?deleted=1", status_code=303)

    @application.get("/account/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect(request.url.path)
        lang = account["preferred_language"]
        csrf_response = _html("", "", lang)
        csrf = _csrf(request, csrf_response, configuration)
        message = tr("settings_saved", lang) if request.query_params.get("saved") == "1" else None
        return _settings_page(account, lang, csrf, configuration, message=message, success=bool(message))

    @application.post("/account/settings")
    async def settings_save(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect("/account/settings")
        form = _form(await request.body())
        lang = account["preferred_language"]
        if not _valid_csrf(request, form, configuration):
            return _settings_page(account, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("csrf_error", lang))
        try:
            request.app.state.auth_store.update_language(account["account_id"], form.get("preferred_language", ""))
        except ValueError:
            return _settings_page(account, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("validation_error", lang))
        return RedirectResponse("/account/settings?saved=1", status_code=303)

    @application.post("/account/password")
    async def password_change(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect("/account/settings")
        form = _form(await request.body())
        lang = account["preferred_language"]
        if not _valid_csrf(request, form, configuration):
            return _settings_page(account, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("csrf_error", lang))
        try:
            changed = request.app.state.auth_store.change_password(account["account_id"], form.get("current_password", ""), form.get("new_password", ""))
        except PasswordPolicyError as exc:
            return _settings_page(account, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=str(exc))
        if not changed:
            return _settings_page(account, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("invalid_login", lang))
        response = RedirectResponse("/auth/login", status_code=303)
        _clear_session(response)
        return response

    @application.post("/account/delete")
    async def account_delete(request: Request):
        account = _account(request)
        if not account:
            return _login_redirect("/account/settings")
        form = _form(await request.body())
        lang = account["preferred_language"]
        if not _valid_csrf(request, form, configuration):
            return _settings_page(account, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("csrf_error", lang))
        if form.get("confirmation") != "DELETE" or not request.app.state.auth_store.delete_account(account["account_id"], form.get("password", "")):
            return _settings_page(account, lang, request.cookies.get(CSRF_COOKIE, ""), configuration, message=tr("invalid_login", lang))
        response = RedirectResponse("/auth/login?signed_out=1", status_code=303)
        _clear_session(response)
        return response

    @application.websocket("/{path:path}")
    async def protected_websocket(websocket: WebSocket, path: str):
        token = websocket.cookies.get(SESSION_COOKIE)
        store: AuthStore = websocket.app.state.auth_store
        origin = websocket.headers.get("origin", "").rstrip("/")
        if origin != configuration.public_origin or not store.account_for_session(token):
            await websocket.close(code=4401)
            return
        upstream_url = f"ws://127.0.0.1:{configuration.streamlit_port}/{path}"
        if websocket.url.query:
            upstream_url += "?" + websocket.url.query
        headers = []
        if websocket.headers.get("cookie"):
            headers.append(("Cookie", websocket.headers["cookie"]))
        if origin:
            headers.append(("Origin", origin))
        offered_protocols = tuple(
            value.strip() for value in websocket.headers.get("sec-websocket-protocol", "").split(",")
            if value.strip() in {"streamlit", "PLACEHOLDER_AUTH_TOKEN"}
        )
        try:
            async with websocket_connect(upstream_url, additional_headers=headers, subprotocols=offered_protocols,
                                         ping_interval=20, max_size=None) as upstream:
                await websocket.accept(subprotocol=upstream.subprotocol)
                async def down():
                    while True:
                        event = await websocket.receive()
                        if event["type"] == "websocket.disconnect":
                            return
                        if event.get("text") is not None:
                            await upstream.send(event["text"])
                        elif event.get("bytes") is not None:
                            await upstream.send(event["bytes"])

                async def up():
                    async for payload in upstream:
                        await websocket.send_text(payload) if isinstance(payload, str) else await websocket.send_bytes(payload)

                async def expiry_watch():
                    while True:
                        await asyncio.sleep(20)
                        if not store.account_for_session(token):
                            await websocket.close(code=4401)
                            await upstream.close()
                            return

                tasks = [asyncio.create_task(fn()) for fn in (down, up, expiry_watch)]
                _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
        except (ConnectionClosed, OSError, asyncio.CancelledError):
            pass
        except Exception as exc:
            LOG.warning("Protected app websocket closed (%s)", type(exc).__name__)
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

    @application.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], include_in_schema=False)
    async def protected_http(request: Request, path: str):
        if not _account(request):
            if request.method in {"GET", "HEAD"}:
                return _login_redirect(request.url.path)
            return JSONResponse({"detail": "Authentication required."}, status_code=401, headers={"Cache-Control": "no-store"})
        upstream_url = f"http://127.0.0.1:{configuration.streamlit_port}/{path}"
        if request.url.query:
            upstream_url += "?" + request.url.query
        excluded = {"host", "connection", "content-length", "transfer-encoding", "upgrade", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers"}
        headers = {k: v for k, v in request.headers.items() if k.casefold() not in excluded and not k.casefold().startswith("x-forwarded-")}
        upstream_request = request.app.state.proxy_client.build_request(
            request.method, upstream_url, headers=headers, content=await request.body(),
        )
        upstream = await request.app.state.proxy_client.send(upstream_request, stream=True)
        allowed = {"content-type", "content-length", "content-encoding", "cache-control", "location", "set-cookie", "etag", "vary", "accept-ranges", "content-range"}
        response_headers = [(k, v) for k, v in upstream.headers.raw if k.decode("latin-1").casefold() in allowed]
        response = StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code,
                                     background=BackgroundTask(upstream.aclose))
        response.raw_headers.extend(response_headers)
        return response

    return application


app = create_app()
