# BWSN-1 PPO — Local-dev + Colab-training procedure

**Role split (do not mix):**
- **Windows laptop (`D:\Thesis`)** — develop + validate source, run unit tests, run
  the real-EPANET smoke, prepare configs. **No long/expensive PPO training here.**
  A tiny `--smoke` is allowed only for integration debugging and is *never* thesis evidence.
- **Google Colab (GPU)** — PPO training, multiple seeds, baselines, scenario/robustness
  evaluation, ablations, final policy evaluation.

All pipeline code is path-portable (`experiments/ppo/*` derive the project root from
`__file__`), so a checkout at `/content/Thesis` works unchanged.

## Exact Colab procedure

1. **(optional) mount Drive** for persistent checkpoints/results:
   ```python
   from google.colab import drive; drive.mount('/content/drive')
   ```
2. **Get the repo** at the exact revision used locally (record the commit):
   ```bash
   cd /content && git clone <REPO_URL> Thesis && cd Thesis && git checkout <COMMIT>
   ```
   (or upload/sync the working tree; the benchmark INP must transfer intact.)
3. **Install deps on top of Colab's preinstalled CUDA torch** (do not reinstall torch):
   ```bash
   pip install -r experiments/colab/requirements-colab.txt
   ```
4. **Verify environment + GPU + hydraulic anchor + SB3 contract** (authoritative gate):
   ```bash
   python -m experiments.ppo.verify_env --full
   ```
   This prints versions + device (expects `cuda_available: true` on a GPU runtime),
   confirms the working-INP SHA matches `53015ba9…`, asserts the native leak anchor
   `84.72988433677985` GPM at `rel < 5e-5`, and runs the SB3 env-checker + a PPO
   construct/predict/tiny-learn + checkpoint round-trip. **If the leak anchor or the
   INP SHA fails, STOP** — investigate version/engine/transfer drift before training.
5. **Cross-environment consistency:** compare the Colab
   `runs/_verify/fingerprint_<host>.json` against the laptop's
   `fingerprint_Ali-Y.json` (obs shape, leak anchor match, horizon). Materially
   different hydraulics ⇒ STOP.
6. **(optional) full env unit battery:**
   ```bash
   python -m unittest tests.test_action_mapper tests.test_metrics_reward \
       tests.test_safety tests.test_baselines tests.test_env_integration \
       tests.test_ppo_traceability
   ```
7. **Development training run** (DEVELOPMENT evidence until STEP-10 is frozen):
   ```bash
   python -m experiments.ppo.train --experiment-id dev_run_s0 \
       --total-timesteps 50000 --seed 0 --device auto --checkpoint-freq 5000
   ```
8. **Resume** after a runtime reset (checkpoints should live on Drive):
   ```bash
   python -m experiments.ppo.train --experiment-id dev_run_s0 \
       --resume runs/dev_run_s0/checkpoints/ppo_<N>_steps.zip --total-timesteps 50000
   ```
9. **Deterministic evaluation:**
   ```bash
   python -m experiments.ppo.evaluate --model runs/dev_run_s0/final_model.zip \
       --experiment-id dev_run_s0 --seed 0
   ```
10. **Persist** `runs/<id>/` (config.yaml, metadata.json, checkpoints, evaluation) to Drive.

## Scientific boundaries
- `--total-timesteps` here is a **development** budget to confirm the pipeline learns,
  not a thesis result.
- **STEP-10 is NOT frozen** (no demand-scenario/robustness/baseline protocol). Do not
  make robustness/OOD/superiority claims from development runs. The final experiment
  program (PHASE 15) runs only after STEP-10 is minted.
- The reward (D-P6-005) and safety (D-P6-006) are frozen; the pipeline logs but never
  redefines them.
