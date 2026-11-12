# Task requirements and submission coverage

This is a post-run audit against `Soup-Task-01-AI-Engineer.pdf`. It distinguishes completed work, a hardware deviation and evidence that remains unknown. It does not replace the two-page report or claim the model is ready for deployment.

| Requirement | Status | Evidence / qualification |
| --- | --- | --- |
| Open model up to 3B parameters | Covered | Qwen3-1.7B; 1,720,574,976 unique parameters. Model choice and alternatives are in DECISIONS.md. |
| Open instruction data, 1-2k examples, evaluable language | Covered | English xLAM subset: 1,000 train + 64 validation + 128 test = 1,192 selected examples. Source license, access, filtering and limitations are documented. |
| Justify model, dataset and alternative stack | Covered | Report's Experiment and choice section; DECISIONS.md gives reasons, alternatives and evidence limits. Transformers/PEFT provides an inspectable training loop; actual Soup diagnostics are evaluated separately. |
| LoRA, adapter merge, 4-bit export | Covered | 125 optimizer updates; saved FP32 merged model; saved/reloaded packed NF4 model with 196 expected linear modules. |
| VRAM estimate before training, with all requested components | Covered | Estimate frozen at 14:01:58 UTC before training. Weight, activation, logit, adapter, optimizer and export allowances are retained. The report shows explicit sums and measured peaks; MEMORY_ANALYSIS.md explains gaps and measurement limits. |
| Prove training beyond falling loss | Covered on tested inputs | Effective adapter updates, enabled/disabled logit differences, a real zero-LR optimizer control, fresh-adapter control and held-out scores. Verification outputs and limitations are retained. |
| Compare base, merged and 4-bit artifacts | Covered | Fresh artifact reloads, same task cases, response loss, exact/JSON scores, behavioral probes, general suites, merge parity and actual quantized tensor checks. |
| Silent failures across data, tokenizer/template, training, merge, quantization and inference | Covered with scoped Soup evidence | SILENT_FAILURES.md and raw controls distinguish semantic label errors, truncation, mask/EOT issues, tokenizer drift, no-op training, omitted merge, false quantization and unsupported calls. Some Soup training-preflight and post-save failure branches were not separately fault-tested; those detection claims remain unknown. |
| One verdict, with precise changes required | Covered | DON'T SHIP for automatic execution: task accuracy below the committed gate, all trained-model abstention probes fail, mini-safety regresses, and representative execution/permission validation is absent. Proposed repairs are not represented as tested fixes. |
| Report at most two pages | Covered | output/submission/final/report.pdf; rendered and visually checked. |
| Raw timestamped logs and raw nvidia-smi | Covered | Supporting ZIP includes timestamped phase logs and raw per-phase GPU telemetry. |
| Verification script and finished notebook or code | Covered via code | Original measured code and reviewed code/verifier are included with source manifests. The notebook is an unexecuted reproduction artifact; no finished Colab notebook execution is claimed. |
| One paragraph on surprise and remaining concerns | Prepared | submission/REFLECTION.md in the ZIP; AI-assisted and explicitly labeled. It is not represented as independently written applicant reflection. |
| Failures: what happened, attempts, lessons; preserve bad results | Covered | EXPERIMENT_LOG.md, original failed outputs, original verifier/report, separately named corrected replay and source history. Publication credential redactions are recorded with original/package hashes; original measured inputs are retained privately. |
| Disclose AI use and corrected suggestions | Covered | AI_USE.md and the report disclose research, implementation, audit, execution and drafting assistance, accepted suggestions and corrections. Independent applicant review is not claimed. |
| Free Colab T4 | Deviation | Actual measurements used the declared Brev Tesla T4 fallback after Colab allocation/browser failures. GPU class matches; provider and host RAM differ. This is not literal completion of the requested free-Colab environment, and strict Colab host fit is unverified. |
| Submit by email reply within 48 hours | Pending | Report, ZIP and email draft are prepared; no email has been sent. The received-email timestamp/deadline has not been independently verified. Reply in the original task thread. |
| 40-minute live discussion | Pending | This is an applicant activity after submission. It accounts for 35% of the score. No interview answer script was prewritten. |

## Which explanations the task explicitly asks for

- Why this model and dataset, and why another stack if Soup is not used for training.
- Why a falling loss is insufficient and how the verification distinguishes an ineffective adapter.
- Why memory estimates differ from measured peaks.
- What each silent-failure check covers, whether the observed Soup command catches it, and what evidence supports that claim.
- Why SHIP or DON'T SHIP follows, and what must change before reconsideration.
- What broke, what was tried, what was learned, and which AI suggestions were accepted, checked or corrected.

The main reasons fit in the report. Detailed selection tradeoffs are in DECISIONS.md; dated observations and changes are in EXPERIMENT_LOG.md. Hyperparameters are fixed baseline choices, not the result of an optimization study. Completing the experiment and producing an honest negative verdict satisfies the requested decision exercise; it does not establish deployment readiness or guarantee evaluator acceptance of the hardware deviation.
