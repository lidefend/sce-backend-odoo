"""Request-local delivery checks, independent of outer contract version support."""
import re

from .contract_runtime.semantic_resolver import component_registration
from .form_configuration_compiler import FormConfigurationError
from .node_component_validation import walk

# Protocol names, not a second registry/version authority.
OPTIONAL_NODE_CAPABILITIES = {
    'sc.insight.summary': 'form.insight.summary.v1',
    'sc.action.list': 'form.action.list.v1',
}
NODE_CAPABILITIES = {
    'sc.feedback.message': 'form.feedback.message.v1',
    'sc.navigation.anchor': 'form.navigation.anchor.v1',
    'sc.display.ribbon': 'form.display.ribbon.v1',
    **OPTIONAL_NODE_CAPABILITIES,
}
DRAFT_FEEDBACK_CAPABILITY = 'form.feedback.draft.v1'


def _project_optional_nodes(contract, capabilities):
    """Remove optional enhancements the current client cannot consume.

    Inherited views and runtime configuration can contribute embedded nodes
    after the formal source was reviewed. Optional business enhancements must
    not turn an otherwise usable record page into a request-wide failure.
    """
    layout = contract.get('layoutContract') or {}
    removed_ids = set()

    def collect_ids(node, target):
        if not isinstance(node, dict):
            return
        container_id = node.get('containerId')
        if isinstance(container_id, str) and container_id:
            target.add(container_id)
        for child in node.get('children') or []:
            collect_ids(child, target)

    def project(rows):
        if not isinstance(rows, list):
            return rows
        kept = []
        for node in rows:
            if not isinstance(node, dict):
                kept.append(node)
                continue
            capability = OPTIONAL_NODE_CAPABILITIES.get(node.get('componentKey'))
            if capability is not None and capability not in capabilities:
                collect_ids(node, removed_ids)
                continue
            children = node.get('children')
            if isinstance(children, list):
                node['children'] = project(children)
            kept.append(node)
        return kept

    layout['containerTree'] = project(layout.get('containerTree', []))
    if removed_ids:
        status = contract.get('statusContract') or {}
        status['containerStatus'] = [
            row for row in status.get('containerStatus', [])
            if not isinstance(row, dict) or row.get('containerId') not in removed_ids
        ]


def validate_component_capabilities(contract, params):
    layout = contract.get('layoutContract') or {}
    registry = layout.get('componentRegistry') or {}
    supplied = params.get('client_contract_capabilities')
    capabilities = set(supplied) if isinstance(supplied, list) and all(type(v) is str for v in supplied) else set()
    _project_optional_nodes(contract, capabilities)
    required = []
    for node, path in walk(layout.get('containerTree', [])):
        key = node.get('componentKey')
        if key is None:
            continue
        if type(key) is not str or not key:
            raise FormConfigurationError('COMPONENT_UNREGISTERED', path + '.componentKey')
        try:
            registration = component_registration(key)
        except ValueError as exc:
            raise FormConfigurationError('COMPONENT_UNREGISTERED', path + '.componentKey') from exc
        if registration['kind'] != 'node':
            continue  # Existing field-component contract remains unchanged.
        version = registration['version']
        delivered = registry.get(key) if isinstance(registry, dict) else None
        if (not re.fullmatch(r'1\.[0-9]+\.[0-9]+', version)
                or not isinstance(delivered, dict) or delivered.get('version') != version):
            raise FormConfigurationError('COMPONENT_VERSION_UNSUPPORTED', path + '.componentKey')
        if key == 'sc.unsupported.native_node':
            # The unsupported node is deliberately published so the client can
            # reject it through the same contract-gap path with its own reason.
            continue
        capability = NODE_CAPABILITIES.get(key)
        if capability is None or capability not in capabilities:
            required.append(path + '.componentKey')
        evaluation = (node.get('componentConfig') or {}).get('evaluation')
        if evaluation is not None and DRAFT_FEEDBACK_CAPABILITY not in capabilities:
            required.append(path + '.componentConfig.evaluation')
    # Finish identity/version validation before rejecting missing capabilities.
    if required:
        raise FormConfigurationError('COMPONENT_CAPABILITY_REQUIRED', required[0])
