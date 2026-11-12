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

### E007 - Official Brev run initialized

- Recorded at: 2026-11-10T14:03:12.428800+00:00.
- Run: `runs/brev-20261110-main-01`, configured with `config.brev.json`. Dataset preparation completed at 14:01:59 UTC, and the analytical estimate was saved at 14:01:58 UTC before training. The cloud audit SHA256 exactly matches the reviewed local audit: `5e8dd23dac8c734b01809dff0129f16ee870503ec3ca3a4c22aade02c4d2e55b`.
- Estimates: train 5.93 GiB, FP32 merge 8.62 GiB, quantization 6.62 GiB. These are preserved predictions; actual peaks remain pending.
- Reference approval identifies Codex as the AI-assisted reviewer, records scope/endpoint limitations, and leaves independent applicant review pending. The run preserves local checks, the Colab failure record, clean-VM compiler failure, and repair output.
- The measured pipeline is launched with a three-hour process limit, immutable per-stage results, timestamped logs, and raw GPU telemetry. Outcome pending; no claim of improvement is made.

### E008 - Semantic-label negative control and pre-flight coverage

- Recorded at: 2026-11-10T14:06:46.967746+00:00.
- Deliberate control: a request explicitly gives order ABC-123, while its syntactically valid reference calls lookup_order with INVENTED-999. Local Soup data doctor returns MINOR/exit 0, warning only about generation markers; no check detects the wrong order ID. Raw fixture and output: `evidence/local-checks/ungrounded-reference-control.jsonl`, `soup-doctor-ungrounded.{json,raw.log}`. This is evidence of missing semantic-label coverage in this command, not a claim that Soup promises label truth.
- Official Brev preflight: doctor, data doctor, profile, and config doctor all exited 0. Data doctor scanned all 1,000 rows and found no truncation, with MINOR missing-generation-markers warning. Its rendered lengths differ slightly from our compact response rendering, so it does not validate our exact mask.
- Doctor recommends newer Soup training dependencies; we intentionally use the independently tested Transformers/PEFT loop, not Soup training. Config doctor reports zero known-unread settings enabled; that narrow result is not a complete training validation. Profile is analytical and is not an observed peak.
- Report takeaway: passing commands must be interpreted by their checks and scope. Grounding, exact masks, effective updates, and export parity require independent evidence.

### E009 - Training, export, and numerical checks observed

- Recorded at: 2026-11-10T14:29:46.188702+00:00.
- Main training completed 125/125 updates on 1,000 examples. Main-loop time 355.10 seconds, 281,143 input tokens / 24,141 supervised tokens, approximately 791.7 input tokens/s including checkpoint IO but excluding validation, control and download. Validation response NLL fell from 0.42752 to 0.02641. This alone is not proof of task improvement.
- The real zero-LR control had gradient norm 2.93517 and changed zero adapter tensors. Fresh enabled/disabled FP32 probe RMS is 2.35226 vs repeat RMS 0. The reloaded merge max absolute logit error is 0.000084877, below the precommitted tolerance. These probes support adapter activity and merge fidelity on their finite inputs.
- Actual memory and differences are explained in `MEMORY_ANALYSIS.md`. Train estimate/allocated/reserved/sampled device peaks: 5.928/4.966/6.055/6.194 GiB; merge: 8.616/8.447/8.762/8.890; quantization: 6.621/1.739/2.262/2.380. Host process RSS highwaters were 3.971/3.879/2.455 GiB. Brev is the declared provider; Colab reproduction remains unverified.
- Checkpoint storage insight: all 311,164,928 embedding/head elements compare bitwise equal. Raw source serialization contains the tied tensor twice; resident unique parameters count it once. See `evidence/local-checks/base-tied-weights-check.json`.
- Captured base task outputs: 128 examples, 42 JSON-valid, 21 flat-schema-valid, 20 correct functions, 19 exact calls. Three inspected syntax failures contain apparently correct names/arguments inside malformed quoted-array output. Do not characterize future exact-score improvement as broad reasoning gains without further evidence.
- General-suite comparison and the final verifier are still running. No final SHIP decision or trained/4-bit task score is asserted in this entry.

