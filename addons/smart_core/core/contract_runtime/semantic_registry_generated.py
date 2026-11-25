# -*- coding: utf-8 -*-
"""GENERATED CONTRACT-RUNTIME CARRIER - do not edit by hand.

Semantic declaration authority: contracts/registry/semantic.yaml
Regenerate with:

    python3 scripts/contract/generate_semantic_registry.py

Drift between this carrier and the declaration is a lint failure
(``make verify.semantic.registry.lint``).
"""

from __future__ import annotations

GENERATED_FROM = ('contracts/registry/semantic.yaml')
REGISTRY_DOCUMENT_VERSION = 3
DERIVATION_DEFAULT = 'readable_value'

# Ordered: the first rule whose conditions all hold decides.  Derived from the
# declaration above; there is no second mapping in the assembler.
DERIVATION_RULES = (
    {"semantic": 'reference', "field_types": ('many2one_reference', 'reference',), "reason": 'reference 值是 (model, id) 对，客户端解析后展示只读文本；声明类型优先于任何 widget 拼写。'},
    {"semantic": 'money', "field_types": ('monetary',)},
    {"semantic": 'money', "widgets": ('monetary',)},
    {"semantic": 'percentage', "widgets": ('percentage', 'percentpie',)},
    {"semantic": 'duration', "widgets": ('float_time',)},
    {"semantic": 'status', "widgets": ('statusbar', 'badge',)},
    {"semantic": 'choice', "widgets": ('account_type_selection',), "reason": 'account_type_selection 只表达选择项，由平台远程选择组件承接，不执行 Odoo 嵌入 widget。'},
    {"semantic": 'activity_collection', "widgets": ('list_activity',), "reason": 'list_activity 表达活动集合，由平台活动集合语义组件承接，不执行 Odoo 嵌入 widget。'},
    {"semantic": 'boolean', "field_types": ('boolean',)},
    {"semantic": 'readable_value', "widgets": ('account-tax-totals-field', 'payment', 'statinfo',), "reason": '会计只读摘要/统计载体（tax_totals、支付挂件、statinfo）是可读展示，不是可编辑的二进制或数字控件。'},
    {"semantic": 'relation', "field_types": ('many2one',)},
    {"semantic": 'relation', "widget_suffix": 'many2one'},
    {"semantic": 'relation_collection', "field_types": ('many2many',), "widgets_exclude": ('many2many_tags',)},
    {"semantic": 'detail_collection', "field_types": ('one2many',)},
    {"semantic": 'relation', "widgets": ('relation',), "reason": '残余 relation 控件等价于关系语义；many2many/one2many 已由更早的字段类型规则接管。'},
    {"semantic": 'text', "widgets": ('input',)},
    {"semantic": 'binary', "widgets": ('binary',)},
    {"semantic": 'binary', "widgets": ('upload',), "reason": 'upload 是 binary 字段的上传控件，与 binary 同一渲染族；声明类型优先于控件拼写。'},
    {"semantic": 'long_text', "widgets": ('textarea',)},
    {"semantic": 'number', "widgets": ('number',)},
    {"semantic": 'choice', "widgets": ('select',)},
    {"semantic": 'choice', "widgets": ('radio',), "reason": 'radio 是 selection 的单选呈现，与 select 同义。'},
    {"semantic": 'boolean', "widgets": ('checkbox',)},
    {"semantic": 'date', "widgets": ('date',)},
    {"semantic": 'datetime', "widgets": ('datetime',)},
    {"semantic": 'detail_table', "widgets": ('table',)},
    {"semantic": 'detail_table', "widgets": ('gantt',), "reason": 'gantt 是集合的时间轴呈现，暂由通用集合渲染器接管；没有独立甘特组件。'},
    {"semantic": 'hierarchical_collection', "widgets": ('tree',)},
    {"semantic": 'tag_collection', "widgets": ('many2many_tags',)},
    {"semantic": 'action', "widgets": ('button',)},
    {"semantic": 'readable_value', "widgets": ('display',)},
)

