# Experiment journal

Collect report material here while the work happens. Record successful runs, failures, unsuccessful fixes, surprising results, limitations, and AI suggestions that were accepted or corrected. Keep the original observations when a conclusion changes; add a dated correction.

This journal can be longer than the final two-page report. Keep choices and their justification in [DECISIONS.md](DECISIONS.md), and link between the two records when an experiment changes a decision.

## Where report material lives

| Report material | Working source |
| --- | --- |
| Why this model, dataset, and stack? | `DECISIONS.md`, sections 1, 2, and 4. |
| Memory estimate, actual peaks, and explanation of the gap | A journal entry containing the estimate before training, followed by measured results and linked raw memory evidence. Preserve the original estimate. |
| Proof of meaningful training and the base/merged/4-bit comparison | Journal entries linking verification commands, configurations, outputs, artifact identities, and the checks' limitations. |
| Silent failures and Soup coverage | An entry for each investigated failure or injected control, including detection evidence for each relevant Soup check. |
| What broke, what we tried, and what we learned | Each entry's observations, attempts, results, and lesson. Preserve failed attempts. |
| SHIP or DON'T SHIP | The policy recorded before the main run in `DECISIONS.md`, section 7, followed by a journal entry applying it to the results. |
| Reflection and remaining concerns | Lessons and concerns recorded in entries, then an applicant-reviewed reflection paragraph at submission. |
| AI assistance and independent review | `DECISIONS.md`, section 8, plus the specific suggestions, corrections, and human checks recorded in each relevant entry. |

## How to capture an entry

- Give each entry an ID and an ISO 8601 timestamp with timezone. If recording an earlier event, distinguish the time of writing from the event time; mark unknown times explicitly.
- Capture the exact command, code/configuration version, relevant environment, and raw output for each attempt. Use a separate directory such as `evidence/<run-id>/` for each run. Include timestamps in new logs and preserve raw `nvidia-smi` output alongside allocator measurements.
- Distinguish observed facts, hypotheses, planned checks, and deliberate failure injections. A failed run is not automatically a silent failure; explain how an apparently successful run could conceal the issue.
- Record Soup's data doctor, pre-flight, and ship coverage separately as **caught**, **missed**, **not tested**, or **not applicable**. Link command output or inspected implementation supporting the conclusion. A documentation claim alone is not a live test.
- Add one short report takeaway after an investigation. Keep detailed evidence here so the final report can explain the result concisely.

Copy this template for each run or investigation; omit fields that do not apply:

```markdown
### E___ - <stage: short description>

- Recorded at: <timestamp with timezone>
- Event/run time: <timestamp, or unknown if retrospective>
- Kind and status: <run / real failure / injected control / correction; planned / observed / unresolved / resolved>
- Question or expected behavior: <what we were trying to establish>
- What happened: <observations; separate any suspected cause>
- What we tried and the results: <each attempt, including unsuccessful ones>
- Evidence: <exact commands; code/config/model/data revisions as relevant; links to raw logs and outputs>
- Soup coverage: <doctor / pre-flight / ship; result and supporting evidence for each relevant check>
- What we learned: <supported conclusion and its limits>
- What still concerns us: <remaining uncertainty or next check>
- Report takeaway: <one or two sentences supported by the evidence>
- AI and human review: <suggestion accepted, changed, or rejected; who verified what; mark review pending when appropriate>
```

## Entries

### E001 - Planning and existing evidence inventory

- Recorded at: 2026-11-10T17:36:09+05:00 (Asia/Almaty).
- Event/run time: retrospective; exact times of earlier setup actions are not recorded in the existing setup logs.
- Kind and status: repository inventory; observed. This entry is not a training run or a failure injection.
- What happened: [DECISIONS.md](DECISIONS.md) records Qwen3-1.7B and a curated xLAM subset as selected, and an instrumented training loop with separate Soup checks as planned. No training implementation, verification script, or measured model results are present in the repository.
- Existing evidence: [dependency installation output](evidence/setup/dependencies.log) and [Brev instance creation output](evidence/setup/brev-create.log). These document setup actions; they do not establish the current cloud state or GPU pipeline compatibility.
- Evidence gap: the existing setup logs do not contain timestamps. Preserve them as they are; capture timestamps in subsequent runs. Do not invent historical event times.
- Soup coverage: doctor, pre-flight, and ship have not been tested in this review.
- Report takeaway: model/dataset rationale and proposed stack are documented; runtime results and failure-detection claims remain unverified.
- Reflection: pending actual experiments and the applicant's own observations.
- AI and human review: the assistant organized the working records and added this inventory. Independent applicant review of this entry has not been recorded.

