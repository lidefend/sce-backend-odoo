# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_construction_scene.services.my_work_scene_targets import (
    resolve_my_work_scene_key,
)


class WorkItemAggregateService:
    SORT_FIELDS = {"id", "title", "model", "deadline", "source", "reason_code", "section", "priority"}
    PRIORITY_LEVELS = ("high", "medium", "low")

    @classmethod
    def normalize_item(cls, row, *, section_key, section_label):
        item = dict(row or {})
        item["id"] = int(item.get("id") or 0)
        item["title"] = str(item.get("title") or "").strip()
        item["model"] = str(item.get("model") or "").strip()
        item["record_id"] = int(item.get("record_id") or 0)
        item["deadline"] = str(item.get("deadline") or "").strip()
        item["source"] = str(item.get("source") or "").strip()
        item["scene_key"] = resolve_my_work_scene_key(
            explicit_scene_key=str(item.get("scene_key") or ""),
            model_name=item["model"],
            source_key=item["source"],
            section_key=section_key,
        )
        item["action_label"] = str(item.get("action_label") or "").strip()
        item["action_key"] = str(item.get("action_key") or "").strip()
        item["reason_code"] = str(item.get("reason_code") or "").strip()
        priority = str(item.get("priority") or "").strip().lower()
        if priority not in cls.PRIORITY_LEVELS:
            priority = "medium"
        item["priority"] = priority
        item["section"] = section_key
        item["section_label"] = section_label
        return item

    @classmethod
    def append_items(cls, target, *, section_key, section_label, rows):
        for row in rows or []:
            target.append(cls.normalize_item(row, section_key=section_key, section_label=section_label))

    @classmethod
    def aggregate_items(cls, rows):
        grouped = {}
        order = []
        for index, row in enumerate(rows or []):
            item = dict(row or {})
            model_name = str(item.get("model") or "").strip()
            record_id = int(item.get("record_id") or 0)
            source = str(item.get("source") or "").strip()
            item_id = int(item.get("id") or 0)
            if model_name and record_id:
                key = "%s:%s:%s" % (item.get("section") or "", model_name, record_id)
            elif source and item_id:
                key = "%s:%s:%s" % (item.get("section") or "", source, item_id)
            else:
                key = "__item__:%s" % index
            grouped.setdefault(key, []).append(item)
            if key not in order:
                order.append(key)

        result = []
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        source_rank = {
            "tier.review": 0,
            "mail.activity": 1,
            "project.task": 2,
        }
        for key in order:
            group = grouped.get(key) or []
            if not group:
                continue
            if len(group) == 1:
                item = dict(group[0])
            else:
                item = dict(
                    sorted(
                        group,
                        key=lambda row: (
                            priority_rank.get(str(row.get("priority") or ""), 9),
                            source_rank.get(str(row.get("source") or ""), 3),
                            -int(row.get("id") or 0),
                        ),
                    )[0]
                )
            sources = sorted({
                str(row.get("source") or "").strip()
                for row in group
                if str(row.get("source") or "").strip()
            })
            item["aggregation_key"] = "" if key.startswith("__item__:") else key
            item["sources"] = sources
            item["source_count"] = len(sources)
            item["source_refs"] = [
                {
                    "id": int(row.get("id") or 0),
                    "source": str(row.get("source") or "").strip(),
                    "action_key": str(row.get("action_key") or "").strip(),
                    "action_label": str(row.get("action_label") or "").strip(),
                    "reason_code": str(row.get("reason_code") or "").strip(),
                    "deadline": str(row.get("deadline") or "").strip(),
                }
                for row in group
            ]
            result.append(item)
        return result

    @staticmethod
    def item_sources(item):
        if not isinstance(item, dict):
            return []
        sources = item.get("sources")
        if isinstance(sources, list):
            return [str(source or "").strip() for source in sources if str(source or "").strip()]
        source = str(item.get("source") or "").strip()
        return [source] if source else []

    @staticmethod
    def ranked_counts(counter_map):
        rows = [{"key": key, "count": int(value)} for key, value in (counter_map or {}).items()]
        rows.sort(key=lambda row: row["count"], reverse=True)
        return rows

    @classmethod
    def build_facets(cls, items):
        source_counts = {}
        reason_counts = {}
        section_counts = {}
        priority_counts = {}
        for item in items or []:
            reason = str(item.get("reason_code") or "").strip()
            section = str(item.get("section") or "").strip()
            priority = str(item.get("priority") or "").strip()
            for source in cls.item_sources(item):
                source_counts[source] = int(source_counts.get(source, 0)) + 1
            if reason:
                reason_counts[reason] = int(reason_counts.get(reason, 0)) + 1
            if section:
                section_counts[section] = int(section_counts.get(section, 0)) + 1
            if priority:
                priority_counts[priority] = int(priority_counts.get(priority, 0)) + 1
        return {
            "source_counts": cls.ranked_counts(source_counts),
            "reason_code_counts": cls.ranked_counts(reason_counts),
            "section_counts": cls.ranked_counts(section_counts),
            "priority_counts": cls.ranked_counts(priority_counts),
        }

    @staticmethod
    def apply_filters(items, *, section, source, reason_code, search):
        result = list(items or [])
        if section and section != "all":
            result = [item for item in result if str(item.get("section") or "") == section]
        if source and source != "all":
            result = [item for item in result if source in WorkItemAggregateService.item_sources(item)]
        if reason_code and reason_code != "all":
            result = [item for item in result if str(item.get("reason_code") or "") == reason_code]
        if search:
            result = [
                item
                for item in result
                if search in " ".join(
                    [
                        str(item.get("title") or ""),
                        str(item.get("model") or ""),
                        str(item.get("action_label") or ""),
                        str(item.get("reason_code") or ""),
                        str(item.get("priority") or ""),
                    ]
                ).lower()
            ]
        return result

    @staticmethod
    def sort_value(item, sort_by):
        if sort_by == "id":
            return int(item.get("id") or 0)
        if sort_by == "priority":
            ranking = {"high": 3, "medium": 2, "low": 1}
            return ranking.get(str(item.get("priority") or "").strip().lower(), 0)
        text = str(item.get(sort_by) or "").lower()
        if sort_by == "deadline":
            return (text == "", text)
        return text

    @classmethod
    def apply_sort(cls, items, *, sort_by, sort_dir):
        reverse = sort_dir == "desc"
        return sorted(list(items or []), key=lambda item: cls.sort_value(item, sort_by), reverse=reverse)

    @staticmethod
    def paginate(items, *, page, page_size):
        rows = list(items or [])
        total = len(rows)
        total_pages = max(1, (total + page_size - 1) // page_size)
        safe_page = min(page, total_pages)
        offset = (safe_page - 1) * page_size
        return rows[offset : offset + page_size], total_pages, safe_page
