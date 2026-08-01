class LocalStateError(RuntimeError):
    pass


class InvalidStateIdError(LocalStateError):
    pass


class StateConflictError(LocalStateError):
    pass


class StateCorruptionError(LocalStateError):
    pass


class ProjectStateBusyError(LocalStateError):
    pass
