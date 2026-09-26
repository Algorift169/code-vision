"""Entry-point tests for the project bootstrap.

These checks keep the initial package launch path stable while the application
is still in its early GTK bootstrap phase.
"""

import runpy


def test_codevision_module_entrypoint_handles_missing_gtk():
    try:
        runpy.run_module("codevision", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected SystemExit when GTK is unavailable")
