"""Barracks — the RL environment, training loop, and eval pipeline.

Wraps sandbox_core in a Gymnasium-compliant environment, trains agents via
Stable-Baselines3 MaskablePPO, and evaluates against the frozen held-out base set.

See app/docs/barracks/design.md for the RL-specific design and
app/docs/technical.md §6 for architecture summary.
"""

__version__ = "0.1.0"