### E002 - Colab environment, implementation, and local controls

- Recorded at: 2026-11-10T13:22:45+00:00.
- Kind and status: implementation and local synthetic verification; observed. Official training is not run.
- Decision change: Colab T4 replaces Brev as primary; merge will use GPU FP32 in a fresh process with sharded saving. Brev remains stopped and is only a documented fallback.
- What was checked: 22 strict-scorer tests and three real-library tests passed locally. The latter use a tiny random Qwen3 on CPU to exercise response masking, a zero-LR optimizer control, effective LoRA updates, merge/save/reload parity, and packed NF4 save/reload/forward. These do not measure Qwen3-1.7B task quality.
- Analytical result: official configuration gives 1,720,574,976 unique parameters, 1,605,632 LoRA parameters, and 196 expected quantized Linear modules. The code's pre-training estimates are 6,364,841,984 training bytes, 9,251,033,088 merge bytes, and 7,109,136,384 quantization bytes. They are estimates, not measured VRAM. The official run will preserve its own timestamped estimate.
- Access: the selected xLAM file returned HTTP 401 without a configured credential. A private local access helper was provided. The applicant reported running it; the subsequent local check still found no credential file. Asked to complete/check Stage 2; cause unresolved. No token was requested in chat.
- Evidence commands: `.venv/bin/python -m pytest tests/test_core.py -q`; `.venv/bin/python -m pytest tests/test_models.py -q`; `scripts/check_access.py`. Raw local outputs will be saved under `evidence/local-checks/`.
- Report takeaway: parameter/file existence is insufficient; the same library path can demonstrate a real optimizer step with zero update and then reject that no-op.
- Limits: no xLAM task score, measured T4 memory, or automatic-execution readiness is established yet.
- AI and human review: implementation and synthetic verification were performed by the assistant. Applicant reference audit and independent result review are pending.

### E003 - Reference audit and local diagnostic controls

- Recorded at: 2026-11-10T13:52:00+00:00; observations occurred during implementation before training. No model predictions were used to select exclusions.
- Kind and status: real data issues, implementation failures, and deliberate controls; resolved for the declared narrow scope, broader reference validity remains unproven.
- Access: an authorized source file was successfully downloaded and its SHA256 matched `config.json`. A later private-helper attempt saved a rejected value (HTTP 401). The existing authorized local file removes the need to send a credential to Colab. Credentials are excluded from source/notebooks/evidence.
- Audit finding: examples could assume an unstated year, movie ID, vehicle make ID, sport ID, or DNS result. The literal/default filter excludes such cases, but also excludes legitimate derivations and conversions. Its 1,271 exclusions are not a source-error count. Manual source exclusions: 49228 (random card vs default A), 59067 (conditional response handling), 23457 (validity depends on an unavailable README).
- Final local preparation: `XLAM_LOCAL_FILE=artifacts/source/xlam_function_calling_60k.json .venv/bin/python experiment.py prepare --run-dir runs/local-audit-final-20261110T1345Z`. Selected 1,000/64/128 rows across 747 naming-based API families with no cross-split family overlap; maximum 821 tokens. The scan examined 40,743 of 60,000 source rows before quotas filled. Restricted schema support and filters do not imply the remaining source rows are wrong.
- The assistant reviewed the final 40 references, including the three replacements. Targets match the supplied extraction task at this level. Some synthetic identifiers may be invalid at real endpoints; no endpoint was executed. Full-label review and independent applicant review remain pending.
- Scoring correction: optional documented defaults are equivalent in the primary metric; raw strict exact remains available. Schema-default strings may be converted to their declared metadata type; generated arguments are never coerced. Missing required flags use a no-default-means-required assumption.
- What broke: an initial numeric boundary rejected a currency value followed by punctuation. Fixed the boundary and added a regression check. Pytest initially discovered frozen source copies under runs; limited collection with `pytest.ini`. Original failed outputs are retained in `evidence/local-checks/`.
- Local result: `.venv/bin/python -m pytest -q` passed 32 tests at approximately 13:50 UTC (3.56 seconds). These are implementation controls, not trained model quality.
- Soup coverage: local `data doctor` returned MINOR/exit 0 for a valid synthetic chat fixture and MAJOR/exit 2 for the deliberate 32-token truncation control. Its generation-marker heuristic warned even where independent prefix/EOT checks passed. In the truncated fixture, the EOS check reported no assistant turns to check: a nominal sub-check pass must be read with its coverage. See `evidence/local-checks/soup-doctor-{normal,truncation}.*`. Live training pre-flight and ship coverage remain pending.
- Report takeaway: apparently valid schemas and JSON do not guarantee grounded labels; diagnostic success is meaningful only with inspection of what was checked. Record scope limits rather than claim automated filtering establishes truth.
- AI and human review: audit, fixes, and checks performed by Codex; no independent human audit is claimed.

