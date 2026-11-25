"""Request-local protocol checks for declared form node semantics."""
from .form_configuration_compiler import FormConfigurationError
from .contract_runtime.semantic_registry_generated import FIELD_SEMANTICS
from .node_component_validation import validate_declared_semantics, walk

# Protocol capabilities keyed by backend node semantics. These do not select a
# frontend component and do not assert renderer implementation support.
OPTIONAL_NODE_CAPABILITIES = {
    'insight_summary': 'form.insight.summary.v1',
    'action_list': 'form.action.list.v1',
}
NODE_CAPABILITIES = {
    'feedback_message': 'form.feedback.message.v1',
    'navigation_anchor': 'form.navigation.anchor.v1',
    'display_ribbon': 'form.display.ribbon.v1',
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
            capability = OPTIONAL_NODE_CAPABILITIES.get(node.get('semanticType'))
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
    validate_declared_semantics(contract)
    layout = contract.get('layoutContract') or {}
    supplied = params.get('client_contract_capabilities')
    capabilities = set(supplied) if isinstance(supplied, list) and all(type(v) is str for v in supplied) else set()
    _project_optional_nodes(contract, capabilities)
    required = []
    for node, path in walk(layout.get('containerTree', [])):
        semantic_type = node.get('semanticType')
        if semantic_type is None:
            continue
        if type(semantic_type) is not str or not semantic_type:
            raise FormConfigurationError('NODE_SEMANTIC_MISSING', path + '.semanticType')
        if semantic_type in FIELD_SEMANTICS:
            continue
        if semantic_type == 'unsupported_native_node':
            # The unsupported node is deliberately published so the client can
            # reject it through the same contract-gap path with its own reason.
            continue
        capability = NODE_CAPABILITIES.get(semantic_type)
        if capability is None or capability not in capabilities:
            required.append(path + '.semanticType')
        evaluation = (node.get('componentConfig') or {}).get('evaluation')
        if evaluation is not None and DRAFT_FEEDBACK_CAPABILITY not in capabilities:
            required.append(path + '.componentConfig.evaluation')
    # Finish identity/version validation before rejecting missing capabilities.
    if required:
        raise FormConfigurationError('COMPONENT_CAPABILITY_REQUIRED', required[0])