### E010 - Post-save tokenizer warning investigated

- Recorded at: 2026-11-10T14:40:57.288780+00:00.
- Actual warning: reloading the locally saved Qwen tokenizer recommends `fix_mistral_regex=True`. Inspected Transformers 4.57.6 `tokenization_utils_base.py`: the non-Mistral exclusion is nested under a <=4.57.2 config-version branch, while locally saved 4.57.6 configs fall through to the warning. This supports a version-detection false-positive explanation for this Qwen model.
- Verification: all three loaded tokenizer backends have identical complete serialized backend fingerprints, and every one of 1,240 selected/probe prompt sequences has identical token IDs. Evidence: `evidence/tokenizer-reload-equivalence.json` in the measured run. No model-specific regex patch was applied to the actual artifacts.
- Additional diagnostic: `scripts/check_tokenizers.py` repeats this check and deliberately applies the suggested Mistral patch in memory as a drift control. This helper was added after the original source freeze; original model/evaluation source and results are preserved. Diagnostic outcome pending.
- Limitation identified: the original verifier fingerprints vocabulary/template/special tokens, but does not by itself fingerprint every backend component. The targeted full-backend/prompt check supplies additional evidence for this run. Universal tokenizer correctness remains unproven.

- Diagnostic result: the original three backend fingerprints match. Applying the suggested Mistral-specific patch only in memory changes the backend and 48/1,240 prompt sequences. The original verifier could miss a backend change with unchanged vocabulary/template; this extra diagnostic addresses that gap for the observed exports. See `evidence/tokenizer-regex-control.json`.
- Helper execution correction: one invocation ran before its upload completed and failed with `No module named scripts.check_tokenizers`. The source was transferred through SSH stdin, completion was checked, and module execution then succeeded. This did not alter model artifacts or scored predictions.

### E011 - Improved call formatting with a severe abstention regression

- Recorded at: 2026-11-10T14:46:08.952405+00:00.
- Observed intermediate result: merged artifact gets 122/128 exact calls (95.3125%) and 128/128 JSON-valid outputs, compared with base 19/128 exact and 42/128 JSON-valid. All 48 merged behavioral probes fail, versus 16/48 for base. Quantized comparison and full general results remain pending at this entry.
- Concrete failures: missing order ID produces lookup_order with empty arguments; a request to cancel a subscription is sent to lookup_order using the subscription ID; an override request produces a delete_account call that is not in the supplied tool list. Raw responses are retained in the measured run.
- Interpretation: training changed the model and improved its required JSON format, but did not establish reliable tool selection or abstention. Positive-only single-call training is a plausible contributor to compelled-call behavior; that mechanism was not isolated with an ablation.
- Exact-score limits: six task mismatches include case and domain-label variants. Some may be endpoint-equivalent; the offline study does not establish that. Held-out labels and scoring were not relaxed after seeing predictions. The probe failures are independent of those reference ambiguities.
- Required next experiment before release: add independently audited missing-information, unavailable-tool and conflicting-instruction training examples; use fresh held-out probes; enforce tool allowlists and required/domain arguments at runtime; verify deployment permission/sandbox boundaries. These are proposed changes, not claimed fixes.

### E012 - Numeric boundary correction in release-gate replay