# Client-independent field semantics and applicability.
FIELD_SEMANTICS = {
    'action': {'category': 'behavioral', 'appliesTo': 'field', 'fieldTypes': ('action',)},
    'activity_collection': {'category': 'collection', 'appliesTo': 'field', 'fieldTypes': ('one2many',)},
    'binary': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('binary',)},
    'boolean': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('boolean',)},
    'challenge_status': {'category': 'auth', 'appliesTo': 'field', 'fieldTypes': ('char', 'selection', 'text')},
    'choice': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('selection',)},
    'credential_entry': {'category': 'auth', 'appliesTo': 'field', 'fieldTypes': ('char',)},
    'date': {'category': 'temporal', 'appliesTo': 'field', 'fieldTypes': ('date',)},
    'datetime': {'category': 'temporal', 'appliesTo': 'field', 'fieldTypes': ('datetime',)},
    'detail_collection': {'category': 'collection', 'appliesTo': 'field', 'fieldTypes': ('one2many',)},
    'detail_table': {'category': 'collection', 'appliesTo': 'field', 'fieldTypes': ('one2many', 'many2many')},
    'duration': {'category': 'temporal', 'appliesTo': 'field', 'fieldTypes': ('float', 'integer')},
    'hierarchical_collection': {'category': 'collection', 'appliesTo': 'field', 'fieldTypes': ('one2many', 'many2many')},
    'long_text': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('text', 'html')},
    'money': {'category': 'business', 'appliesTo': 'field', 'fieldTypes': ('monetary', 'float')},
    'number': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('integer', 'float', 'monetary')},
    'one_time_secret': {'category': 'auth', 'appliesTo': 'field', 'fieldTypes': ('char', 'text')},
    'payment_settlement_detail_collection': {'category': 'industry', 'appliesTo': 'field', 'fieldTypes': ('one2many',)},
    'percentage': {'category': 'business', 'appliesTo': 'field', 'fieldTypes': ('float', 'integer')},
    'readable_value': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('*',)},
    'reference': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('many2one_reference', 'reference')},
    'relation': {'category': 'relation', 'appliesTo': 'field', 'fieldTypes': ('many2one',)},
    'relation_collection': {'category': 'relation', 'appliesTo': 'field', 'fieldTypes': ('many2many',)},
    'secret_confirmation': {'category': 'auth', 'appliesTo': 'field', 'fieldTypes': ('char',)},
    'status': {'category': 'business', 'appliesTo': 'field', 'fieldTypes': ('selection', 'char')},
    'support_action': {'category': 'auth', 'appliesTo': 'field', 'fieldTypes': ('action',)},
    'tag_collection': {'category': 'relation', 'appliesTo': 'field', 'fieldTypes': ('many2many',)},
    'text': {'category': 'basic', 'appliesTo': 'field', 'fieldTypes': ('char',)},
    'unsupported_native_widget': {'category': 'behavioral', 'appliesTo': 'field', 'fieldTypes': ('*',)},
}

NODE_SEMANTICS = {
    'action_list': {'category': 'behavioral'},
    'display_ribbon': {'category': 'behavioral'},
    'feedback_message': {'category': 'behavioral'},
    'insight_summary': {'category': 'industry'},
    'navigation_anchor': {'category': 'behavioral'},
    'unsupported_native_node': {'category': 'behavioral'},
}

