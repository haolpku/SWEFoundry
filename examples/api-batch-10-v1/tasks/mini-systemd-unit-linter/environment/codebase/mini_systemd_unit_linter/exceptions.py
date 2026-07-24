class UnitLintError(Exception):
    'Base exception for the educational unit linter.'


class DependencyCycleError(UnitLintError):
    'Raised when a deterministic activation order cannot be computed.'

    def __init__(self, cycle):
        self.cycle = tuple(sorted(str(item) for item in cycle))
        super().__init__('dependency cycle: ' + ', '.join(self.cycle))
