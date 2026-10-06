"""Autonomous DAA decision framework package."""

__all__ = [
    "detect_problem",
    "classify_problem",
    "run_scenario",
    "build_report",
    "generate_architecture_diagram",
]


def __getattr__(name):
    if name in __all__:
        from .framework import (
            detect_problem,
            classify_problem,
            run_scenario,
            build_report,
            generate_architecture_diagram,
        )

        return {
            "detect_problem": detect_problem,
            "classify_problem": classify_problem,
            "run_scenario": run_scenario,
            "build_report": build_report,
            "generate_architecture_diagram": generate_architecture_diagram,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