- Recorded at: 2026-11-10T14:54:28.960145+00:00.
- Found during review, independently of the final 4-bit results: `0.8 - 0.75 > 0.05` is true in binary floating point. The intended policy allows exactly five percentage points of regression. A targeted test using otherwise healthy synthetic scores reproduced a false DON'T SHIP. Original failed output: `evidence/local-checks/float-boundary-failure.raw.log`.
- Correction: numeric excess checks ignore only rounding differences within 1e-12 absolute of the unchanged committed boundary; a genuine 5.1-point decline still fails the regression test. This changes no task labels, predictions, model artifacts or numeric policy thresholds.
- Versioning: the ongoing measured run retains its original frozen source/verifier. A corrected replay using the reviewed source will be kept separately and compared with the original. Do not overwrite the first verification result or represent the new source as the one used for training.
- Validation: full reviewed-source test result is saved in `evidence/local-checks/pytest-33-tests.timestamped.log`.

- Further inspection: Soup 0.77.2 already uses a regression epsilon in `utils/ship_verdict.py`; the boundary defect was in our custom gate. The measured merged mini-tool score is exactly five points below base (0.675 to 0.625), making the distinction material. The committed maximum remains five points; a corrected replay must not list that exact-boundary change as an exceedance.

### E013 - Reviewed report renderer

- Recorded at: 2026-11-10T15:03:55.555430+00:00.
- The reviewed renderer adds full failure conditions, explicit flat-schema limits, actual sampled-device peaks, the streaming-quantization estimate gap, throughput denominators, and the post-export tokenizer finding. Original measured source and original automatic report are retained; the reviewed report can select a separately versioned verification replay and output directory.
- A string-concatenation error in the renderer was caught by the synthetic layout test, saved in `evidence/local-checks/report-revision-concatenation-failure.raw.log`, and corrected. Both reporting tests then passed. A stress fixture with the fallback paragraph, timings and several failed conditions rendered as two pages; both page PNGs were visually inspected and are clearly marked synthetic, not submission results.
- No model measurement, prediction or frozen policy was edited for report layout. Actual final PDF must still be rendered and visually checked after results are complete.

### E014 - Completed measured comparison and corrected release decision

- Recorded at: 2026-11-10T16:03:55.304771+00:00.
- The original pipeline completed at 2026-11-10T15:30:49.027+00:00. All 11 artifact checks passed; training effect, task improvement on this contract and scoped export checks are established. The 4-bit/base exact improvement is +0.80469 with a paired 95% family-bootstrap interval [0.66972, 0.90517], using 63 naming-based test families and 2,000 resamples.
- Final 4-bit task NLL is 0.0337806 vs merged 0.0239748; exact accuracy is 122/128 for both. Quantization introduces two invalid/truncated task outputs and changes the identity of one wrong/right case. All 48 probes fail for both trained artifacts; base fails the 16 override variants only. Full results are in `ERROR_ANALYSIS.md` and raw prediction JSONL.
- General mini-safety: base 0.60, merged 0.55, 4-bit 0.425. General over-refusal outputs hit the 256-token cap in 37/40 cases for all artifacts, so its score is not completeness evidence.
- Soup results observed: live untrained control rejects `adapter_noop`; deliberately truncated training data gets MAJOR/exit 2; offline merged SHIP, offline 4-bit DON'T SHIP for mini_safety regression. Offline ship was supplied our task/general scores and not the custom probes, so its verdict is not independent model or deployment validation.
- The corrected verifier replay completed at 2026-11-10T15:31:31.797462+00:00 with exit 0 and DON'T SHIP. It removes the spurious exact-boundary mini_over_refusal flag while retaining four real blockers. Original results, source and automatic report are unchanged.
- A reviewed two-page report was rendered from the corrected replay. It explicitly scopes export checks and reports clipping/truncation limits. The exact final renderer and all source versions accompany the submission.
- Post-run hardening: future reproductions automatically run the frozen tokenizer diagnostic before verification/reporting, preserve its failure log, and stop if it fails. A new test uses a deliberately failing frozen helper to verify the stop; reviewed source now passes 34 tests. This integration was not the code used for the original measurements.

### E015 - Export backup transport

