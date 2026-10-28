"""Read-only project stage requirements. No wizard or business writes."""
from odoo.exceptions import AccessError
from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_construction_core.handlers.project_context_resolver import ProjectContextResolverMixin
from odoo.addons.smart_construction_core.services.project_stage_requirements_read import project_stage_requirements_payload


class ProjectStageRequirementsReadHandler(ProjectContextResolverMixin, BaseIntentHandler):
    INTENT_TYPE = 'project.stage.requirements.read'
    DESCRIPTION = '只读查看当前项目阶段要求'
    VERSION = '1.0.0'
    MACHINE_ACCESS = 'read'
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ['base.group_user']
    PROJECT_ID_PARAM_RECORD_ID = False
    PROJECT_ID_PROJECT_CONTEXT = False
    PROJECT_ID_CTX_RECORD_ID = False
    PROJECT_ID_INCLUDE_HANDLER_PAYLOAD = False

    def handle(self, payload=None, ctx=None):
        params = payload or self.params or {}
        if isinstance(params.get('params'), dict):
            params = params['params']
        if type(params.get('project_id')) is not int or params['project_id'] <= 0:
            raise AccessError('当前账号无法读取此项目的阶段要求')
        resolution = self._resolve_project_scope(params, self.context or {})
        if not resolution.available:
            raise AccessError('当前账号无法读取此项目的阶段要求')
        return {'ok': True, 'data': project_stage_requirements_payload(resolution.project)}
