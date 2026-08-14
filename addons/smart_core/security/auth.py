# smart_core/security/auth.py
import jwt
import logging
import os
import time
import uuid
from datetime import datetime
from odoo.http import request
from odoo import http, SUPERUSER_ID, api
from odoo.exceptions import AccessDenied
from odoo.modules.registry import Registry
from odoo.tools import config

AUTH_METHOD_API_KEY = "api_key"
AUTH_METHOD_BOOTSTRAP_SECRET = "bootstrap_secret"
AUTH_METHOD_PASSWORD = "password"
PRINCIPAL_HUMAN = "human"

_logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
DEFAULT_EXP_SECONDS = 8 * 60 * 60  # 8h
MINIMUM_HMAC_SECRET_BYTES = 32

SOURCE_KIND = "jwt_auth_session_proxy"
SOURCE_AUTHORITIES = ("res.users", "ir.config_parameter", "http.authorization", "odoo.session")
NO_BUSINESS_FACT_AUTHORITY = True


def source_authority_contract() -> dict:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "rebuildable": False,
        "write_proxy": True,
        "no_business_fact_authority": NO_BUSINESS_FACT_AUTHORITY,
        "identity_surface_only": True,
    }


def _get_secret_key():
    secret = os.getenv("SC_JWT_SECRET") or os.getenv("JWT_SECRET")
    try:
        env = getattr(request, "env", None)
    except RuntimeError:
        env = None
    if not secret and env is not None:
        try:
            secret = env["ir.config_parameter"].sudo().get_param("sc.jwt.secret")
        except Exception:
            secret = None
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < MINIMUM_HMAC_SECRET_BYTES:
        _logger.error("JWT signing secret is missing or shorter than %s bytes", MINIMUM_HMAC_SECRET_BYTES)
        raise AccessDenied("JWT 签名密钥未安全配置")
    return secret


def get_token_exp_seconds():
    try:
        env = getattr(request, "env", None)
    except RuntimeError:
        env = None
    raw = os.getenv("SC_JWT_EXP_SECONDS")
    if not raw and env is not None:
        try:
            raw = env["ir.config_parameter"].sudo().get_param("sc.jwt.exp_seconds")
        except Exception:
            raw = None
    try:
        val = int(raw)
        if val > 0:
            return val
    except Exception:
        pass
    return DEFAULT_EXP_SECONDS

def generate_token(
    *,
    principal,
    expires_in: int | None = None,
):
    now = int(time.time())
    exp = now + int(expires_in or get_token_exp_seconds())
    if principal is None or not callable(getattr(principal, "claims", None)):
        raise AccessDenied("Token 必须由明确身份上下文签发")
    principal_claims = principal.claims()
    payload = {
        **principal_claims,
        "iat": now,
        "exp": exp,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)

def decode_token(token):
    try:
        return jwt.decode(
            token,
            _get_secret_key(),
            algorithms=[ALGORITHM],
            options={"require": [
                "exp", "iat", "jti", "token_version", "user_id", "db",
                "principal_type", "auth_method", "credential_id", "scope",
                "company_id", "allowed_company_ids", "role_xmlids", "credential_epoch",
            ]},
        )
    except jwt.ExpiredSignatureError:
        raise AccessDenied("Token 已过期")
    except jwt.MissingRequiredClaimError:
        raise AccessDenied("Token 缺少必要字段")
    except jwt.InvalidTokenError:
        raise AccessDenied("无效的 Token")


def _extract_bearer_token(auth_header):
    parts = str(auth_header or "").strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise AccessDenied("Authorization 头格式无效")
    return parts[1].strip()


