"""Per-control-step hydraulic metrics for the D-P6-005 reward.

This module turns ONE ``StepResult`` (the realised end-of-control-step hydraulic
state produced by ``epanet_adapter.SteppingHydraulicDriver``) into the four
scalar quantities the frozen reward consumes:

    leak_gpm            total emitter leakage at the endpoint instant
    unserved_pos_gpm    max(0, requested - served) at the endpoint instant
    deficit_psi_nodesum sum of (20 - p)^+ over the 121 service junctions
    power_kw            total pump hydraulic power at the endpoint instant

PROVENANCE (frozen accounting law)
----------------------------------
These are the SAME definitions as the whole-horizon water balance in
``g6_g7_g8_leak_pda.accounting`` (lines 159-253), restricted to a single report
instant. That function froze the Phase-5/6 anchors (native leak 84.72988 GPM,
DSR 0.98334, 386 node-ts < 20 psi, 0 negative), so computing the per-step
metrics by the identical law is what keeps the episode's pooled statistics
comparable to those anchors.

    signed emitter law   q_j   = sign(p_j) * |p_j|^0.5 * coeff[j]      (alpha=0.5)
    leak                 L     = sum_j q_j            over ALL junctions
    served               S     = (sum_j demand_j) - L  demand_j = reported nodal
                                                        demand (includes emitter)
    requested            R     = sum_j requested_j   expected_demand at the clock
    unserved             U     = R - S;  U^+ = max(0, U)
    deficit              D     = sum_{j in service} max(0, 20 - p_j)
    power                P     = sum_pumps max(0, rho*g*Q*dH) / 1000  (kW)

NODE SETS (deliberately different, matching the frozen law):
  * leak / served / requested sum over the FULL junction set (``accounting`` uses
    ``wn.junction_name_list``); connectors carry zero base demand so they add no
    requested demand, and their emitter contribution -- if any -- is part of the
    frozen balance, so they are NOT dropped here.
  * deficit sums over the 121 SERVICE junctions only (connectors are excluded
    service artefacts, D-P6-004), matching D-P6-005 s.8.1.

Pure: no EPANET calls, no reward weights, no normalisation. The reward layer
(``reward.py``) applies the frozen weights and reference normalisers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SERVICE_PSI = 20.0            # service / PDA threshold (frozen)
LEAK_EXPONENT = 0.5           # signed emitter exponent (g6_g7_g8_leak_pda.accounting)


@dataclass
class StepMetrics:
    """The four reward drivers plus the raw balance terms, for one instant."""
    leak_gpm: float
    served_gpm: float
    requested_gpm: float
    unserved_gpm: float          # signed: requested - served (may be < 0)
    unserved_pos_gpm: float      # max(0, unserved) -- the reward term
    deficit_psi_nodesum: float   # sum over 121 service nodes
    power_kw: float
    dsr: float                   # served / requested (demand satisfaction, for logs)


def step_metrics(step, coeff_us: dict[str, float],
                 service_nodes: list[str]) -> StepMetrics:
    """Compute the frozen per-instant metrics from one ``StepResult``.

    ``step``          an ``epanet_adapter.StepResult`` (endpoint instant).
    ``coeff_us``      leak coefficients (GPM / psi^alpha), one per junction.
    ``service_nodes`` the 121 service junctions used for the pressure deficit.
    """
    p = step.pressures_psi
    dem = step.demand_gpm
    reqd = step.requested_gpm

    # leak over the full junction set (every node that carries a leak coefficient
    # and has a reported pressure), signed emitter law q = sign(p)|p|^alpha * C.
    leak = 0.0
    for j, c in coeff_us.items():
        pj = p[j]
        leak += float(np.sign(pj) * abs(pj) ** LEAK_EXPONENT) * float(c)

    q_total = float(sum(dem.values()))                 # reported demand (incl. emitter)
    req_total = float(sum(reqd.values())) if reqd else 0.0
    served = q_total - leak
    unserved = req_total - served
    unserved_pos = max(0.0, unserved)

    deficit = 0.0
    for j in service_nodes:
        deficit += max(0.0, SERVICE_PSI - float(p[j]))

    power = float(sum(step.pump_power_kw.values()))
    dsr = (served / req_total) if req_total > 0.0 else float("nan")

    return StepMetrics(
        leak_gpm=leak,
        served_gpm=served,
        requested_gpm=req_total,
        unserved_gpm=unserved,
        unserved_pos_gpm=unserved_pos,
        deficit_psi_nodesum=deficit,
        power_kw=power,
        dsr=dsr,
    )
