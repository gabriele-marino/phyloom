import doctest
import importlib
import pkgutil
from types import ModuleType

import pytest

import phyloom


def iter_modules() -> list[ModuleType]:
    modules = [phyloom]
    modules.extend(
        importlib.import_module(name)
        for _, name, _ in pkgutil.walk_packages(
            phyloom.__path__, phyloom.__name__ + "."
        )
    )
    return modules


@pytest.mark.parametrize("module", iter_modules(), ids=lambda m: m.__name__)
def test_docstring_examples(module: ModuleType) -> None:
    finder = doctest.DocTestFinder()
    runner = doctest.DocTestRunner(
        optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    )

    failures = 0
    attempted = 0
    for test in finder.find(module):
        test.globs = {"__builtins__": __builtins__}
        result = runner.run(test)
        failures += result.failed
        attempted += result.attempted

    assert failures == 0, (
        f"{failures} doctest(s) failed in {module.__name__} ({attempted} run)"
    )