def _request_db_name():
    httprequest = getattr(request, "httprequest", None)
    if httprequest is not None:
        try:
            header_db = httprequest.headers.get("X-Odoo-DB") or httprequest.headers.get("X-DB")
        except Exception:
            header_db = None
        if str(header_db or "").strip():
            return str(header_db).strip()
        try:
            query_db = httprequest.args.get("db")
        except Exception:
            query_db = None
        if str(query_db or "").strip():
            return str(query_db).strip()
    session_db = getattr(getattr(request, "session", None), "db", None)
    if str(session_db or "").strip():
        return str(session_db).strip()
    try:
        return str(getattr(getattr(request.env, "cr", None), "dbname", "") or "").strip()
    except Exception:
        return ""


def _ensure_token_db_matches_request(token_db):
    expected = str(token_db or "").strip()
    current = _request_db_name()
    if expected and current and expected != current:
        raise AccessDenied("Token 数据库与当前请求数据库不一致")


def _token_user_id(payload):
    try:
        user_id = int((payload or {}).get("user_id") or 0)
    except Exception:
        user_id = 0
    if user_id <= 0:
        raise AccessDenied("Token 缺少有效 user_id")
    return user_id


def _session_user_id(session_uid):
    try:
        user_id = int(session_uid or 0)
    except Exception:
        user_id = 0
    if user_id <= 0:
        raise AccessDenied("系统 Session 缺少有效 user_id")
    return user_id


def _validate_claim_list(payload, key):
    value = (payload or {}).get(key)
    if not isinstance(value, list):
        raise AccessDenied(f"Token {key} 无效")
    return value


def _validated_int_claims(payload, key):
    try:
        values = tuple(int(value) for value in _validate_claim_list(payload, key))
    except (TypeError, ValueError):
        raise AccessDenied(f"Token {key} 无效")
    if not values or any(value <= 0 for value in values) or values != tuple(sorted(set(values))):
        raise AccessDenied(f"Token {key} 无效")
    return values


def _current_role_xmlids(user):
    mapping = user.groups_id.get_external_id() or {}
    return tuple(sorted(mapping[group.id] for group in user.groups_id if mapping.get(group.id)))


def _validated_token_principal(payload, user, env):
    auth_method = str(payload.get("auth_method") or "").strip()
    principal_type = str(payload.get("principal_type") or "").strip()
    credential_id = str(payload.get("credential_id") or "").strip()
    scopes = tuple(str(value or "").strip() for value in _validate_claim_list(payload, "scope"))
    allowed_company_ids = _validated_int_claims(payload, "allowed_company_ids")
    role_xmlids = tuple(str(value or "").strip() for value in _validate_claim_list(payload, "role_xmlids"))
    company_id = int(payload.get("company_id") or 0)
    if (
        not scopes
        or not company_id
        or company_id not in allowed_company_ids
        or not role_xmlids
        or role_xmlids != tuple(sorted(set(role_xmlids)))
    ):
        raise AccessDenied("Token 身份范围无效")
    current_companies = set(user.company_ids.ids)
    if not set(allowed_company_ids).issubset(current_companies):
        raise AccessDenied("Token 公司范围已失效")
    if role_xmlids != _current_role_xmlids(user):
        raise AccessDenied("Token 角色范围已失效")
    if auth_method == AUTH_METHOD_PASSWORD:
        if principal_type != PRINCIPAL_HUMAN or credential_id or scopes != ("interactive",):
            raise AccessDenied("Token 人类会话声明无效")
    elif auth_method == AUTH_METHOD_API_KEY:
        if principal_type != "machine" or not credential_id:
            raise AccessDenied("Token 机器会话声明无效")
        policy = env["sc.auth.credential.policy"].sudo().search(
            [("credential_id", "=", credential_id), ("user_id", "=", user.id)],
            limit=1,
        )
        now = datetime.utcnow()
        if (
            not policy
            or policy.state != "active"
            or int(policy.credential_epoch or 0) != int(payload.get("credential_epoch") or 0)
            or not policy.native_key_exists()
            or (policy.expires_at and policy.expires_at <= now)
            or not set(scopes).issubset(set(policy.scope_values()))
            or not set(allowed_company_ids).issubset(set(policy.company_ids.ids))
            or company_id not in policy.company_ids.ids
        ):
            raise AccessDenied("Token 机器凭据已失效")
    elif auth_method == AUTH_METHOD_BOOTSTRAP_SECRET:
        if principal_type != "machine" or credential_id != "platform_bootstrap_secret" or scopes != ("bootstrap",):
            raise AccessDenied("Token 引导凭据声明无效")
    else:
        raise AccessDenied("Token 认证方式无效")
    return {
        "user": user,
        "payload": payload,
        "auth_method": auth_method,
        "principal_type": principal_type,
        "credential_id": credential_id,
        "scopes": scopes,
        "company_id": company_id,
        "allowed_company_ids": allowed_company_ids,
        "role_xmlids": role_xmlids,
    }