- Recorded at: 2026-11-10T16:03:55.304771+00:00.
- GPU work is complete; full-model backup is in progress. Public base files were downloaded locally from the exact pinned revision, avoiding the slow SSH relay. FP32 exports are losslessly compressed for transfer; NF4 exports are copied unchanged. Each restored artifact must match the original cloud manifest SHA256 before cleanup.
- A purpose-built Brev copy attempt for a secondary shard failed its three SSH availability probes (5-second timeouts). Persistent SSH/rsync transfers remained usable. Concurrency was reduced while collecting control/evidence, then increased for the final bulk copy; partial bytes and transport logs were retained. This affects backup wall time, not frozen model measurements.
- No backup completion or VM shutdown is claimed yet. A completion entry will record actual hash checks and cloud state.

### E016 - Backup transport diagnosis and final report review

- Recorded at: 2026-11-10T16:48:04.942501+00:00.
- The shared SSH multiplex session accepted a control connection but stalled while opening new channels. A fresh independent SSH connection retrieved the seven original tensor headers successfully. Subsequent transfers bypass that shared session. A header-dependent launch was initially attempted after a timed-out fetch; it was stopped, partial bytes were retained, and the dependency was checked before relaunch. No model result changed.
- Backup optimization: reconstruct only a candidate rsync basis from the pinned base tensors converted exactly to FP32, with original cloud shard headers. The embedding-only shard matches its original hash exactly as a control. Rsync must then fetch the trained differences from the original cloud files; candidate files are not accepted as backups until the complete original cloud SHA256 matches. This is byte transport, not a new merge or inference experiment.
- The final PDF explicitly states why loss alone is insufficient, the measured comparison, memory gaps, finite-check limits, observed Soup outcomes, failed release conditions and proposed next steps. Both current pages were rendered and visually inspected with no clipping. Both reporting tests passed after the final wording change. An optional pypdf-based inspection failed because that package was absent; Poppler successfully checked the page count and extracted content without adding a dependency.
- The final report metadata identifies its exact renderer and corrected cloud replay. Earlier reports and failures are preserved. Independent applicant review is still not claimed. Full backup verification and cloud shutdown remain pending.

### E017 - Verified backup and cloud cleanup

- Recorded at: 2026-11-10T17:06:13.782365+00:00.
- All 70 manifested model artifact files, totaling 12,410,656,746 bytes, match the original cloud SHA256s. Verification finished at 2026-11-10T17:03:11.177509+00:00. Public base files came from the pinned repository revision; merged files used a pinned-base rsync candidate with the actual trained differences fetched from cloud. Both restored NF4 files match their complete original hashes.
- The final NF4 transfers were limited by individual connections. Remaining original byte ranges were fetched in parallel after preserving the partial prefixes, then reassembled and checked against whole-file hashes. This changed only transport. Interrupted transport attempts, method changes, helper code and raw logs are retained under evidence/post-run-backup/. Candidate/basis files were never accepted as model results.
- The local recorded verifier replay exited 0 at 2026-11-10T17:03:36.651643+00:00. Its checks, verdict, failure reasons, numerical comparison and bootstrap results agree exactly with the corrected cloud replay. This is a copied-artifact/hash/recorded-evidence check, not another GPU inference run.
- Brev stop exited 0; the CLI subsequently confirmed STOPPED at 2026-11-10T17:04:14.491169+00:00. Raw stop/status output and its SHA256 are retained. The VM was not deleted, so retained storage may still be billed. The final invoice is unknown; no exact cost is claimed from the quoted hourly rate.
- Scientific outcome remains DON'T SHIP for automatic execution. No thresholds, labels, predictions or original measured source were changed to make the result favorable. Independent applicant review and a completed Colab reproduction remain unrecorded. No email was sent.

### E018 - Publication scan finds credential-like source defaults

