# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class CompanyScopeState(str, Enum):
    NOT_PROVIDED = "NOT_PROVIDED"
    VALID_ALLOWED_COMPANY = "VALID_ALLOWED_COMPANY"
    INVALID_OR_UNAUTHORIZED = "INVALID_OR_UNAUTHORIZED"


COMPANY_SCOPE_NOT_PROVIDED = object()


@dataclass(frozen=True)
class CompanyScopeSelection:
    state: CompanyScopeState
    company_id: int = 0


class ProjectScopeUnavailable(Exception):
    """Raised when a caller-scoped project cannot be resolved."""

    code = "PROJECT_NOT_FOUND_OR_FORBIDDEN"


@dataclass(frozen=True)
class ProjectResolution:
    """Caller-scoped project resolution result.

    ``env`` and each available ``project`` retain the authenticated caller
    identity and a server-derived company context.  An unavailable result uses
    ``project=None`` so denial handling remains a pure-Python state and cannot
    perform post-error model access.  Public diagnostics deliberately exclude
    record identifiers, candidate counts, model names, and exception details.
    """

    env: Any
    project: Any
    available: bool
    code: str
    diagnostics: Dict[str, Any]


class ProjectAuthorizationService:
    """Resolve projects without trusting request-controlled security context."""

    PUBLIC_UNAVAILABLE_CODE = "PROJECT_NOT_FOUND_OR_FORBIDDEN"

    def __init__(self, env):
        self.env = env

    @staticmethod
    def _coerce_positive_id(raw_value):
        try:
            value = int(raw_value or 0)
        except (TypeError, ValueError):
            return 0
        return value if value > 0 else 0

    @staticmethod
    def _parse_company_scope(raw_value):
        """Keep omitted, valid, and invalid company selectors distinct.

        ``None`` is the one explicit value treated as equivalent to omission.
        Empty strings, booleans, floats, containers, zero, and negative values
        are explicit invalid selectors and must fail closed.
        """

        if raw_value is COMPANY_SCOPE_NOT_PROVIDED or raw_value is None:
            return CompanyScopeSelection(CompanyScopeState.NOT_PROVIDED)
        if isinstance(raw_value, bool):
            return CompanyScopeSelection(CompanyScopeState.INVALID_OR_UNAUTHORIZED)
        if isinstance(raw_value, int):
            if raw_value > 0:
                return CompanyScopeSelection(
                    CompanyScopeState.VALID_ALLOWED_COMPANY,
                    int(raw_value),
                )
            return CompanyScopeSelection(CompanyScopeState.INVALID_OR_UNAUTHORIZED)
        if isinstance(raw_value, str):
            if not raw_value or raw_value != raw_value.strip() or not raw_value.isdecimal():
                return CompanyScopeSelection(CompanyScopeState.INVALID_OR_UNAUTHORIZED)
            company_id = int(raw_value)
            if company_id > 0:
                return CompanyScopeSelection(
                    CompanyScopeState.VALID_ALLOWED_COMPANY,
                    company_id,
                )
        return CompanyScopeSelection(CompanyScopeState.INVALID_OR_UNAUTHORIZED)

    def _server_company_scope(self, selected_company_id=COMPANY_SCOPE_NOT_PROVIDED):
        """Return a caller env whose company scope comes only from res.users."""

        user = self.env.user
        allowed_company_ids = tuple(sorted(set(int(item) for item in user.company_ids.ids)))
        selection = self._parse_company_scope(selected_company_id)

        current_company_id = int(user.company_id.id or 0)
        if selection.state == CompanyScopeState.INVALID_OR_UNAUTHORIZED:
            return self.env(context={"allowed_company_ids": [], "active_test": True}), False
        if selection.state == CompanyScopeState.VALID_ALLOWED_COMPANY:
            if selection.company_id not in allowed_company_ids:
                return self.env(context={"allowed_company_ids": [], "active_test": True}), False
            scoped_company_ids = [selection.company_id]
        elif current_company_id in allowed_company_ids:
            scoped_company_ids = [current_company_id] + [
                company_id
                for company_id in allowed_company_ids
                if company_id != current_company_id
            ]
        elif allowed_company_ids:
            scoped_company_ids = list(allowed_company_ids)
        else:
            return self.env(context={"allowed_company_ids": [], "active_test": True}), False

        # A positional context replaces, instead of merges with, request
        # context.  This prevents request-supplied allowed_company_ids,
        # company_id, domain, sudo, or identity hints from entering ORM scope.
        safe_context = {
            "allowed_company_ids": scoped_company_ids,
            "active_test": True,
        }
        if user.lang:
            safe_context["lang"] = str(user.lang)
        if user.tz:
            safe_context["tz"] = str(user.tz)
        return self.env(context=safe_context), True

    @staticmethod
    def _diagnostics(path, available):
        return {
            "status": "available" if available else "unavailable",
            "resolution_path": str(path or "unavailable"),
        }

    def _unavailable(self, scoped_env=None, path="unavailable"):
        env = scoped_env or self.env
        return ProjectResolution(
            env=env,
            project=None,
            available=False,
            code=self.PUBLIC_UNAVAILABLE_CODE,
            diagnostics=self._diagnostics(path, False),
        )

    def resolve(self, project_id=0, company_id=COMPANY_SCOPE_NOT_PROVIDED):
        """Resolve an explicit or default project under caller record rules."""

        # A sudo/superuser environment is not an authenticated restricted
        # caller scope and must not be accepted by this boundary.
        if bool(getattr(self.env, "su", False)):
            return self._unavailable(path="caller_scope_unavailable")

        scoped_env, company_scope_available = self._server_company_scope(company_id)
        if not company_scope_available:
            return self._unavailable(scoped_env, "company_scope_unavailable")

        try:
            Project = scoped_env["project.project"]
        except Exception:
            return self._unavailable(scoped_env, "project_scope_unavailable")

        requested_id = self._coerce_positive_id(project_id)
        company_domain = [
            (
                "company_id",
                "in",
                list(scoped_env.context.get("allowed_company_ids") or []),
            )
        ]
        try:
            if requested_id:
                project = Project.search(
                    company_domain + [("id", "=", requested_id)],
                    limit=1,
                )
                path = "explicit_project"
            else:
                project = Project.search(
                    company_domain,
                    order="write_date desc,id desc",
                    limit=1,
                )
                path = "default_visible_project"
        except Exception:
            return self._unavailable(scoped_env, "project_scope_unavailable")

        if not project:
            # Explicit missing and explicit unauthorized IDs intentionally use
            # the same public state to avoid an ID-enumeration oracle.
            return self._unavailable(scoped_env, "project_unavailable")

        return ProjectResolution(
            env=scoped_env,
            project=project,
            available=True,
            code="",
            diagnostics=self._diagnostics(path, True),
        )

    def require(self, project_id=0, company_id=COMPANY_SCOPE_NOT_PROVIDED):
        resolution = self.resolve(project_id=project_id, company_id=company_id)
        if not resolution.available:
            raise ProjectScopeUnavailable(self.PUBLIC_UNAVAILABLE_CODE)
        return resolution


