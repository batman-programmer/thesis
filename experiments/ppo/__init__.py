"""BWSN-1 PPO pipeline (portable local-dev + Colab-training).

Modules
-------
make_env    : portable env factory (project root from __file__; no hard-coded path)
config      : PPOConfig + device resolution + reproducibility metadata + run layout
callbacks   : ThesisLoggingCallback (SB3 observability, logging-only)
train       : configuration-driven PPO training launcher
evaluate    : deterministic evaluation entry point (frozen metrics only)
verify_env  : cross-environment verification + real-EPANET/SB3 smoke tool

The frozen scientific semantics (D-P6-001..006) live in ``src/env`` and are NOT
re-implemented here; this package only orchestrates training/evaluation around them.
"""
