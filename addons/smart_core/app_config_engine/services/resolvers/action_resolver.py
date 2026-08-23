# -*- coding: utf-8 -*-
# smart_core/app_config_engine/services/resolvers/action_resolver.py
# 【职责】动作解析与下钻：
#   - resolve_action：通过 xmlid/id/menu 定位动作记录（含 base->specific）
#   - drill_down_action：只接受显式 server→window 映射；client/url/report 原样返回
import logging
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first

_logger = logging.getLogger(__name__)

class ActionResolver:
    SOURCE_KIND = "odoo_action_resolution_projection"
    SOURCE_AUTHORITIES = (
        "ir.actions.actions",
        "ir.actions.act_window",
        "ir.actions.server",
        "ir.actions.client",
        "ir.actions.report",
        "ir.actions.act_url",
        "ir.ui.menu",
    )
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls):
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": True,
            "write_proxy": True,
            "no_business_fact_authority": cls.NO_BUSINESS_FACT_AUTHORITY,
            "runtime_carrier": "app_config_engine.action_resolver",
        }

    def __init__(self, env):
        self.env = env

    # ----------------- 外部调用入口 -----------------

    def resolve_action(self, action_id=None, action_xmlid=None, menu_id=None):
        """
        解析动作优先级：
        1) xmlid → 直接 ref；
        2) action_id → ir.actions.actions（base）→ specific（如 ir.actions.act_window）；
           若 base 找不到 specific，再穷举常见模型；
        3) menu_id → 从菜单取 action；
        """
        _logger.debug("RESOLVE_ACTION_ENTER action_id=%s action_xmlid=%s menu_id=%s",
                     action_id, action_xmlid, menu_id)
        # a) xmlid 优先
        if action_xmlid:
            rec = self.env.ref(str(action_xmlid), raise_if_not_found=False)
            if rec and rec.exists():
                return rec
        # b) id：先 base，再 specific，下沉到具体类型
        if action_id:
            base = self.env['ir.actions.actions'].sudo().browse(int(action_id))
            if base and base.exists():
                a_type = getattr(base, 'type', None)
                if a_type and a_type != 'ir.actions.actions':
                    try:
                        specific = self.env[a_type].sudo().browse(int(action_id))
                        if specific and specific.exists():
                            _logger.debug("DRILL_DOWN: specific %s #%s name=%s", a_type, action_id, getattr(specific,'name',None))
                            return specific
                    except Exception as e:
                        _logger.debug("DRILL_DOWN: specific fail %s #%s: %s", a_type, action_id, e)
                _logger.debug("DRILL_DOWN: fallback base actions #%s", action_id)
                return base
            # c) 直查常见模型（防越库/脏数据）
            for mdl in ('ir.actions.act_window','ir.actions.server','ir.actions.client','ir.actions.report','ir.actions.act_url'):
                try:
                    rec = self.env[mdl].sudo().browse(int(action_id))
                    if rec and rec.exists():
                        _logger.debug("DRILL_DOWN: found directly in %s #%s", mdl, action_id)
                        return rec
                except Exception:
                    pass
        # d) 从 menu_id 回退
        if menu_id:
            menu = self.env['ir.ui.menu'].sudo().browse(int(menu_id))
            return menu.action if menu and menu.exists() else None
        return None

    def resolve_action_from_menu(self, menu, safe_server_run=False):
        """
        从菜单解析动作。``safe_server_run`` 仅保留调用兼容性；契约读取
        永不执行 server action。
        """
        menu = menu.sudo()
        action = menu.action
        if not action:
            return None
        raw = self.resolve_action(action_id=action.id)
        final = self.drill_down_action(raw, safe_server_run=False)
        return final

    def as_action_info(self, act):
        """
        将 record/dict 统一转为标准 dict 结构（便于下游装配使用）
        """
        if not act:
            return {'type': None, '_name': None, 'id': None, 'xml_id': None, 'exists': False}
        # 如果是父 actions，先下钻到具体动作
        try:
            if not isinstance(act, dict) and getattr(act, '_name', '') == 'ir.actions.actions':
                act_type = (getattr(act, 'type', None) or '').strip()
                if act_type:
                    act = self.env[act_type].sudo().browse(int(getattr(act, 'id', 0)))
        except Exception:
            pass
        # dict → 归一化
        if isinstance(act, dict):
            d = dict(act)
            d.setdefault('type', d.get('type') or d.get('_name'))
            d.setdefault('_name', d.get('_name') or d.get('type'))
            d.setdefault('url', d.get('url'))
            d.setdefault('target', d.get('target'))
            d.setdefault('name', d.get('name'))
            d.setdefault('exists', True)
            return d
        # recordset → 提取关键属性/外部 xmlid
        try:
            _name = getattr(act, '_name', None)
            _type = getattr(act, 'type', None) or _name
            xmlid = None
            try:
                ext = act.get_external_id()
                if ext and act.id in ext and ext[act.id]:
                    xmlid = ext[act.id]
            except Exception:
                pass
            return {
                'type': _type, '_name': _name, 'id': getattr(act, 'id', None),
                'xml_id': xmlid, 'res_model': getattr(act, 'res_model', None),
                'view_mode': getattr(act, 'view_mode', None), 'tag': getattr(act, 'tag', None),
                'url': getattr(act, 'url', None), 'target': getattr(act, 'target', None),
                'name': getattr(act, 'name', None),
                'domain': getattr(act, 'domain', None),
                'context': getattr(act, 'context', None),
                'exists': True,
            }
        except Exception:
            return {'type': None, '_name': None, 'id': None, 'xml_id': None, 'exists': False}

    # ----------------- 下钻 / 物化 -----------------

    def drill_down_action(self, act_or_dict, safe_server_run=False):
        """
        将动作统一下钻为可渲染的标准动作 dict：
        - act_window：直接返回；
        - server：仅接受显式映射，读取契约时绝不执行代码；
        - client/url/report：原样返回交给上层。
        """
        if not act_or_dict:
            return None
        d = self.normalize_action_dict(act_or_dict)
        a_type = d.get('type')

        if a_type == 'ir.actions.act_window':
            _logger.debug("FINAL_ACTION: act_window model=%s view_mode=%s", d.get('res_model'), d.get('view_mode'))
            return d

        if a_type == 'ir.actions.server':
            # 1) 自定义映射（避免执行 server 代码）
            mapped = self.map_server_to_window(d.get('id'), d.get('xml_id'))
            if mapped:
                dd = self.normalize_action_dict(mapped)
                _logger.debug("FINAL_ACTION: server→mapped act_window model=%s", dd.get('res_model'))
                return dd
            _logger.warning("FINAL_ACTION: server not resolvable id=%s xml_id=%s", d.get('id'), d.get('xml_id'))
            return None

        # client/url/report：交由上层装配
        _logger.debug("FINAL_ACTION: non-window type=%s", a_type)
        return d

    # ----------------- 工具 -----------------

    def normalize_action_dict(self, act):
        """
        将 record 或 dict 统一转换为标准动作字典，确保存在基础键位。
        """
        if hasattr(act, '_name'):
            out = {
                "type": act.type, "id": act.id,
                "res_model": getattr(act, 'res_model', None),
                "view_mode": getattr(act, 'view_mode', None),
                "url": getattr(act, 'url', None),
                "domain": getattr(act, 'domain', None) or [],
                "context": getattr(act, 'context', None) or {},
                "target": getattr(act, 'target', None),
                "name": getattr(act, 'name', None), "xml_id": None,
            }
            try:
                xid = act.get_xml_id()
                out["xml_id"] = xid.get(act.id) if isinstance(xid, dict) else xid
            except Exception:
                pass
            return out
        out = dict(act or {})
        out.setdefault("url", out.get("url"))
        out.setdefault("domain", []); out.setdefault("context", {})
        out.setdefault("view_mode", out.get("view_mode") or "tree,form")
        return out

    def map_server_to_window(self, server_id=None, server_xmlid=None):
        """
        可选：将某些 server 动作映射为固定 act_window，避免执行代码。
        - 如无定制映射，返回 None。
        """
        mapping = call_extension_hook_first(self.env, "smart_core_server_action_window_map", self.env)
        if not isinstance(mapping, dict):
            mapping = {}
        target_xmlid = None
        if server_xmlid and server_xmlid in mapping:
            target_xmlid = mapping[server_xmlid]
        if not target_xmlid and server_id:
            try:
                rec = self.env["ir.actions.server"].sudo().browse(int(server_id))
                if rec and rec.exists():
                    xmlid = (rec.get_xml_id() or {}).get(rec.id)
                    if xmlid in mapping:
                        target_xmlid = mapping[xmlid]
            except Exception:
                target_xmlid = None
        if not target_xmlid:
            return None
        target = self.env.ref(target_xmlid, raise_if_not_found=False)
        if not target or not target.exists():
            return None
        return self.normalize_action_dict(target)