def get_principal_from_token():
    """
    从请求中提取 Token 并解析用户对象。兼容系统原生登录与自定义 Token 登录。
    """
    auth_header = request.httprequest.headers.get("Authorization")
    session = getattr(request, "session", None)
    session_uid = getattr(session, "uid", None)

    if auth_header:
        token = _extract_bearer_token(auth_header)
        payload = decode_token(token)
        user_id = _token_user_id(payload)
        token_db = str(payload.get("db") or "").strip()
        db_name = token_db or getattr(getattr(request, "session", None), "db", None) or getattr(request, "db", None)
        if not db_name:
            raise AccessDenied("Token 缺少数据库信息")
        if token_db:
            _ensure_token_db_matches_request(token_db)
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            user = env["res.users"].sudo().browse(user_id)
            if not user.exists():
                raise AccessDenied("Token 中指定的用户不存在")
            current_version = int(getattr(user, "token_version", 0) or 0)
        token_version = int(payload.get("token_version") or 0)
        if token_version != current_version:
            raise AccessDenied("Token 已撤销")
        # Return a user record bound to the current request env/cursor.
        # The `user` record above was created on a temporary cursor.
        request_user = request.env["res.users"].sudo().browse(user_id)
        if not request_user.exists():
            raise AccessDenied("Token 中指定的用户不存在")
        return _validated_token_principal(payload, request_user, request.env)

    elif session_uid:
        user = request.env["res.users"].browse(_session_user_id(session_uid))
        if not user.exists():
            raise AccessDenied("系统 Session 中的用户无效")
        return {
            "user": user,
            "payload": {},
            "auth_method": AUTH_METHOD_PASSWORD,
            "principal_type": PRINCIPAL_HUMAN,
            "credential_id": "",
            "scopes": ("interactive",),
            "company_id": int(user.company_id.id or 0),
            "allowed_company_ids": tuple(user.company_ids.ids),
            "role_xmlids": (),
        }

    else:
        raise AccessDenied("未提供 Token 或未登录 Session")


def get_user_from_token():
    """Backward-compatible user projection of the unified principal."""
    return get_principal_from_token()["user"]

def authenticate_user(login, password, db: str | None = None):
    """
    基于用户名和密码校验用户身份，并返回登录用户对象
    """
    session_db = getattr(getattr(request, "session", None), "db", None)
    query_db = None
    if getattr(request, "httprequest", None) is not None:
        try:
            query_db = request.httprequest.args.get("db")
        except Exception:
            query_db = None
    env_db = getattr(getattr(getattr(request, "env", None), "cr", None), "dbname", None)
    config_db = config.get("db_name")
    if isinstance(config_db, str) and "," in config_db:
        config_db = next((item.strip() for item in config_db.split(",") if item.strip()), None)
    elif isinstance(config_db, (list, tuple)):
        config_db = next((str(item).strip() for item in config_db if str(item).strip()), None)

    db = db or session_db or query_db or env_db or config_db
    if not db:
        raise AccessDenied("未指定数据库")
    from .credential_service import authenticate_password
    try:
        principal = authenticate_password(database=db, login=login, secret=password)
    except AccessDenied:
        raise AccessDenied("用户名或密码错误")
    return {
        "id": principal.user_id,
        "login": login,
        "db": db,
        "principal": principal,
    }
