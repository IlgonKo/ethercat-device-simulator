"""Instance-local role lookup acceleration for the externally supplied OD model.

Definition changes must go through define/overlay, as in the model API.
Runtime value writes do not invalidate the index. No dependency class is patched.
"""


def install_role_index(od):
    if getattr(od, '_simulator_role_index_installed', False):
        return
    index = None

    def invalidate_after(method):
        def update(*args, **kwargs):
            nonlocal index
            try:
                return method(*args, **kwargs)
            finally:
                # Even a failed definition update must not leave stale entries.
                index = None
        return update

    def rebuild():
        nonlocal index
        rebuilt = {}
        for entry in od.entries.values():
            rebuilt.setdefault(entry.definition.role, []).append(entry.definition)
        index = rebuilt

    def definition_by_role(role):
        if index is None:
            rebuild()
        matches = index.get(role, ())
        if len(matches) != 1:
            raise KeyError(
                f"Expected one OD definition for role {role!r}, "
                f"found {len(matches)}"
            )
        return matches[0]

    od.define = invalidate_after(od.define)
    od.overlay = invalidate_after(od.overlay)
    od.definition_by_role = definition_by_role
    od._simulator_role_index_installed = True
    # Build before the first cycle, including missing/duplicate role counts.
    rebuild()
