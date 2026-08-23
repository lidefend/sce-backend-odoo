# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json, hashlib, logging

_logger = logging.getLogger(__name__)

class AppActionConfig(models.Model):
    _name = 'app.action.config'
    _description = 'Application Action Configuration'
    _rec_name = 'label'
    _order = 'model'
    SOURCE_KIND = "odoo_native_bound_action_projection"
    SOURCE_AUTHORITIES = ("ir.actions.act_window", "ir.actions.server", "ir.actions.act_url")

    # ========= 基础信息（按模型聚合一份）=========
    name = fields.Char('Action Name', required=True)      # 记录名（例如 action_<model>）
    label = fields.Char('Label', required=True)           # 显示（例如 'Actions for sale.order'）
    model = fields.Char('Model', required=True, index=True)  # 关联模型（被聚合的“当前模型”）

    # 主类型字段保留，但真正的动作清单放到 actions_def
    action_type = fields.Selection([
        ('object', 'Object Method'),  # 调用服务器方法（按钮）
        ('action', 'Window Action'),  # 跳转到窗口（act_window）
        ('stat',   'Stat Button'),    # 统计按钮（视图上的 oe_stat_button）
        ('smart',  'Smart Button'),   # 智能按钮（同上/或移动端区域）
        ('url',    'External URL')    # 外部链接
    ], string='Action Type', default='action')

    # ========= 版本/缓存 =========
    version = fields.Integer('Version', default=1)
    config_hash = fields.Char('Config Hash', readonly=True, index=True)
    last_generated = fields.Datetime('Last Generated', readonly=True)

    # ========= 权限与扩展 =========
    groups_id = fields.Many2many('res.groups', string='Access Groups')  # 该聚合记录本身的可见组，通常不启用
    meta_info = fields.Json('Meta Info')   # 预留
    is_active = fields.Boolean('Active', default=True)

    # ========= 标准化动作清单（契约直用）=========
    actions_def = fields.Json('Actions Definition', help="""
    标准动作契约（列表）：
    [
      {
        "key": "open_sale_order",
        "label": "销售订单",
        "kind": "open",                     # open|object|server|url|report
        "model": "sale.order",              # 当前模型
        "target_model": "sale.order",       # 目标模型（open 时）
        "level": "toolbar",                 # toolbar|header|row|smart
        "selection": "none",                # none|single|multi
        "groups": [1,3],
        "groups_xmlids": ["base.group_user"],
        "visible": {"domain": [], "states": []},  # 可见性提示（前端可选用）
        "intent": "open",                   # open|execute|url
        "params": {"refresh": "list"},      # 附加参数（刷新策略/二次确认/对话框尺寸等）
        "payload": {
          "action_id": 123, "xml_id": "sale.action_orders",
          "view_mode": "tree,form", "view_id": 456,
          "context_raw": "{'search_default_my':1}", "domain_raw": "[]"
        }
      },
      ...
    ]
    """)

    _sql_constraints = [
        ('uniq_model', 'unique(model)', '每个模型仅允许一条动作聚合配置（model 唯一）。'),
    ]

    @api.model
    def _source_contract(self, model_name):
        return {
            "kind": self.SOURCE_KIND,
            "authorities": list(self.SOURCE_AUTHORITIES),
            "model": str(model_name or ""),
            "projection_only": True,
            "rebuildable": True,
            "no_business_fact_authority": True,
        }

    # ================== 生成（聚合 Odoo 各类动作） ==================

    @api.model
    def _generate_from_ir_actions(self, model_name):
        """
        为“某个模型”聚合标准化动作清单，并持久化（不变更不涨版）。
        只投影 Odoo 明确绑定到模型的上下文动作。

        表单/列表视图中的 ``<button>`` 由 ``app.view.config`` 对当前
        用户的有效视图做唯一解析。本投影不得再扫描原始
        ``ir.ui.view.arch_db``，否则会越过 action/view/inheritance/group 作用域。
        """
        try:
            if model_name not in self.env:
                raise ValueError(_("模型不存在：%s") % model_name)

            # 1) 只扫描显式 binding 来源（sudo 仅读定义，运行时再与用户 ACL 求交）
            actions = []
            actions += self._scan_window_actions(model_name)
            actions += self._scan_server_actions(model_name)
            actions += self._scan_url_actions(model_name)

            # 2) 去重与稳定排序（按 key 去重；排序保证哈希稳定）
            uniq = {}
            for a in actions:
                uniq[a['key']] = a
            actions_def = sorted(uniq.values(), key=lambda x: (x.get('level') or '', x.get('label') or '', x.get('key') or ''))

            # 3) 计算哈希（仅依赖 actions_def）
            payload = json.dumps(actions_def, sort_keys=True, ensure_ascii=False, default=str)
            new_hash = hashlib.md5(payload.encode('utf-8')).hexdigest()

            # 4) 写库（不变更不涨版）
            cfg = self.sudo().search([('model', '=', model_name)], limit=1)
            vals = {
                "name": f"action_{model_name}",
                "label": f"Actions for {model_name}",
                "model": model_name,
                "actions_def": actions_def,
                "meta_info": {"source": self._source_contract(model_name)},
                "config_hash": new_hash,
                "last_generated": fields.Datetime.now(),
            }
            if self.env.context.get('contract_projection_readonly'):
                vals["version"] = cfg.version if cfg else 0
                vals["meta_info"] = {
                    "source": self._source_contract(model_name),
                    "transient": True,
                    "runtime_readonly": True,
                }
                return self.new(vals)
            if cfg:
                if cfg.config_hash != new_hash:
                    vals["version"] = cfg.version + 1
                    cfg.write(vals)
                    _logger.info("Action config updated for %s → version %s", model_name, cfg.version)
                else:
                    _logger.info("Action config for %s unchanged, keep version %s", model_name, cfg.version)
            else:
                vals["version"] = 1
                cfg = self.sudo().create(vals)
                _logger.info("Action config created for %s → version 1", model_name)

            return cfg

        except Exception as e:
            _logger.exception("Failed to generate action config for %s", model_name)
            raise

    # ================== 各来源扫描（内部） ==================

    def _native_bound_action_scope(self, binding_view_types):
        """Project Odoo contextual actions without inventing create authority.

        A binding is a contextual action on an existing record or selection.
        Odoo's ``binding_view_types`` identifies form/list surfaces, but never
        authorizes execution against an unsaved form.  Mixed bindings retain
        both declared surfaces instead of taking the former list-only branch.
        """
        raw = str(binding_view_types or "").strip().lower()
        tokens = [token.strip() for token in raw.replace("tree", "list").split(",") if token.strip()]
        token_set = set(tokens) or {"list", "form"}
        profiles = []
        if "form" in token_set:
            profiles.extend(["edit", "readonly"])
        if "list" in token_set:
            profiles.extend(["readonly", "list"])
        return {
            "selection": "multi" if "list" in token_set else "none",
            "visible_profiles": list(dict.fromkeys(profiles)),
        }

    def _native_server_action_scope(self, binding_view_types):
        return self._native_bound_action_scope(binding_view_types)

    def _scan_window_actions(self, model_name):
        """扫描显式绑定模型的 ir.actions.act_window。"""
        res = []
        Act = self.env['ir.actions.act_window'].sudo()
        if 'binding_model_id' not in Act._fields:
            return res
        acts = Act.search([('binding_model_id.model', '=', model_name)])
        for a in acts:
            key = a.xml_id or f"aw_{a.id}"
            scope = self._native_bound_action_scope(getattr(a, 'binding_view_types', None))
            entry = {
                "key": key,
                "label": a.name or key,
                "kind": "open",
                "model": model_name,
                "target_model": a.res_model,
                "level": "toolbar",          # 缺省放工具栏；具体布局交给 view.config
                "selection": scope["selection"],
                "visible_profiles": scope["visible_profiles"],
                "groups": [g.id for g in getattr(a, 'groups_id', self.env['res.groups'])],
                "groups_xmlids": self._groups_xmlids(getattr(a, 'groups_id', self.env['res.groups'])),
                "visible": {"domain": [], "states": []},
                "intent": "open",
                "params": {"target": getattr(a, 'target', 'current')},
                "payload": {
                    "action_id": a.id,
                    "xml_id": a.xml_id or None,
                    "view_mode": a.view_mode or 'tree,form',
                    "view_id": a.view_id.id if a.view_id else None,
                    "context_raw": a.context or None,
                    "domain_raw": getattr(a, 'domain', None),
                    "help": a.help or None,
                }
            }
            res.append(entry)
        return res

    def _scan_server_actions(self, model_name):
        """扫描 ir.actions.server（服务端动作），统一为 kind='server'"""
        res = []
        Srv = self.env['ir.actions.server'].sudo()
        # Only actions explicitly bound to the model belong to its contextual
        # toolbar.  ``model_id`` also identifies cron/internal execution
        # actions, which must not become user-visible multi-record actions.
        srvs = Srv.search([('binding_model_id.model', '=', model_name)])
        for s in srvs:
            key = s.xml_id or f"srv_{s.id}"
            label = s.name or key
            scope = self._native_bound_action_scope(getattr(s, 'binding_view_types', None))
            entry = {
                "key": key,
                "label": label,
                "kind": "server",
                "model": model_name,
                "target_model": model_name,
                "level": "toolbar",
                "selection": scope["selection"],
                "visible_profiles": scope["visible_profiles"],
                "groups": [g.id for g in s.groups_id],
                "groups_xmlids": self._groups_xmlids(s.groups_id),
                "visible": {"domain": [], "states": []},
                "intent": "execute",
                "params": {"server_state": s.state},  # code/obj_create/obj_write/multi等
                "payload": {
                    "server_action_id": s.id,
                    "xml_id": s.xml_id or None
                }
            }
            res.append(entry)
        return res

    def _scan_url_actions(self, model_name):
        """扫描 ir.actions.act_url（若版本支持绑定模型），统一为 kind='url'"""
        res = []
        if not self._model_exists('ir.actions.act_url'):
            return res
        Url = self.env['ir.actions.act_url'].sudo()
        try:
            urls = Url.search([('binding_model_id.model', '=', model_name)])
        except Exception:
            # 某些版本没有 binding_model_id，跳过
            urls = Url.browse([])
        for u in urls:
            key = u.xml_id or f"url_{u.id}"
            scope = self._native_bound_action_scope(getattr(u, 'binding_view_types', None))
            entry = {
                "key": key,
                "label": u.name or key,
                "kind": "url",
                "model": model_name,
                "target_model": None,
                "level": "toolbar",
                "selection": scope["selection"],
                "visible_profiles": scope["visible_profiles"],
                "groups": [], "groups_xmlids": [],
                "visible": {"domain": [], "states": []},
                "intent": "url",
                "params": {"target": getattr(u, 'target', 'new')},
                "payload": {
                    "url": u.url,
                    "action_id": u.id,
                    "xml_id": u.xml_id or None
                }
            }
            res.append(entry)
        return res

    # ================== 标准化输出 ==================

    def get_action_contract(self, filter_runtime=True, check_model_acl=False):
        """
        返回标准化动作契约列表。
        - filter_runtime=True：按当前用户组过滤不可见动作（groups 有交集或为空 → 可见）
        - check_model_acl=True：对 object/open 等再做一次 read/write ACL 粗校（可选，成本略高）
        """
        self.ensure_one()
        actions = list(self.actions_def or [])
        if not filter_runtime and not check_model_acl:
            return actions

        user_groups = set(self.env.user.groups_id.ids)

        def allowed_by_groups(a):
            ag = set(a.get('groups') or [])
            return (not ag) or bool(ag & user_groups)

        def allowed_by_acl(a):
            if not check_model_acl:
                return True
            kind = a.get('kind')
            mdl = a.get('model')
            if not mdl or mdl not in self.env:
                return True
            try:
                if kind in ('open', 'url', 'server'):
                    # 读权限足够
                    return bool(self.env[mdl].check_access_rights('read', raise_exception=False))
                if kind == 'object':
                    # 执行模型方法，多数情况下需要 write；这里取 write 作粗校
                    return bool(self.env[mdl].check_access_rights('write', raise_exception=False))
            except Exception:
                return False
            return True

        filtered = []
        for a in actions:
            group_allowed = allowed_by_groups(a)
            acl_allowed = allowed_by_acl(a)
            if not (group_allowed and acl_allowed):
                continue
            row = dict(a)
            row.update({
                "allowed": True,
                "enabled": True,
                "disabled": False,
                "authorization_allowed": True,
                "entitlement_evaluated": True,
                "reason_code": "OK",
                "source_authority": self._source_contract(self.model),
            })
            filtered.append(row)
        return filtered

    # ================== 工具方法 ==================

    def _groups_xmlids(self, groups):
        """把 groups 记录集转 xmlids 列表"""
        try:
            mapping = groups.get_external_id() or {}
        except Exception:
            try:
                mapping = groups.get_xml_id() or {}
            except Exception:
                mapping = {}
        return sorted({str(value) for value in mapping.values() if value})

    def _model_exists(self, name):
        try:
            self.env[name]
            return True
        except Exception:
            return False
