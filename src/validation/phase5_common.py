"""Phase 5 - BWSN-1 pre-flight validation: shared utilities.

Scope discipline (Phase 5 rules): validation and falsification only.
No RL training, no hyperparameter search, no reward tuning, no GA/PSO valve
placement, no topology edits. Every number produced by this package is either
read directly from the model file or computed by the EPANET / WNTR solver.

The distributed model file is never modified in place. A working copy is
produced by `build_working_copy()` from an explicit, auditable patch list.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "networks"
WORKDIR = DATA / "working"
RESULTS = REPO / "results" / "phase5"
ORIGINAL_INP = DATA / "BWSN_Network_1.inp"
WORKING_INP = WORKDIR / "BWSN_Network_1_working.inp"

# Provenance of the distributed model file. Both mirrors were fetched on
# 2026-09-02 and returned byte-identical content (same SHA-256).
PROVENANCE = {
    "file": "BWSN_Network_1.inp",
    "benchmark": "BWSN Network 1 (Battle of the Water Sensor Networks, 2008)",
    "size_bytes": 44402,
    "sha256": "510af942ec643eb87adcf26e5a7df1cc4c23eb0c1e470a8a1257ed055f1956f1",
    "md5": "09bf6a2879a045f5e7c5f0986ff78261",
    "mirrors_verified_identical": [
        "https://filedn.com/lumBFq2P9S74PNoLPWtzxG4/EPyT-Flow/Networks/BWSN_Network_1.inp",
        "https://raw.githubusercontent.com/OpenWaterAnalytics/EPyT/dev/"
        "epyt/networks/asce-tf-wdst/BWSN_Network_1.inp",
    ],
    "mirror_not_found": [
        "https://raw.githubusercontent.com/KIOS-Research/EPANET-Benchmarks/"
        "master/BWSN_Network_1.inp"
    ],
    "downloaded_utc": "2026-09-02",
}
# ---------------------------------------------------------------------------
# The ONLY textual edit applied to the distributed file.
#
# WNTR 1.5.0 refuses to parse `[OPTIONS] Quality  Chemical TIME`: its reader
# (wntr/epanet/io.py::_read_options) requires the third token on a CHEMICAL
# quality line to contain "mg" or "ug", and raises ENValueError(213) otherwise.
# Native EPANET 2.x accepts the line. The token names the *water-quality mass
# unit*; this thesis performs hydraulic analysis only, so the substitution
# cannot change any hydraulic result. EPANET solves hydraulics independently of
# the quality module.
# ---------------------------------------------------------------------------
PATCHES = [
    {
        "id": "P1-quality-units-token",
        "find": "Quality            \tChemical TIME",
        "replace": "Quality            \tChemical mg/L",
        "reason": (
            "WNTR 1.5.0 cannot parse the non-standard chemical-unit token "
            "'TIME'. Replaced with the EPANET default mass unit 'mg/L'. "
            "Water-quality analysis is not used anywhere in this thesis; "
            "hydraulics are unaffected."
        ),
        "hydraulically_neutral": True,
    }
]

# Runtime option overrides applied in-memory by the test scripts, never written
# into the working .inp. Each is logged with the run that used it.
RUNTIME_NOTES = {
    "rule_timestep": (
        "The distributed [TIMES] section does not declare a rule timestep. "
        "Native EPANET then defaults to 1/10 of the hydraulic timestep = 180 s "
        "(confirmed via EPyT getTimeRuleControlStep). WNTR's own default is "
        "360 s, so an unmodified WNTR run evaluates the tank-level pump rules "
        "at half the native frequency. Every run here sets 180 s explicitly."
    ),
    "report_timestep": (
        "The distributed file reports every 1:00 while solving every 0:30. "
        "Tests that need half-hourly output set report_timestep = 1800 s "
        "in memory. This changes output resolution only, not the solution."
    ),
}
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def env_info() -> dict:
    """Everything needed to reproduce a run. Recorded with every gate."""
    import numpy
    import pandas
    import scipy
    import networkx
    import wntr

    info = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "os": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "python_build": platform.python_build()[1],
        "wntr": wntr.__version__,
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
        "scipy": scipy.__version__,
        "networkx": networkx.__version__,
        "epanet_engine_wntr": _wntr_epanet_version(),
        "epanet_engine_epyt": _epyt_epanet_version(),
        "original_inp_sha256": sha256_file(ORIGINAL_INP) if ORIGINAL_INP.exists() else None,
        "working_inp_sha256": sha256_file(WORKING_INP) if WORKING_INP.exists() else None,
        "determinism": (
            "EPANET's hydraulic solver is deterministic. No stochastic input is "
            "used anywhere in Phase 5; leak-node selection and leak-coefficient "
            "allocation are closed-form functions of pipe length, so no random "
            "seed is required. Recorded seed: none used."
        ),
    }
    return info


def _wntr_epanet_version():
    """Query the EPANET shared libraries bundled with WNTR directly."""
    import ctypes
    import os

    import wntr.epanet

    base = os.path.join(os.path.dirname(wntr.epanet.__file__), "libepanet", "windows-x64")
    out = {}
    if not os.path.isdir(base):
        return "libepanet/windows-x64 not present"
    for fname in sorted(os.listdir(base)):
        if not fname.endswith(".dll") or "msx" in fname:
            continue
        try:
            lib = ctypes.CDLL(os.path.join(base, fname))
            ver = ctypes.c_int()
            lib.ENgetversion(ctypes.byref(ver))
            out[fname] = ver.value
        except Exception as exc:  # pragma: no cover - diagnostic only
            out[fname] = f"unavailable: {type(exc).__name__}"
    return out

def _epyt_epanet_version():
    try:
        import io as _io
        import contextlib

        from epyt import epanet

        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            d = epanet(str(ORIGINAL_INP))
            v = d.getVersion()
            d.unload()
        return v
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f"unavailable: {type(exc).__name__}"


def read_sections(path: Path) -> dict[str, list[str]]:
    """Section-aware raw reader. Comments stripped, blank lines dropped."""
    out: dict[str, list[str]] = {}
    cur = None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*\[([A-Za-z_]+)\]", line)
        if m:
            cur = m.group(1).upper()
            out.setdefault(cur, [])
            continue
        if cur is None:
            continue
        body = line.split(";")[0].strip()
        if body:
            out[cur].append(body)
    return out


def build_working_copy(verbose: bool = True) -> dict:
    """Create the patched working copy. The original is never touched."""
    WORKDIR.mkdir(parents=True, exist_ok=True)
    text = ORIGINAL_INP.read_text(encoding="utf-8", errors="replace")
    applied = []
    for patch in PATCHES:
        n = text.count(patch["find"])
        if n != 1:
            raise RuntimeError(
                f"patch {patch['id']}: expected exactly 1 match, found {n}. "
                "Refusing to guess. The input file is not the expected revision."
            )
        text = text.replace(patch["find"], patch["replace"])
        applied.append({**patch, "matches": n})
    WORKING_INP.write_text(text, encoding="utf-8")
    record = {
        "original": str(ORIGINAL_INP),
        "original_sha256": sha256_file(ORIGINAL_INP),
        "working": str(WORKING_INP),
        "working_sha256": sha256_file(WORKING_INP),
        "patches_applied": applied,
        "provenance": PROVENANCE,
        "runtime_notes": RUNTIME_NOTES,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "working_copy_provenance.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    if verbose:
        print(f"original sha256 {record['original_sha256']}")
        print(f"working  sha256 {record['working_sha256']}")
        print(f"patches applied {[p['id'] for p in applied]}")
    return record


def load_wn(rule_timestep: int = 180, report_timestep: int | None = None):
    """Load the working copy with the native rule timestep restored."""
    import wntr

    if not WORKING_INP.exists():
        build_working_copy(verbose=False)
    wn = wntr.network.WaterNetworkModel(str(WORKING_INP))
    wn.options.time.rule_timestep = rule_timestep
    if report_timestep is not None:
        wn.options.time.report_timestep = report_timestep
    return wn


def run_epanet(wn, prefix: str):
    """Run the EPANET 2.x engine through WNTR. Returns (results, warnings)."""
    import warnings as _w

    import wntr

    tmp = RESULTS / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    sim = wntr.sim.EpanetSimulator(wn)
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        res = sim.run_sim(file_prefix=str(tmp / prefix))
    msgs = sorted({f"{c.category.__name__}: {c.message}" for c in caught})
    return res, msgs
# --- unit helpers -----------------------------------------------------------
# WNTR works in SI internally (m, m3/s). The model file is GPM/psi/ft.
# All conversions go through WNTR's own converters so no constant is invented.

def _fu():
    from wntr.epanet.util import FlowUnits

    return FlowUnits.GPM


def m_to_psi(x):
    from wntr.epanet.util import HydParam, from_si

    return from_si(_fu(), x, HydParam.Pressure)


def m_to_ft(x):
    from wntr.epanet.util import HydParam, from_si

    return from_si(_fu(), x, HydParam.HydraulicHead)


def m3s_to_gpm(x):
    from wntr.epanet.util import HydParam, from_si

    return from_si(_fu(), x, HydParam.Flow)


def psi_to_m(x):
    from wntr.epanet.util import HydParam, to_si

    return to_si(_fu(), x, HydParam.Pressure)


def gpm_to_m3s(x):
    from wntr.epanet.util import HydParam, to_si

    return to_si(_fu(), x, HydParam.Flow)


def jdump(name: str, payload: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[written] {path}")
    return path





