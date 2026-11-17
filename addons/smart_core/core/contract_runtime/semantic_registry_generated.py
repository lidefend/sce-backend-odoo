# -*- coding: utf-8 -*-
"""GENERATED CONTRACT-RUNTIME CARRIER - do not edit by hand.

Declaration authority: contracts/registry/semantic.yaml -> contracts/registry/component.yaml
Regenerate with:

    python3 scripts/contract/generate_semantic_registry.py

Drift between this carrier and the declaration is a lint failure
(``make verify.semantic.registry.lint``).
"""

from __future__ import annotations

GENERATED_FROM = ('contracts/registry/semantic.yaml', 'contracts/registry/component.yaml')
REGISTRY_DOCUMENT_VERSION = 2
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

# semantic -> the component key the frontend renders.
SEMANTIC_COMPONENTS = {
    'action': 'sc.button.action',
    'binary': 'sc.input.binary',
    'boolean': 'sc.input.boolean',
    'challenge_status': 'sc.auth.challenge_status',
    'choice': 'sc.select.remote',
    'credential_entry': 'sc.auth.credential_entry',
    'date': 'sc.input.date',
    'datetime': 'sc.input.datetime',
    'detail_collection': 'sc.relation.table',
    'detail_table': 'sc.table.data',
    'duration': 'sc.value.duration',
    'hierarchical_collection': 'sc.tree.data',
    'long_text': 'sc.input.textarea',
    'money': 'sc.value.money',
    'number': 'sc.input.number',
    'one_time_secret': 'sc.auth.one_time_secret',
    'payment_settlement_detail_collection': 'sc.payment.settlement_detail_collection',
    'percentage': 'sc.value.percentage',
    'readable_value': 'sc.display.text',
    'reference': 'sc.display.text',
    'relation': 'sc.relation.many2one',
    'relation_collection': 'sc.relation.many2many',
    'secret_confirmation': 'sc.auth.secret_confirmation',
    'status': 'sc.display.status',
    'support_action': 'sc.auth.support_action',
    'tag_collection': 'sc.select.tags',
    'text': 'sc.input.text',
    'unsupported_native_widget': 'sc.unsupported.native_widget',
}