class CallerScopedProjectServiceMixin:
    """Make an industry read service consume the canonical project boundary.

    Scene services must not grow their own project membership, ownership, or
    fallback semantics.  They either consume a resolution already validated by
    the handler or resolve through :class:`ProjectAuthorizationService` using
    the authenticated caller environment.
    """

    def _initialize_project_authorization(self, env):
        self._authorized_resolution = None
        self._project_authorization_service = ProjectAuthorizationService(env)

    def _bind_caller_env(self, env):
        """Rebind downstream readers to the resolver's sanitized caller env."""

        self.env = env

    def bind_authorized_resolution(self, resolution):
        if not isinstance(resolution, ProjectResolution) or not resolution.available:
            raise ProjectScopeUnavailable(ProjectAuthorizationService.PUBLIC_UNAVAILABLE_CODE)
        if bool(getattr(resolution.env, "su", False)):
            raise ProjectScopeUnavailable(ProjectAuthorizationService.PUBLIC_UNAVAILABLE_CODE)
        if int(resolution.env.user.id) != int(self.env.user.id):
            raise ProjectScopeUnavailable(ProjectAuthorizationService.PUBLIC_UNAVAILABLE_CODE)
        self._authorized_resolution = resolution
        self._project_authorization_service = ProjectAuthorizationService(resolution.env)
        self._bind_caller_env(resolution.env)
        return self

    def resolve_project_with_diagnostics(self, project_id):
        resolution = self._authorized_resolution
        if resolution is None:
            resolution = self._project_authorization_service.resolve(project_id=project_id)
            if resolution.available:
                self.bind_authorized_resolution(resolution)

        try:
            requested_id = int(project_id or 0)
        except (TypeError, ValueError):
            requested_id = 0
        if (
            not resolution.available
            or requested_id <= 0
            or requested_id != int(resolution.project.id)
        ):
            return None, {
                "status": "unavailable",
                "resolution_path": "project_unavailable",
            }
        return resolution.project, dict(resolution.diagnostics)
