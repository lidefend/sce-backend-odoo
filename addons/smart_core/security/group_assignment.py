"""Pure native-group source projection. No industry roles or inferred grants."""


class GroupAuthorityGap(ValueError):
    pass


def apply_commands(initial, commands):
    if not isinstance(commands, (list, tuple)):
        raise GroupAuthorityGap('GROUP_AUTHORITY_UNSUPPORTED_COMMAND')
    roots = None if initial is None else set(initial)
    for command in commands:
        if not isinstance(command, (tuple, list)) or not command:
            raise GroupAuthorityGap('GROUP_AUTHORITY_UNSUPPORTED_COMMAND')
        op = command[0]
        if isinstance(op, bool) or not isinstance(op, int):
            raise GroupAuthorityGap('GROUP_AUTHORITY_UNSUPPORTED_COMMAND')
        op = int(op)
        if op == 6 and len(command) == 3 and isinstance(command[2], (list, tuple)):
            if any(type(value) is not int or value <= 0 for value in command[2]):
                raise GroupAuthorityGap('GROUP_AUTHORITY_INVALID_GROUP_ID')
            roots = set(command[2])
        elif op == 5 and len(command) in (1, 3):
            roots = set()
        elif op in (3, 4) and len(command) in (2, 3) and type(command[1]) is int and command[1] > 0:
            if roots is None:
                raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
            if op == 4:
                roots.add(command[1])
            else:
                roots.discard(command[1])
        else:
            raise GroupAuthorityGap('GROUP_AUTHORITY_UNSUPPORTED_COMMAND')
    if roots is None:
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    return roots


def verified_roots(state, current, closure):
    if not isinstance(state, dict) or state.get('version') not in (1, 2) or state.get('status') != 'tracked':
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    roots = state.get('roots')
    if not isinstance(roots, list) or any(type(value) is not int or value <= 0 for value in roots):
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    if set(state.get('observed', [])) != set(current) or set(closure) != set(current):
        raise GroupAuthorityGap('GROUP_AUTHORITY_PROJECTION_DRIFT')
    if state['version'] == 2 and source_union(verified_sources(state)) != set(roots):
        raise GroupAuthorityGap('GROUP_AUTHORITY_SOURCE_DRIFT')
    return set(roots)


def verified_sources(state):
    """Read provenance only; callers must also verify the observed native closure."""
    if not isinstance(state, dict) or state.get('status') != 'tracked':
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    return recorded_sources(state)


def recorded_sources(state):
    """Read retained provenance for explicit review, without claiming projection validity."""
    if not isinstance(state, dict):
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    sources = {'native': state.get('roots')} if state.get('version') == 1 else state.get('sources')
    if state.get('version') not in (1, 2) or not isinstance(sources, dict) or 'native' not in sources:
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    for key, values in sources.items():
        if not isinstance(key, str) or not key or not isinstance(values, list) or any(type(x) is not int or x <= 0 for x in values):
            raise GroupAuthorityGap('GROUP_AUTHORITY_SOURCE_DRIFT')
    return {key: set(values) for key, values in sources.items()}


def source_union(sources):
    return set().union(*sources.values()) if sources else set()


def replace_source(sources, key, roots):
    if not isinstance(key, str) or not key or key == 'native':
        raise GroupAuthorityGap('GROUP_AUTHORITY_INVALID_SOURCE')
    if any(type(value) is not int or value <= 0 for value in roots):
        raise GroupAuthorityGap('GROUP_AUTHORITY_INVALID_GROUP_ID')
    result = {name: set(values) for name, values in sources.items()}
    if roots:
        result[key] = set(roots)
    else:
        result.pop(key, None)
    return result


def apply_native_source_commands(sources, commands):
    """Native writes cannot erase managed sources or promote them by a no-op replace."""
    requested = apply_commands(source_union(sources), commands)
    managed = source_union({key: values for key, values in sources.items() if key != 'native'})
    if managed - requested:
        raise GroupAuthorityGap('GROUP_AUTHORITY_MANAGED_SOURCE_REQUIRED')
    native = set(sources['native'])
    for command in commands:
        if command[0] == 6:
            target = set(command[2])
            native = (native & target) | (target - managed)
        else:
            native = apply_commands(native, [command])
    return {**sources, 'native': native}


def replace_roles(roots, assignable, requested, technical=()):
    if set(requested) - set(assignable):
        raise GroupAuthorityGap('GROUP_AUTHORITY_ROLE_NOT_ASSIGNABLE')
    return (set(roots) - set(assignable)) | set(requested) | set(technical)