### E004 - Free Colab allocation retry

- Recorded at: 2026-11-10T13:52:00+00:00.
- Kind and status: real infrastructure failure followed by successful retry.
- First request: free Colab T4 allocation reported "No backend with GPU available" and offered CPU. Declined CPU; retained the actual alert in `evidence/colab-allocation/attempt-1.json`.
- Retry: the notebook now reports a connected Google Compute Engine GPU backend. Hardware identity and usable memory still require `nvidia-smi` and torch checks before official training. No second GPU-unavailable error was observed; no claim of two failures is made.
- Brev status: `brev ls` confirmed `soup-internship-t4` STOPPED. It was not started for this attempt.
- Report takeaway: a transient allocation failure did not require switching hardware; preserve the failed request and report measurements only from the actual runtime.

### E005 - Browser control failure and declared Brev fallback

- Recorded at: 2026-11-10T13:56:11.029817+00:00.
- Kind and status: real infrastructure/control failure; fallback preparation in progress.
- After the successful GPU connection, updating the first cell and clicking Run both returned Orca `runtime_timeout`; a subsequent snapshot timed out after 35 seconds, and switching/reloading also failed to restore inspection. Setup execution is unverified, so no Colab measurements are used. See `evidence/colab-allocation/browser-control-failure.json`.
- The authorized Brev T4 fallback was started. `config.brev.json` explicitly declares the provider and reason before run initialization. CPU/RAM differences will be disclosed; no claim of strict Colab reproduction will be made.
- The notebook source builder now wraps the embedded base64 into short lines to reduce editor stress. This is a plausible UI workaround, not a proven diagnosis or a verified Colab recovery.
- Report takeaway: an allocated GPU is insufficient if the run cannot be operated or its outputs retrieved reliably. Preserve failures and separate provider measurements.

- Pre-run correction at 2026-11-10T13:57:01.366450+00:00: inspection of installed Soup 0.77.2 `gate_suites.py` explicitly recommends 256 tokens for behavioral suites after documenting truncation defects at 64. The general-suite budget is now separately frozen at 256 (task budget remains 128), and scorer revision/fingerprint are saved. This is an implementation/protocol correction before any main model predictions.

### E006 - Clean GPU VM exposes a missing compiler

- Recorded at: 2026-11-10T14:00:19.249959+00:00.
- Environment: Brev Tesla T4, driver 595.91.07, 15,360 MiB reported by nvidia-smi, approximately 25 GiB host RAM. New Python 3.11.18 / torch 2.6.0+cu124 environment with the pinned requirements.
- Actual failure: 30 tests passed and two real-library tests failed while importing bitsandbytes/Triton: `Failed to find C compiler. Please specify via CC environment variable.` The CPU-only laptop environment did not exercise the installed CUDA Triton driver path.
- Attempt: installing Ubuntu build-essential and rerunning the same tests before preparing the official run. Original output is retained as remote `evidence/cloud-setup/setup.raw.log`; repair has a separate `compiler-fix.raw.log`. Outcome pending.
- Lesson: dependency installation and laptop tests do not establish GPU-environment compatibility. This is an explicit setup failure, not evidence of a silent model failure.

- Repair result at 2026-11-10T14:00:58.282746+00:00: GCC 11.4 installed; all 32 tests passed on Brev in 6.19 seconds. torch reports 2.6.0+cu124 / CUDA 12.4 / Tesla T4. No model training was required to identify or fix this environment issue.
