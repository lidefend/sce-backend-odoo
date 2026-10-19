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
        if type(op) is not int:
            raise GroupAuthorityGap('GROUP_AUTHORITY_UNSUPPORTED_COMMAND')
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
    if not isinstance(state, dict) or state.get('version') != 1 or state.get('status') != 'tracked':
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    roots = state.get('roots')
    if not isinstance(roots, list) or any(type(value) is not int or value <= 0 for value in roots):
        raise GroupAuthorityGap('GROUP_AUTHORITY_ORIGIN_UNRESOLVED')
    if set(state.get('observed', [])) != set(current) or set(closure) != set(current):
        raise GroupAuthorityGap('GROUP_AUTHORITY_PROJECTION_DRIFT')
    return set(roots)


def replace_roles(roots, assignable, requested, technical=()):
    if set(requested) - set(assignable):
        raise GroupAuthorityGap('GROUP_AUTHORITY_ROLE_NOT_ASSIGNABLE')
    return (set(roots) - set(assignable)) | set(requested) | set(technical)
