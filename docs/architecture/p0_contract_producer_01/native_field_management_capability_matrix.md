# Native Odoo Field Management Capability Matrix

## Purpose

This matrix defines the minimum native field facts that Contract V2.7 must
consider when translating an Odoo field occurrence into a client-independent
contract. It prevents field capabilities from being discovered one page defect
at a time.

The upper-bound list is the Odoo 17 `ir.ui.view._get_view_field_attributes()`
set used by the Odoo web client:

`change_default`, `context`, `currency_field`, `definition_record`,
`definition_record_field`, `digits`, `domain`, `group_operator`, `groups`,
`help`, `name`, `readonly`, `related`, `relation`, `relation_field`,
`required`, `searchable`, `selection`, `size`, `sortable`, `store`, `string`,
`translate`, `trim`, `type`.

View XML then supplies occurrence-specific overrides and presentation facts.
ORM implementation details that do not alter a user management action remain
backend-only.

## Source Layers

| Layer | Owns | Must not own |
| --- | --- | --- |
| Odoo field definition | type, relation target, selection, required/readonly defaults, domain/context, size, search/sort, aggregation, translation, currency/digits | page ordering or Vue implementation |
| View XML occurrence | visibility, widget, label/help override, options, modifiers, domain/context override, layout position, attachment filename | model field access or persisted business values |
| Runtime projection | effective permissions, record state, dynamic modifiers, current values, defaults/onchange outcomes | a second field-definition system |
| Industry declaration | professional semantic and business constraints | duplicate Odoo field lifecycle or renderer identity |

## Odoo 17 Web Client Field Attributes

| Odoo attribute | Contract carrier | Responsibility decision |
| --- | --- | --- |
| `name` | `fieldCode` | carried |
| `string` | `label` | carried, occurrence override wins |
| `type` | `fieldType` plus `semanticType`/`widgetType` | carried; storage type, business meaning and native occurrence remain distinct |
| `help` | `help` | carried |
| `readonly` | descriptor base value plus effective `statusContract` | effective runtime state is authoritative |
| `required` | descriptor base value plus effective `statusContract` | effective runtime state is authoritative |
| `context` | `context` | carried, occurrence override wins |
| `domain` | `domain` / `domainExpression` | carried, occurrence override wins |
| `currency_field` | `currencyField` | carried; required for `money` |
| `digits` | `digits` | carried when observable |
| `selection` | `selection` | carried as ordered key/label pairs |
| `relation` | `relation` / `relationEntry` | carried |
| `relation_field` | `relationField` | carried |
| `size` | `size` | carried and consumed as input max length |
| `searchable` | `searchable` | carried; collection management capability |
| `sortable` | `sortable` | carried; collection management capability |
| `group_operator` | `groupOperator` | carried; aggregation capability |
| `change_default` | `changeDefault` | carried; user-default interaction capability |
| `definition_record` | `definitionRecord` | carried for dynamic/property field management |
| `definition_record_field` | `definitionRecordField` | carried for dynamic/property field management |
| `store` | `store` | carried as a field fact; backend remains write authority |
| `translate` | `translate` | carried; translated-management capability |
| `trim` | `trim` | carried; input normalization capability |
| `related` | `related` | carried as normalized field-path provenance |
| `groups` | effective permission result | raw group membership is backend authorization evidence and is not published |

## View Occurrence Capabilities

| View fact | Contract carrier |
| --- | --- |
| `widget` | `widgetType` plus provenance |
| `options` | `widgetOptions` |
| `domain` / `context` | descriptor override / normalized expression |
| `readonly` / `required` / `invisible` / `column_invisible` | effective `statusContract`; modifiers remain source evidence |
| `string` / `nolabel` / `col` / `colspan` | label and layout occurrence |
| `filename` | `filename` |
| `force_save` | occurrence attributes and existing write lifecycle where applicable |
| `optional` / `sum` | collection occurrence columns |
| row `decoration-*` | collection presentation contract |

## Backend-Only Exclusions

The following are not client management capabilities and must not be copied
blindly into the frontend contract: compute/inverse/search method names,
`compute_sudo`, `precompute`, database index/column/table names, prefetch
groups, ORM cache details, and raw authorization group membership.

## Completion Criteria

A native field capability is closed only when:

1. its Odoo source fact is identified in the matrix;
2. the contract carrier and ownership are explicit;
3. effective permissions are projected without leaking raw authorization data;
4. the frontend either consumes the capability or the unimplemented consumption
   is explicitly recorded as a capability gap;
5. positive and negative tests prove the projection, not only a happy-path page.
