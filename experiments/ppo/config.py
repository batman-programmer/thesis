"""Training configuration + reproducibility metadata for the BWSN-1 PPO pipeline.

Design goals
------------
* PORTABLE: the project root is derived from ``__file__`` (no ``D:\\Thesis``); run
  directories live under ``experiments/ppo/runs/<experiment_id>/`` relative to it,
  so the same code produces the same layout on the laptop and on Colab.
* DEVICE-AGNOSTIC: ``resolve_device("auto")`` picks CUDA only when a *functioning*
  CUDA GPU is actually present, else CPU. The chosen device is recorded, never
  assumed.
* NO HIDDEN SCIENTIFIC DEFAULTS: every PPO hyperparameter and every frozen-spec
  identifier (D-P6-001..006) is written into ``metadata.json`` + ``config.yaml``.
* HONEST: nothing here claims the hyperparameters are optimal; they are a
  conventional, conservative single-environment starting configuration. torch /
  stable-baselines3 / gymnasium are imported LAZILY so this module loads on a
  machine without the RL stack (version capture degrades to ``"NOT INSTALLED"``).

The frozen numbers (bounds, reward weights/normalisers, safety defaults, horizon)
are mirrored from PROJECT_STATE.yaml / docs for the run record ONLY; the authoritative
runtime values still come from the frozen ``src/env`` modules, never from here.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "experiments" / "ppo" / "runs"
WORKING_INP = PROJECT_ROOT / "data" / "networks" / "working" / "BWSN_Network_1_working.inp"

# Frozen-spec identifiers (for the run record; authoritative values live in src/env).
FROZEN_SPEC = {
    "action_dim": 7,
    "observation_dim": 139,
    "action_order": ["VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178",
                     "PUMP-170", "PUMP-172"],
    "n_control_steps": 192,
    "report_instants": 193,
    "control_step_s": 1800,
    "rule_timestep_s": 180,
    "horizon_s": 96 * 3600,
    "decisions": {
        "D-P6-001": "ABSOLUTE action encoding",
        "D-P6-002": "pump bounds",
        "D-P6-003": "PRV bounds",
        "D-P6-004": "139-dim observation",
        "D-P6-005": "reward C-A_F1_balanced_dense",
        "D-P6-006": "safety F1 execution-time admissibility (HOLD counterfactual)",
    },
    # LINE-ENDING-INDEPENDENT anchor: SHA-256 of the INP with CRLF/CR normalized to
    # LF in memory (see normalized_sha256). This equals the git blob's own hash, so
    # it is identical on Windows (CRLF checkout) and Linux/Colab (LF checkout).
    # The raw-byte digest of a CRLF Windows checkout is
    # 53015ba9212e46bec731d190971819996233996b498bc269e828f992830a20a9 -- recorded
    # for provenance only; the file content is identical modulo line endings.
    "working_inp_sha256_expected":
        "f14db5930f5b8c648a2e81f56a3f1b560e94b7c83745ec4def4fab53f9583cea",
    "working_inp_sha256_raw_crlf_windows":
        "53015ba9212e46bec731d190971819996233996b498bc269e828f992830a20a9",
    "hydraulic_stack_frozen": "WNTR 1.5.0 / EPANET 2.2 (engine 20200)",
}


@dataclass
class PPOConfig:
    """One PPO run's configuration.

    Hyperparameters are a CONVENTIONAL, CONSERVATIVE single-environment starting
    point (NOT claimed optimal). ``n_steps=192`` aligns one rollout to one 96 h
    episode (192 control transitions); the rollout is intentionally small because
    each safety-enabled env step runs multiple real EPANET solves (see
    ``verify_env.py`` for the measured per-step cost).
    """
    experiment_id: str = "dev_smoke"
    seed: int = 0
    device: str = "auto"                 # auto -> cuda if functional else cpu

    # --- PPO hyperparameters (provisional; conventional defaults) ---
    total_timesteps: int = 192           # dev default = 1 episode; raise on Colab
    learning_rate: float = 3.0e-4
    n_steps: int = 192                   # 1 full episode per rollout
    batch_size: int = 64                 # divides 192 (= 3 minibatches)
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.0
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    net_arch: list = field(default_factory=lambda: [256, 256])
    activation: str = "tanh"

    # --- environment / protocol ---
    enable_safety: bool = True
    safety_eps_p_psi: float = 0.0        # frozen D-P6-006 default
    safety_horizon_steps: int = 1        # frozen D-P6-006 default
    network: str = "BWSN-1"
    # STEP-10 (D-P6-007): "native" (frozen anchor path), "train" (per-episode
    # stream draws), or a fixed evaluation id ("val/<i>" / "test/<i>" / "ood/<i>").
    demand_scenario: str = "native"
    # STEP-10 D5: baseline condition trained under ("joint" = full 7-dim action
    # space, the default PPO condition; "prv_only"/"vsp_only" mask the non-free
    # dims to native during TRAINING via baselines.apply_mask -- each is a
    # SEPARATE trained policy, never a post-hoc mask of a joint policy).
    baseline_mode: str = "joint"
    scenario_master_seed: int = 20261019  # frozen D-P6-007 master seed

    # --- run management ---
    eval_freq: int = 0                   # 0 = no periodic eval during dev smoke
    checkpoint_freq: int = 0             # 0 = final-only; >0 = every N steps
    tensorboard: bool = True

    def minibatch_divides(self) -> bool:
        return (self.n_steps % self.batch_size) == 0


def smoke_config(experiment_id: str = "dev_smoke") -> PPOConfig:
    """Deliberately tiny budget for integration smoke tests (NOT research)."""
    return PPOConfig(experiment_id=experiment_id, total_timesteps=16, n_steps=8,
                     batch_size=8, n_epochs=2, eval_freq=0, checkpoint_freq=0)


# --------------------------------------------------------------------------- #
# device + reproducibility                                                     #
# --------------------------------------------------------------------------- #
def resolve_device(pref: str = "auto") -> str:
    """Return 'cuda' only when a functioning CUDA GPU is actually available."""
    if pref == "cpu":
        return "cpu"
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _pkg_version(name: str) -> str:
    try:
        import importlib.metadata as md
        return md.version(name)
    except Exception:
        return "NOT INSTALLED"


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", str(PROJECT_ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def normalized_sha256(data: bytes) -> str:
    """SHA-256 over content whose line endings are normalized to LF in memory.

    The repository stores the benchmark INP with LF endings, but this checkout has
    ``core.autocrlf=true``, so Windows working copies materialise CRLF while Linux
    ones stay LF. Hashing the raw bytes therefore yields a platform-dependent
    digest for BYTE-IDENTICAL content (verified on this repo: the CRLF worktree is
    45063 B and hashes to 53015ba9...; normalizing removes exactly its 661 CRLF
    pairs, giving 44402 B and f14db593..., which equals the git blob's own hash).

    Normalization happens IN MEMORY ONLY -- the .inp file is never rewritten, and
    no hydraulic parameter, solver setting or baseline value is involved.
    """
    return hashlib.sha256(
        data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def _working_inp_sha256() -> str:
    """Line-ending-independent SHA-256 of the working INP (the comparison anchor)."""
    if not WORKING_INP.exists():
        return "MISSING"
    return normalized_sha256(WORKING_INP.read_bytes())


def _working_inp_sha256_raw() -> str:
    """Raw-byte SHA-256 -- DIAGNOSTIC ONLY (platform-dependent; not an anchor)."""
    if not WORKING_INP.exists():
        return "MISSING"
    return hashlib.sha256(WORKING_INP.read_bytes()).hexdigest()


def device_report(pref: str = "auto") -> dict:
    """Actual (not assumed) device facts: cuda availability, name, versions."""
    rep = {"preference": pref, "resolved": resolve_device(pref),
           "cuda_available": False, "gpu_name": None, "torch_cuda_version": None}
    try:
        import torch
        rep["cuda_available"] = bool(torch.cuda.is_available())
        if rep["cuda_available"]:
            rep["gpu_name"] = torch.cuda.get_device_name(0)
            rep["torch_cuda_version"] = getattr(torch.version, "cuda", None)
    except Exception:
        pass
    return rep


def reproducibility_metadata(config: PPOConfig) -> dict:
    """Full run record: timestamp, git, versions, device, specs, hyperparameters.

    Every value is read live (versions via importlib.metadata, device via torch);
    nothing is fabricated. ``working_inp_sha256`` is recomputed so a corrupted
    file transfer to Colab is caught (compare against FROZEN_SPEC expected hash).
    """
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "device": device_report(config.device),
        "versions": {k: _pkg_version(k) for k in
                     ("torch", "stable-baselines3", "gymnasium", "numpy",
                      "pandas", "scipy", "wntr", "epyt", "PyYAML")},
        "working_inp_sha256": _working_inp_sha256(),
        "frozen_spec": FROZEN_SPEC,
        "config": asdict(config),
    }


def set_global_seeds(seed: int) -> None:
    """Seed python/numpy/torch (where present). Does NOT claim cross-machine bits."""
    import random
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# run directory layout                                                          #
# --------------------------------------------------------------------------- #
@dataclass
class RunLayout:
    """``runs/<experiment_id>/`` with checkpoints/ logs/ evaluation/ summaries/."""
    experiment_id: str
    root: Path = None  # set in __post_init__

    def __post_init__(self):
        self.root = RUNS_DIR / self.experiment_id
        for sub in ("checkpoints", "logs", "evaluation", "summaries"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    @property
    def checkpoints(self) -> Path: return self.root / "checkpoints"
    @property
    def logs(self) -> Path: return self.root / "logs"
    @property
    def evaluation(self) -> Path: return self.root / "evaluation"
    @property
    def summaries(self) -> Path: return self.root / "summaries"
    @property
    def final_model(self) -> Path: return self.root / "final_model.zip"

    def write_config(self, config: PPOConfig) -> Path:
        meta = reproducibility_metadata(config)
        (self.root / "metadata.json").write_text(json.dumps(meta, indent=2))
        cfg_path = self.root / "config.yaml"
        try:
            import yaml
            cfg_path.write_text(yaml.safe_dump(asdict(config), sort_keys=False))
        except Exception:
            cfg_path = self.root / "config.json"
            cfg_path.write_text(json.dumps(asdict(config), indent=2))
        return cfg_path