# explicit native View Widget token -> declared support status.
NATIVE_WIDGET_STATUS = {
    'account-tax-totals-field': {'status': 'ready', 'reasonCode': ''},
    'analytic_distribution': {'status': 'ready', 'reasonCode': ''},
    'badge': {'status': 'ready', 'reasonCode': ''},
    'binary': {'status': 'ready', 'reasonCode': ''},
    'boolean': {'status': 'ready', 'reasonCode': ''},
    'boolean_toggle': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'button': {'status': 'ready', 'reasonCode': ''},
    'checkbox': {'status': 'ready', 'reasonCode': ''},
    'date': {'status': 'ready', 'reasonCode': ''},
    'daterange': {'status': 'ready', 'reasonCode': ''},
    'datetime': {'status': 'ready', 'reasonCode': ''},
    'display': {'status': 'ready', 'reasonCode': ''},
    'domain': {'status': 'unsupported', 'reasonCode': 'NATIVE_WIDGET_DOMAIN_EDITOR_UNSUPPORTED'},
    'email': {'status': 'ready', 'reasonCode': ''},
    'float_time': {'status': 'ready', 'reasonCode': ''},
    'handle': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'html': {'status': 'ready', 'reasonCode': ''},
    'image': {'status': 'fallback', 'reasonCode': 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
    'input': {'status': 'ready', 'reasonCode': ''},
    'json': {'status': 'ready', 'reasonCode': ''},
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
    'textarea': {'status': 'ready', 'reasonCode': ''},
    'tier_validation': {'status': 'unsupported', 'reasonCode': 'NATIVE_WIDGET_QWEB_RENDERER_UNSUPPORTED'},
    'tree': {'status': 'ready', 'reasonCode': ''},
    'upload': {'status': 'ready', 'reasonCode': ''},
    'url': {'status': 'ready', 'reasonCode': ''},
}

# Embedded Form <widget name="..."/> nodes -> node component identity.
NATIVE_VIEW_WIDGET_COMPONENTS = {
    'sc_insight_banner': {'component': 'sc.insight.summary', 'status': 'ready', 'reasonCode': '', 'payloadRequired': True},
    'sc_next_actions': {'component': 'sc.action.list', 'status': 'ready', 'reasonCode': '', 'payloadRequired': True},
    'sc_stage_requirements': {'component': 'sc.action.list', 'status': 'ready', 'reasonCode': '', 'payloadRequired': True},
    'web_ribbon': {'component': 'sc.display.ribbon', 'status': 'ready', 'reasonCode': '', 'payloadRequired': False},
}
NATIVE_VIEW_WIDGET_DEFAULT = {
    'component': 'sc.unsupported.native_node',
    'status': 'unsupported',
    'reasonCode': 'NATIVE_VIEW_WIDGET_UNSUPPORTED',
}

# Backend registration identity only; no client support is implied.
FIELD_CONTRACT_VERSION = '1.0'
COMPONENT_REGISTRATIONS = {
    'sc.action.list': {'kind': 'node', 'version': '1.0.0'},
    'sc.auth.challenge_status': {'kind': 'field', 'version': '1.0'},
    'sc.auth.credential_entry': {'kind': 'field', 'version': '1.0'},
    'sc.auth.one_time_secret': {'kind': 'field', 'version': '1.0'},
    'sc.auth.secret_confirmation': {'kind': 'field', 'version': '1.0'},
    'sc.auth.support_action': {'kind': 'field', 'version': '1.0'},
    'sc.button.action': {'kind': 'field', 'version': '1.0'},
    'sc.display.ribbon': {'kind': 'node', 'version': '1.0.0'},
    'sc.display.status': {'kind': 'field', 'version': '1.0'},
    'sc.display.text': {'kind': 'field', 'version': '1.0'},
    'sc.feedback.message': {'kind': 'node', 'version': '1.0.0'},
    'sc.input.binary': {'kind': 'field', 'version': '1.0'},
    'sc.input.boolean': {'kind': 'field', 'version': '1.0'},
    'sc.input.date': {'kind': 'field', 'version': '1.0'},
    'sc.input.datetime': {'kind': 'field', 'version': '1.0'},
    'sc.input.number': {'kind': 'field', 'version': '1.0'},
    'sc.input.text': {'kind': 'field', 'version': '1.0'},
    'sc.input.textarea': {'kind': 'field', 'version': '1.0'},
    'sc.insight.summary': {'kind': 'node', 'version': '1.0.0'},
    'sc.navigation.anchor': {'kind': 'node', 'version': '1.0.0'},
    'sc.payment.settlement_detail_collection': {'kind': 'field', 'version': '1.0'},
    'sc.relation.many2many': {'kind': 'field', 'version': '1.0'},
    'sc.relation.many2one': {'kind': 'field', 'version': '1.0'},
    'sc.relation.table': {'kind': 'field', 'version': '1.0'},
    'sc.select.remote': {'kind': 'field', 'version': '1.0'},
    'sc.select.tags': {'kind': 'field', 'version': '1.0'},
    'sc.table.data': {'kind': 'field', 'version': '1.0'},
    'sc.tree.data': {'kind': 'field', 'version': '1.0'},
    'sc.unsupported.native_node': {'kind': 'node', 'version': '1.0.0'},
    'sc.unsupported.native_widget': {'kind': 'field', 'version': '1.0'},
    'sc.value.duration': {'kind': 'field', 'version': '1.0'},
    'sc.value.money': {'kind': 'field', 'version': '1.0'},
    'sc.value.percentage': {'kind': 'field', 'version': '1.0'},
}
