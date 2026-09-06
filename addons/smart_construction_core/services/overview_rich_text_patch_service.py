# -*- coding: utf-8 -*-
"""项目概况受限富文本 patch service（G7.4，ADR-006 决策 1/2/4/5）。

纯函数层：canonical restricted_html 子集白名单、nh3 sanitize-on-save、
内容摘要（expected 基线 / 审计均用摘要不落全文）、长度上限、flag 解析。
不依赖 ORM，桩加载可直接单测。

安全口径：
- 白名单 = ADR-006 决策 1 的 canonical 子集（段落/标题/列表/粗斜体/
  链接/受控表格），默认 nh3 白名单（~75 标签）过宽，必须显式收紧；
- a[href] url_schemes 仅 http/https/mailto（javascript:/data: 剥除）；
- 附件边界：不引入 img/audio/video/iframe/source 标签——正文只承载
  文本结构与链接，受控附件引用属后续切片（决策 5）；
- nh3 不可用时抛 RuntimeError（handler 层结构化降级 CAPABILITY_DISABLED，
  fail-closed——绝不落库未经净化的内容）。
"""
from __future__ import annotations

import hashlib

EVENT_CODE = "PROJECT_OVERVIEW_RICH_TEXT_PATCH"
EDITABLE_FIELD = "overview_html"
FLAG_KEY = "sc.rich_text_editor.enabled"
PATCH_SCHEMA = "project.overview.rich_text.patch/v1"
# ADR-006 决策 4：max_length 由契约下发，默认 20000（对原始输入生效）
MAX_LENGTH = 20000

# canonical restricted_html 子集（ADR-006 决策 1）
CANONICAL_TAGS = frozenset(
    {
        "p", "h1", "h2", "h3",
        "ul", "ol", "li",
        "strong", "em", "b", "i",
        "table", "thead", "tbody", "tr", "td", "th",
        "a", "br",
    }
)
CANONICAL_ATTRIBUTES = {
    "a": frozenset({"href", "title"}),
    "td": frozenset({"colspan", "rowspan"}),
    "th": frozenset({"colspan", "rowspan"}),
}
URL_SCHEMES = frozenset({"http", "https", "mailto"})
LINK_REL = "noopener noreferrer"


def sanitize_overview_html(raw):
    """sanitize-on-save（ADR-006 决策 2）：nh3 白名单净化一次入库。

    读取路径直渲染不在读取路径反复净化；nh3 缺失抛 RuntimeError
    （fail-closed，调用方结构化降级）。
    """
    try:
        import nh3  # noqa: PLC0415（延迟导入：缺依赖时不炸 handler 注册链）
    except ImportError as exc:
        raise RuntimeError("nh3 unavailable (requirements-odoo.txt): %s" % exc)
    text = "" if raw is None else str(raw)
    return nh3.clean(
        text,
        tags=set(CANONICAL_TAGS),
        attributes={key: set(value) for key, value in CANONICAL_ATTRIBUTES.items()},
        url_schemes=set(URL_SCHEMES),
        link_rel=LINK_REL,
    )


def overview_digest(content):
    """内容摘要（sha256 hex 前 16 位）：基线比对与审计载荷共用，不落全文。"""
    text = "" if content is None else str(content)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def baseline_matches(expected_digest, stored_content):
    """expected 基线比对：客户端摘要 vs 服务端当前内容摘要（严格小写 hex）。"""
    if not isinstance(expected_digest, str):
        return False
    expected = expected_digest.strip().lower()
    if not expected:
        return False
    return expected == overview_digest(stored_content)


def content_over_limit(content):
    """原始输入长度上限（决策 4）：净化前判定，超限即拒（fail fast）。"""
    text = "" if content is None else str(content)
    return len(text) > MAX_LENGTH


def flag_enabled(raw):
    """kill switch 解析：仅认显式真值（与 G7.1 fail-closed 同口径）。"""
    return isinstance(raw, str) and raw.strip().lower() in ("1", "true", "yes", "on")


def build_audit_payload(
    *,
    project_id,
    digest_before,
    digest_after,
    length_before,
    length_after,
    content_modified,
    idempotency_key,
    idempotency_fingerprint,
    trace_id,
    duration_ms,
    result,
):
    """审计载荷：摘要 + 长度（不落正文全文，避免审计链膨胀）。"""
    return {
        "project_id": int(project_id or 0),
        "field": EDITABLE_FIELD,
        "digest_before": digest_before,
        "digest_after": digest_after,
        "length_before": int(length_before or 0),
        "length_after": int(length_after or 0),
        "content_modified": bool(content_modified),
        "idempotency_key": idempotency_key,
        "idempotency_fingerprint": idempotency_fingerprint,
        "trace_id": trace_id,
        "duration_ms": int(duration_ms or 0),
        "result": result or {},
    }
