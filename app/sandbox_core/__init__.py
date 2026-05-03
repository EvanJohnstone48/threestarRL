"""Sandbox-core — pure-Python deterministic Clash-style attack simulator.

The simulator owns all world state and produces replays. It is headless,
RL-importable, and emits JSON artifacts validated by Pydantic v2 models.

See app/docs/technical.md §5 for architecture and app/docs/prd.md §5.1 for FRs.
"""

__version__ = "0.1.0"