# explicit native View Widget token -> declared support status.
NATIVE_WIDGET_STATUS = {
    'account-tax-totals-field': {'status': 'ready', 'reasonCode': ''},
    'account_type_selection': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_PLATFORM_COMPONENT_SUBSTITUTION'},
    'analytic_distribution': {'status': 'ready', 'reasonCode': ''},
    'badge': {'status': 'ready', 'reasonCode': ''},
    'binary': {'status': 'ready', 'reasonCode': ''},
    'boolean': {'status': 'ready', 'reasonCode': ''},
    'boolean_favorite': {'status': 'ready', 'reasonCode': ''},
    'boolean_toggle': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'button': {'status': 'ready', 'reasonCode': ''},
    'checkbox': {'status': 'ready', 'reasonCode': ''},
    'date': {'status': 'ready', 'reasonCode': ''},
    'daterange': {'status': 'ready', 'reasonCode': ''},
    'datetime': {'status': 'ready', 'reasonCode': ''},
    'display': {'status': 'ready', 'reasonCode': ''},
    'domain': {'status': 'unsupported', 'reasonCode': 'NATIVE_WIDGET_DOMAIN_EDITOR_UNSUPPORTED'},
    'email': {'status': 'ready', 'reasonCode': ''},
    'field_partner_autocomplete': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'float_time': {'status': 'ready', 'reasonCode': ''},
    'gantt': {'status': 'ready', 'reasonCode': ''},
    'handle': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'html': {'status': 'ready', 'reasonCode': ''},
    'image': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'input': {'status': 'ready', 'reasonCode': ''},
    'json': {'status': 'ready', 'reasonCode': ''},
    'list_activity': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_PLATFORM_COMPONENT_SUBSTITUTION'},
    'many2many': {'status': 'ready', 'reasonCode': ''},
    'many2many_binary': {'status': 'ready', 'reasonCode': ''},
    'many2many_tags': {'status': 'ready', 'reasonCode': ''},
    'many2one': {'status': 'ready', 'reasonCode': ''},
    'many2one_avatar_user': {'status': 'ready', 'reasonCode': ''},
    'monetary': {'status': 'ready', 'reasonCode': ''},
    'number': {'status': 'ready', 'reasonCode': ''},
    'one2many': {'status': 'ready', 'reasonCode': ''},
    'one2many_list': {'status': 'ready', 'reasonCode': ''},
    'payment': {'status': 'ready', 'reasonCode': ''},
    'percentage': {'status': 'ready', 'reasonCode': ''},
    'percentpie': {'status': 'ready', 'reasonCode': ''},
    'phone': {'status': 'ready', 'reasonCode': ''},
    'radio': {'status': 'ready', 'reasonCode': ''},
    'relation': {'status': 'ready', 'reasonCode': ''},
    'res_partner_many2one': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'select': {'status': 'ready', 'reasonCode': ''},
    'selection': {'status': 'ready', 'reasonCode': ''},
    'statinfo': {'status': 'ready', 'reasonCode': ''},
    'statusbar': {'status': 'ready', 'reasonCode': ''},
    'table': {'status': 'ready', 'reasonCode': ''},
    'text': {'status': 'ready', 'reasonCode': ''},
    'textarea': {'status': 'ready', 'reasonCode': ''},
    'tier_validation': {'status': 'unsupported', 'reasonCode': 'NATIVE_WIDGET_QWEB_RENDERER_UNSUPPORTED'},
    'tree': {'status': 'ready', 'reasonCode': ''},
    'upload': {'status': 'ready', 'reasonCode': ''},
    'url': {'status': 'ready', 'reasonCode': ''},
}

# Embedded Form <widget name="..."/> nodes -> semantic and payload protocol.
NATIVE_VIEW_WIDGET_SEMANTICS = {
    'sc_insight_banner': {'semantic': 'insight_summary', 'status': 'ready', 'reasonCode': '', 'payloadRequired': True, 'payloadSchema': 'insight_summary.v1'},
    'sc_next_actions': {'semantic': 'action_list', 'status': 'ready', 'reasonCode': '', 'payloadRequired': True, 'payloadSchema': 'action_list.v1'},
    'sc_stage_requirements': {'semantic': 'action_list', 'status': 'ready', 'reasonCode': '', 'payloadRequired': True, 'payloadSchema': 'action_list.v1'},
    'web_ribbon': {'semantic': 'display_ribbon', 'status': 'ready', 'reasonCode': '', 'payloadRequired': False, 'payloadSchema': ''},
}
NATIVE_VIEW_WIDGET_DEFAULT = {
    'semantic': 'unsupported_native_node',
    'status': 'unsupported',
    'reasonCode': 'NATIVE_VIEW_WIDGET_UNSUPPORTED',
}

SEMANTIC_SPEC_VERSION = 3
