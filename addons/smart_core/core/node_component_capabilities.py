"""Request-local delivery checks, independent of outer contract version support."""
import re

from .contract_runtime.semantic_resolver import component_registration
from .form_configuration_compiler import FormConfigurationError
from .node_component_validation import walk

# Protocol names, not a second registry/version authority.
NODE_CAPABILITIES = {
    'sc.feedback.message': 'form.feedback.message.v1',
    'sc.navigation.anchor': 'form.navigation.anchor.v1',
}
DRAFT_FEEDBACK_CAPABILITY = 'form.feedback.draft.v1'


def validate_component_capabilities(contract, params):
    layout = contract.get('layoutContract') or {}
    registry = layout.get('componentRegistry') or {}
    supplied = params.get('client_contract_capabilities')
    capabilities = set(supplied) if isinstance(supplied, list) and all(type(v) is str for v in supplied) else set()
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
        capability = NODE_CAPABILITIES.get(key)
        if capability is None or capability not in capabilities:
            required.append(path + '.componentKey')
        evaluation = (node.get('componentConfig') or {}).get('evaluation')
        if evaluation is not None and DRAFT_FEEDBACK_CAPABILITY not in capabilities:
            required.append(path + '.componentConfig.evaluation')
    # Finish identity/version validation before rejecting missing capabilities.
    if required:
        raise FormConfigurationError('COMPONENT_CAPABILITY_REQUIRED', required[0])
