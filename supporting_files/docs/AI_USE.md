# AI assistance and review record

Codex assisted with source research, comparison of candidate models/datasets, experiment design, implementation, dependency setup, data selection, tests, GPU execution, evidence review, and report drafting. The applicant selected the first-ranked Qwen3-1.7B/xLAM pairing and authorized the available compute budget. The implementation and reference audit should not be represented as independently written or reviewed by the applicant.

Accepted suggestions include a small LoRA adapter, explicit response/EOT supervision, separate held-out API families, fixed release criteria, fresh artifact reloads, effective BA/logit checks, zero-update controls, and per-phase memory instrumentation. The direct Transformers/PEFT loop was chosen for inspection of masks, gradients and updates; Soup's diagnostic commands are evaluated separately.

Suggestions changed or corrected during the work:

- The early Qwen2.5/Dolly proposal was replaced after a broader source comparison and the applicant's choice. Generic answer-string matching was replaced by a task-specific call contract.
- A pre-training reference audit found unsupported assumptions and ambiguous API behavior. The supported scope was narrowed to literal extraction/defaults, and three source exclusions were recorded before predictions. This does not certify all labels or real endpoint behavior.
- The primary metric treats documented optional defaults as equivalent, while preserving raw strict exact and generated-value type checks. This change occurred before the measured run.
- Soup's installed source recommends a 256-token behavioral-suite budget. That budget was separated from the task's 128-token limit before evaluation.
- A numeric-boundary bug and accidental duplicate pytest collection were fixed with regression evidence; original failures remain available.
- Laptop controls did not establish GPU compatibility. Clean-VM tests exposed a missing compiler, which was installed before the same 32 tests passed on Brev.
- Review found a floating-point edge in the custom release gate. An exact five-point drop could be misclassified as exceeding five points; a failing test and corrected 33-test run are retained. Soup already handles that boundary correctly. The original measured-source verifier and a separate corrected replay are preserved; no policy threshold or prediction was changed.
- Colab was selected first. An initial allocation denial and later browser-operation timeouts were preserved, then the authorized Brev T4 fallback was explicitly declared. No completed Colab reproduction is claimed.
- The post-save tokenizer warning was investigated before applying its suggested repair. Full backend and prompt checks supported leaving the Qwen tokenizer unchanged; the in-memory repair control changed 48 prompt sequences. The added diagnostic is distinguished from the original verifier's narrower tokenizer fingerprint.
- Final archive review expanded the credential scan beyond Hugging Face tokens and found a GitHub credential-like default in two public-data tool schemas. Publication copies are redacted and record both hashes; original measured inputs are preserved. The value was never used for authentication. This late finding exposes a preparation gap, not a repaired training run.

Checks performed by the assistant include source/version inspection, review of 40 reference examples, scorer and masking tests, real-library tiny-model controls, and review of measured run evidence. The report must distinguish measured results from synthetic controls and analytical estimates. Full-model behavior and release conclusions are recorded in the run's verification output, with finite-probe and deployment limitations.

Independent applicant review of the code, selected references and final results has not been recorded. The applicant should review the submission and ensure its explanations reflect their understanding. No interview answers have been prewritten, and no email has been sent by the project.
