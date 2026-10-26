"""SB3 training callbacks for scientific observability (STAGE 6 / PHASE 13).

``ThesisLoggingCallback`` records, per rollout, the signals needed to interpret
training without re-defining anything frozen:

  * reward components (leak/unserved/deficit/movement/energy terms, from the
    D-P6-005 RewardBreakdown in ``info['reward_breakdown']``);
  * hydraulic metrics (leak, DSR, deficit, min service pressure, negative-pressure
    count) from ``info['metrics']``;
  * safety outcomes (accepted / reject_to_hold / reference_fallback counts and the
    acceptance rate) from ``info['outcome']``;
  * action statistics (mean |proposed|, mean |executed|, mean movement) from the
    Phase-4 traceability keys.

It LOGS ONLY -- it never changes the reward, observation, action, or safety
decision. stable-baselines3 is imported lazily so this file can be imported for
inspection on a machine without the RL stack.
"""

from __future__ import annotations

import numpy as np

try:
    from stable_baselines3.common.callbacks import BaseCallback
    _HAS_SB3 = True
except Exception:  # noqa: BLE001
    BaseCallback = object  # type: ignore
    _HAS_SB3 = False


class ThesisLoggingCallback(BaseCallback):
    """Aggregate frozen env diagnostics into the SB3 logger each rollout."""

    def __init__(self, verbose: int = 0):
        if not _HAS_SB3:
            raise RuntimeError("stable-baselines3 is required for ThesisLoggingCallback")
        super().__init__(verbose)
        self._reset_acc()

    def _reset_acc(self):
        self._acc = {k: [] for k in (
            "leak_gpm", "dsr", "deficit", "min_pressure_psi", "n_neg",
            "r_leak", "r_unserved", "r_deficit", "r_movement",
            "abs_proposed", "abs_executed", "movement_l2sq", "safety_dp_min")}
        self._outcomes = {"accepted": 0, "reject_to_hold": 0,
                          "reference_fallback": 0, "no_safety": 0}
        # STEP-10: active scenario per step (native -> None; train/val/test/ood
        # -> the episode's demand multiplier). Logged as env/scenario_multiplier
        # and, once per episode, env/scenario_id.
        self._scenario_mults = []
        self._last_scenario_id = None
        self._last_seed_provenance = None

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            m = info.get("metrics")
            rb = info.get("reward_breakdown")
            sc = info.get("demand_scenario")
            if sc is not None:
                self._last_scenario_id = sc.get("scenario_id")
                self._last_seed_provenance = info.get("scenario_seed_provenance")
                if "multiplier" in sc:
                    self._scenario_mults.append(float(sc["multiplier"]))
            if m is not None:
                self._acc["leak_gpm"].append(m.leak_gpm)
                self._acc["dsr"].append(m.dsr)
                self._acc["deficit"].append(m.deficit_psi_nodesum)
            # TRUE endpoint service-pressure diagnostics (frozen 121-node definitions).
            if "min_service_pressure_psi" in info:
                self._acc["min_pressure_psi"].append(info["min_service_pressure_psi"])
            if "n_service_nodes_negative" in info:
                self._acc["n_neg"].append(info["n_service_nodes_negative"])
            if rb is not None:
                self._acc["r_leak"].append(rb.leak_term)
                self._acc["r_unserved"].append(rb.unserved_term)
                self._acc["r_deficit"].append(rb.deficit_term)
                self._acc["r_movement"].append(rb.movement_term)
                self._acc["movement_l2sq"].append(rb.movement_l2sq)
            dec = info.get("safety")
            if dec is not None:
                # RELATIVE guard margin p_min(proposed) - p_min(hold); not a pressure.
                self._acc["safety_dp_min"].append(
                    float(getattr(dec, "min_dp_min_psi", np.nan)))
            self._outcomes[info.get("outcome", "no_safety")] = \
                self._outcomes.get(info.get("outcome", "no_safety"), 0) + 1
            p = info.get("proposed_action_norm")
            e = info.get("executed_action_norm")
            if p is not None:
                self._acc["abs_proposed"].append(float(np.mean(np.abs(p))))
            if e is not None:
                self._acc["abs_executed"].append(float(np.mean(np.abs(e))))
        return True

    def _on_rollout_end(self) -> None:
        rec = self.logger.record
        for k, v in self._acc.items():
            if v:
                rec(f"env/{k}", float(np.nanmean(v)))
        if self._scenario_mults:
            rec("env/scenario_multiplier", float(np.mean(self._scenario_mults)))
        if self._last_scenario_id is not None:
            rec("env/scenario_id", self._last_scenario_id)
        if self._last_seed_provenance is not None:
            # Provenance logging only; never affects training semantics. The
            # fixed-scenario branch has no stream seed, so only the train
            # branch emits these keys.
            prov = self._last_seed_provenance
            if prov.get("effective_stream_seed") is not None:
                rec("env/scenario_stream_seed", prov["effective_stream_seed"])
            if prov.get("draw_index") is not None:
                rec("env/scenario_draw_index", prov["draw_index"])
        total = sum(self._outcomes.values()) or 1
        for k, c in self._outcomes.items():
            rec(f"safety/{k}", c)
        rec("safety/accept_rate", self._outcomes.get("accepted", 0) / total)
        self._reset_acc()
