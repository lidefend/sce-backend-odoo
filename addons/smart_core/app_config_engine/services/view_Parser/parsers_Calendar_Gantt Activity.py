# -*- coding: utf-8 -*-
"""
services/view_Parser/parsers_Calendar_Gantt Activity.py

calendar / gantt / activity / search 解析与合并
"""
from lxml import etree
import logging

_logger = logging.getLogger(__name__)


class _CalendarGanttActivitySearchParserMixin:
    SOURCE_KIND = "odoo_calendar_gantt_activity_search_view_parser_mixin"
    SOURCE_AUTHORITIES = (
        "ir.ui.view:calendar",
        "ir.ui.view:gantt",
        "ir.ui.view:activity",
        "ir.ui.view:search",
        "ir.model.fields",
    )
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": True,
            "rebuildable": True,
            "no_business_fact_authority": cls.NO_BUSINESS_FACT_AUTHORITY,
            "view_parser_mixin_only": True,
        }

    # ---------------- calendar 解析 ----------------
    def _parse_calendar_view(self, arch, root=None):
        out = {
            "date_start": "date_start",
            "date_stop": "date_end",
            "color": "user_id",
            "date_slots": {"start": "date_start", "stop": "date_end"},
            "color_slots": {"color": "user_id"},
            "event_open_popup": None,
            "default_scale": None,
            "fields": [],
            "native_attrs": {},
        }
        try:
            if root is not None or arch:
                if root is None:
                    root = etree.fromstring(arch.encode('utf-8'))
                if root.tag != 'calendar':
                    cals = root.xpath('.//calendar')
                    root = cals[0] if cals else root

                out["native_attrs"] = dict(root.attrib or {})
                for k in ('date_start', 'date_stop', 'color'):
                    if root.get(k):
                        out[k] = root.get(k)
                out["date_slots"] = {"start": out["date_start"], "stop": out["date_stop"]}
                out["color_slots"] = {"color": out["color"]}

                eop = root.get('event_open_popup')
                if isinstance(eop, str):
                    out["event_open_popup"] = eop.strip().lower() in ('1', 'true', 'yes', 'y', 'on')

                if root.get('default_scale'):
                    out["default_scale"] = root.get('default_scale')

                for extra in ('quick_add', 'mode', 'create'):
                    if root.get(extra) is not None:
                        out[extra] = root.get(extra)
                out["fields"] = self._parse_view_field_nodes(root)
        except Exception:
            _logger.exception("parse calendar view failed")
        return out

    # ---------------- gantt 解析 ----------------
    def _parse_gantt_view(self, arch, root=None):
        out = {
            "date_start": "date_start",
            "date_stop": "date_end",
            "progress": "progress",
            "date_slots": {"start": "date_start", "stop": "date_end"},
            "resource_slots": {},
            "dependency_slots": {},
            "default_scale": None,
            "event_open_popup": None,
            "decorations": [],
            "fields": [],
            "native_attrs": {},
        }
        try:
            if root is not None or arch:
                if root is None:
                    root = etree.fromstring(arch.encode('utf-8'))
                if root.tag != 'gantt':
                    g = root.xpath('.//gantt')
                    root = g[0] if g else root

                out["native_attrs"] = dict(root.attrib or {})
                for k in ('date_start', 'date_stop', 'progress'):
                    if root.get(k):
                        out[k] = root.get(k)
                out["date_slots"] = {"start": out["date_start"], "stop": out["date_stop"]}
                if root.get('default_group_by'):
                    out["resource_slots"]["group_by"] = root.get('default_group_by')
                if root.get('dependency_field'):
                    out["dependency_slots"]["dependency_field"] = root.get('dependency_field')

                if root.get('default_scale'):
                    out["default_scale"] = root.get('default_scale')

                eop = root.get('event_open_popup')
                if isinstance(eop, str):
                    out["event_open_popup"] = eop.strip().lower() in ('1', 'true', 'yes', 'y', 'on')

                for k, v in (root.attrib or {}).items():
                    if k.startswith('decoration-') and v:
                        out["decorations"].append({
                            "class": k.replace('decoration-', ''),
                            "expr_raw": v,
                            "expr": self._safe_eval_expr(v)
                        })

                if root.get('consolidate'):
                    out['consolidate'] = root.get('consolidate')
                out["fields"] = self._parse_view_field_nodes(root)
        except Exception:
            _logger.exception("parse gantt view failed")
        return out

    # ---------------- activity 解析（最小可用） ----------------
    def _parse_activity_view(self, arch, root=None):
        out = {
            "template_qweb": None,
            "activity_type_slots": {},
            "deadline_slots": {},
            "assignee_slots": {},
            "fields": [],
            "native_attrs": {},
        }
        try:
            if root is not None or arch:
                if root is None:
                    root = etree.fromstring(arch.encode('utf-8'))
                if root.tag != 'activity':
                    ac = root.xpath('.//activity')
                    root = ac[0] if ac else root
                out["native_attrs"] = dict(root.attrib or {})
                if root.get('activity_type'):
                    out["activity_type_slots"]["type"] = root.get('activity_type')
                if root.get('date_deadline'):
                    out["deadline_slots"]["deadline"] = root.get('date_deadline')
                if root.get('user_id'):
                    out["assignee_slots"]["assignee"] = root.get('user_id')
                out["fields"] = self._parse_view_field_nodes(root)
                tmpl = root.xpath('.//templates')
                out["template_qweb"] = tmpl and etree.tostring(tmpl[0], encoding='unicode') or None
        except Exception:
            _logger.exception("parse activity view failed")
        return out

    # ---------------- search 解析与合并 ----------------
    def _parse_search_from_arch(self, arch, root=None):
        out = {
            "filters": [], "group_by": [], "group_by_fields": [], "search_fields": [],
            "search_panel": {"sections": []}, "facets": {"enabled": True},
        }
        try:
            if root is None and not arch:
                return out
            if root is None:
                root = etree.fromstring(arch.encode('utf-8'))
            search_nodes = root.xpath('.//search') if root.tag != 'search' else [root]
            if not search_nodes:
                return out

            gb_set = []  # 使用列表以“遇到即记录 + 去重”的方式保持稳定顺序
            seen_gb = set()
            filters = []
            group_by_fields = []
            search_fields = []
            for s in search_nodes:
                occurrence_nodes = [node for node in s.iter() if node is not s and node.tag in ('filter', 'field')]
                source_positions = {id(node): index for index, node in enumerate(occurrence_nodes)}

                def identity(element):
                    tag = str(element.tag or '')
                    name = element.get('name')
                    duplicate_ordinal = 1
                    segments = []
                    current = element
                    while current is not None and isinstance(getattr(current, 'tag', None), str):
                        parent = current.getparent() if hasattr(current, 'getparent') else None
                        tag_ordinal = 1
                        if parent is not None:
                            siblings = [child for child in parent if getattr(child, 'tag', None) == current.tag]
                            if current in siblings:
                                tag_ordinal = siblings.index(current) + 1
                            if current is element:
                                duplicates = [
                                    child for child in parent
                                    if getattr(child, 'tag', None) == tag and child.get('name') == name
                                ]
                                if current in duplicates:
                                    duplicate_ordinal = duplicates.index(current) + 1
                        segments.append('%s[%s]' % (current.tag, tag_ordinal))
                        current = parent
                    return {
                        "native_locator": "/" + "/".join(reversed(segments)),
                        "occurrence_index": duplicate_ordinal,
                        "source_position": source_positions[id(element)],
                        "attributes": dict(element.attrib or {}),
                    }

                for field in (node for node in occurrence_nodes if node.tag == 'field'):
                    fname = (field.get('name') or '').strip()
                    if not fname:
                        continue
                    parent = field.getparent()
                    inside_search_panel = False
                    while parent is not None:
                        if getattr(parent, 'tag', None) == 'searchpanel':
                            inside_search_panel = True
                            break
                        parent = parent.getparent() if hasattr(parent, 'getparent') else None
                    if inside_search_panel:
                        out["search_panel"]["sections"].append({
                            "field": fname,
                            "name": fname,
                            "label": field.get('string') or fname,
                            "domain_raw": field.get('domain') or '',
                            "groupby": field.get('groupby') or '',
                            "hierarchize": field.get('hierarchize'),
                            "select": field.get('select'),
                            "limit": field.get('limit'),
                            **identity(field),
                        })
                        continue
                    search_fields.append({
                        "name": fname,
                        "label": field.get('string') or fname,
                        "operator": field.get('operator') or '',
                        "filter_domain_raw": field.get('filter_domain') or '',
                        "context_raw": field.get('context') or '',
                        "domain_raw": field.get('domain') or '',
                        "optional": field.get('optional'),
                        "sum": field.get('sum'),
                        **identity(field),
                    })
                for f in (node for node in occurrence_nodes if node.tag == 'filter'):
                    name = f.get('name') or ''
                    label = f.get('string') or name
                    domain_raw = f.get('domain')
                    context_raw = f.get('context')
                    domain_val = self._safe_eval_expr(domain_raw)
                    context_val = self._safe_eval_expr(context_raw)

                    occurrence = identity(f)
                    filters.append({
                        "name": name or label,
                        "label": label,
                        "domain": domain_val if isinstance(domain_val, (list, tuple)) else [],
                        "domain_raw": domain_raw,
                        "context_raw": context_raw,
                        "context": context_val if isinstance(context_val, dict) else {},
                        "help": f.get('help') or '',
                        "date": f.get('date'),
                        "type": f.get('type'),
                        **occurrence,
                    })

                    gb = None
                    if isinstance(context_val, dict):
                        gb = context_val.get('group_by')
                    if gb:
                        if isinstance(gb, str):
                            if gb not in seen_gb:
                                gb_set.append(gb); seen_gb.add(gb)
                        elif isinstance(gb, (list, tuple)):
                            for g in gb:
                                if isinstance(g, str) and g not in seen_gb:
                                    gb_set.append(g); seen_gb.add(g)
                    if gb:
                        group_by_fields.append({
                            "name": name or label,
                            "label": label,
                            "field": gb,
                            "context_raw": context_raw,
                            **occurrence,
                        })

            out["filters"] = filters
            out["group_by"] = gb_set
            out["group_by_fields"] = group_by_fields
            out["search_fields"] = search_fields
            return out
        except Exception:
            _logger.exception("parse search view failed")
            raise

    def _merge_search(self, primary, secondary):
        """
        合并两个 search 结构：
        - filters：按 (name,label,domain_raw,context_raw) 去重保序
        - group_by：遇到即并入，去重保序
        - facets.enabled：任一为 True 则 True
        """
        primary = primary or {"filters": [], "group_by": [], "facets": {"enabled": True}}
        secondary = secondary or {"filters": [], "group_by": [], "facets": {"enabled": True}}

        def _key(f):
            locator = str(f.get('native_locator') or '').strip()
            if locator:
                return ('native', locator, int(f.get('occurrence_index') or 0))
            return (
                (f.get('name') or ''),
                (f.get('label') or ''),
                (f.get('domain_raw') or ''),
                (f.get('context_raw') or ''),
            )

        seen = set()
        merged_filters = []
        for f in (primary.get('filters', []) + secondary.get('filters', [])):
            k = _key(f)
            if k in seen:
                continue
            seen.add(k)
            merged_filters.append(f)

        gb_seen = set()
        merged_gb = []
        for g in (primary.get('group_by', []) + secondary.get('group_by', [])):
            if g not in gb_seen:
                gb_seen.add(g)
                merged_gb.append(g)

        facets_enabled = bool((primary.get('facets') or {}).get('enabled') or (secondary.get('facets') or {}).get('enabled'))

        merged_search_fields = []
        sf_seen = set()
        for row in (primary.get('search_fields', []) + secondary.get('search_fields', [])):
            key = _key(row)
            if key in sf_seen:
                continue
            sf_seen.add(key)
            merged_search_fields.append(row)

        merged_group_fields = []
        gf_seen = set()
        for row in (primary.get('group_by_fields', []) + secondary.get('group_by_fields', [])):
            key = _key(row)
            if key in gf_seen:
                continue
            gf_seen.add(key)
            merged_group_fields.append(row)

        merged_panel_sections = []
        panel_seen = set()
        for source in (primary, secondary):
            panel = source.get('search_panel') if isinstance(source.get('search_panel'), dict) else {}
            for row in panel.get('sections', []) if isinstance(panel.get('sections'), list) else []:
                key = _key(row)
                if key in panel_seen:
                    continue
                panel_seen.add(key)
                merged_panel_sections.append(row)

        return {
            "filters": merged_filters,
            "group_by": merged_gb,
            "group_by_fields": merged_group_fields,
            "search_fields": merged_search_fields,
            "search_panel": {"sections": merged_panel_sections},
            "facets": {"enabled": facets_enabled},
        }

    def _parse_view_field_nodes(self, root):
        rows = []
        seen = set()
        for field in root.xpath('.//field[@name]') if root is not None else []:
            name = (field.get('name') or '').strip()
            if not name or name in seen:
                continue
            seen.add(name)
            rows.append({
                "name": name,
                "label": field.get('string') or name,
                "widget": field.get('widget') or '',
                "invisible": field.get('invisible') or '',
                "modifiers": field.get('modifiers') or '',
            })
        return rows
