"""Finish sample stages only after their real business facts have been created."""
from odoo.exceptions import UserError

from ..registry import SeedStep, register
from .step_20_projects_demo import STAGE_PROJECTS, _apply_lifecycle


def run(env):
    for code, _name, target, _phase in STAGE_PROJECTS:
        # Seed identity lookup only; _apply_lifecycle switches to the real actor.
        projects = env["project.project"].sudo().search([("project_code", "=", code)])
        if len(projects) != 1:
            raise UserError("Demo stage requires exactly one project: %s" % code)
        _apply_lifecycle(projects, target)


register(SeedStep(
    name="demo_80_finalize_stages",
    description="Advance prepared stage samples through native project actions.",
    run=run,
))