- Recorded at: 2026-11-10T17:17:27.504349+00:00.
- The initial packager scanned for Hugging Face token literals and passed. A broader final scan covering GitHub formats failed on data/train.json. Inspection located the same credential-like default in the unused list_folder_contents tool schema in source rows 17135 and 43443; it also appears in train_chat.jsonl. The source-token fingerprint is recorded in evidence/post-run-archive-scan.json, without publishing its value. Validity is unknown and no authentication request was made.
- Correction: only publication copies of the two training files replace that value with a redaction marker. DATA_REDACTIONS.json records the original and packaged hashes and occurrence counts. Original measured inputs, labels, predictions, model artifacts and frozen hashes are unchanged; verify_frozen_inputs still passes on the full local run. Restore the original private training files before recorded replay from the email bundle.
- The original preview and first archive are preserved privately under tmp/submission_archive_history/, outside the final attachments. Their original HF-only credential-scan metadata is insufficient; it must not be interpreted as a broad credential-clearance result. The final packager scans the broader formats and accepts redaction only for the exact observed source fingerprint and two known files; unexpected matches fail.
- Lesson: the 40-row reference audit and valid structured data did not cover all unused tool defaults. Sanitization must happen before a new release training run. Publication redaction does not establish unlearning or repair this measured model. The final report and silent-failure notes disclose the late finding; Soup credential detection was not separately fault-tested.

### E019 - Rewrite the final report around the decision

- Recorded at: 2026-11-10T17:44:50.411292+00:00.
- User requested an editorial rewrite after review. The revised two-page report leads with the release decision, compares exact/JSON/loss/probe/mini-safety results together, explains the control outcomes in prose, and displays the actual merged and NF4 missing-order-ID outputs for probe-missing-00. It replaces fractional accuracy deltas with percentage points.
- Memory arithmetic is read from the frozen pre-training record and shown as explicit component sums for training, FP32 merge and NF4 export. Exact-byte sums are asserted against the original estimates, and retained in report metadata. No estimate was replaced with an observed peak.
- Operational detail was shortened while retaining the Brev deviation, data-redaction notice, finite-check limits and AI-use status. Both latest pages were rendered and visually inspected; no clipping or overlap was observed. Both reporting tests passed. The previous report, archive, metadata, validation and renderer are preserved under output/submission/final/revisions/07-before-editorial/.
- Prior PDF SHA256: 0b7462f360e1dd4b6b34bb0b8da671c77e39c767b7174cb85305447b2a7d5c52. Revised PDF SHA256: baac4d40293648b99db7af6c5de5a47cdb56e37ad740bbbd9dbc0dade3d75170. The same corrected cloud verification replay supports both. Training, inference, model artifacts, labels, predictions and release thresholds were not rerun or changed. Latest model data/runtime/stages and the reviewed verifier/core remain checked against their original manifests.

### E020 - Audit task coverage and decision explanations

- Recorded at: 2026-11-10T18:01:22.302407+00:00.
- Reread the original task and compared it with the report, packaged files, controls and rationale record. Added SUBMISSION_CHECKLIST.md with requirement-to-evidence mapping and explicit deviations/pending activities. This audit does not claim literal free-Colab compliance or comprehensive fault coverage for every Soup training-preflight branch.
- Found a documentation gap: model/data/stack choices were explained, while some numerical settings were mainly listed. Added a post-run tradeoff/limitation table to DECISIONS.md covering dataset/split sizes, grouping, resampling, LoRA targets/rank/scaling, learning rate/epoch, batching, sequence/generation budgets, dtypes, merge/export and release thresholds. These explanations are engineering judgments; no sweep, competing-model experiment or ablation was invented. The original setting values remain frozen.
- Material qualifications remain: actual Brev T4 fallback and different host RAM; some Soup detection claims unknown; independent applicant review unrecorded; notebook unexecuted as a reproduction artifact while finished code/logs are supplied; email and live discussion pending. The received-email deadline was not independently verified.
- Documentation and bundle refresh only. Report PDF, predictions, models, source training/evaluation stages and release policy are unchanged; no GPU session, inference or new quality experiment was started.
