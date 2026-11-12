# Soup AI Engineer experiment

Qwen3-1.7B + a curated xLAM function-calling subset. The reproduction target is **free Google Colab T4**, as specified in the assignment; measured results use the declared Brev T4 fallback.
The original assignment is [here](Soup-Task-01-AI-Engineer.pdf).

**Measured result: DON'T SHIP for automatic execution.** The Brev T4 run completed training, FP32 merge,
NF4 export, all three evaluations, Soup controls and verification. Exact call accuracy was 14.84% base,
95.31% merged and 95.31% 4-bit. The trained and 4-bit models each failed 48/48 abstention probes;
the 4-bit mini-safety score fell from 60% to 42.5%. All artifact-integrity checks passed.

The reviewed report is `output/submission/final/report.pdf`; the email archive is
`output/submission/final/supporting_files.zip`. Raw evidence and model manifests are in
`runs/brev-20261110-main-01/`. All 70 manifested model files (12,410,656,746 bytes) match their original
cloud hashes. A local recorded replay passed all 11 integrity checks and exactly matches the corrected
cloud results. Brev was confirmed **STOPPED at 2026-11-10T17:04:14.491169+00:00**.
The retained VM disk can still incur storage charges; the final invoice was not verified.

A post-run archive scan found a GitHub credential-like default in unused tool definitions from two public
xLAM training rows (17135 and 43443). Its validity is unknown and it was never used for authentication.
The submission copies of `data/train.json` and `data/train_chat.jsonl` are redacted; `DATA_REDACTIONS.json`
records original and packaged hashes. The original measured run is unchanged. Restore those two private
original files before frozen-input replay, along with the separately retained full weights and probe arrays.
A future release run must sanitize tool schemas before training; publication redaction does not repair the model.

**Hardware deviation:** Colab initially denied GPU allocation, later connected, then notebook operations
repeatedly timed out. All measured model results use the declared **Brev Tesla T4 fallback** with different
host RAM. No completed Colab reproduction is claimed. `Soup_Submission.ipynb` is an unexecuted,
self-contained reproduction notebook, with an explicitly labeled archived-results summary.

## Run on Colab

1. Open [Google Colab](https://colab.research.google.com/) and upload `Soup_Submission.ipynb`.
2. Select **Runtime > Change runtime type > T4 GPU**. The notebook checks the actual GPU.
3. Run cells in order. Install pinned libraries without replacing Colab's CUDA torch with a CPU wheel.
4. Accept the [xLAM access conditions](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)
   in your Hugging Face account. Enter an authorized read token only in the private notebook prompt,
   or upload the already authorized `xlam_function_calling_60k.json` to `/content/`. Its pinned SHA256
   is checked in either case; the public model is downloaded without forwarding that credential.
5. Review the reference-audit sample and record who reviewed it and the findings. Do not auto-approve it.
6. Run the measured stages. Download evidence and full artifact files before the runtime is deleted.

The notebook embeds source built by `scripts/build_notebook.py`, not an external mutable repository.
It contains no token and has no execution outputs until it is run. Rebuild it after source changes.

## Local preparation and tests

Python 3.11-3.13 is appropriate. Keep CPU and Colab environments separate.

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest -q
# With the already authorized, downloaded source:
XLAM_LOCAL_FILE=artifacts/source/xlam_function_calling_60k.json .venv/bin/python experiment.py prepare --run-dir runs/local-audit
# For a fresh source download, first run: bash scripts/access_wizard.sh
```

The access wizard saves a token only to ignored `.env` with private permissions. Never submit it.
Prepared data/reference review and the analytical memory budget can be inspected without a GPU.
The full pipeline deliberately refuses CPU or non-T4 execution as an official result.

```bash
python experiment.py approve-audit --run-dir runs/colab-RUN_ID --reviewer 'Actual reviewer' --notes 'Actual findings'
python experiment.py run --run-dir runs/colab-RUN_ID
python verify.py --run-dir runs/colab-RUN_ID
python verify.py --run-dir runs/colab-RUN_ID --recorded
```

`verify.py` without `--recorded` reloads artifacts and regenerates probes/predictions on the T4.
`--recorded` checks hashes and replays evidence; it is not fresh inference. Exit 2 means an artifact-integrity
check failed; DON'T SHIP is a measured release decision and does not by itself indicate a program crash.

The post-export regex warning also prompted an additional check:
`python -m scripts.check_tokenizers --run-dir <run>`. It compares complete tokenizer backends and all
1,240 selected/probe prompt token sequences, then demonstrates the effect of an in-memory Mistral-specific
patch on this Qwen tokenizer. It never saves that patched tokenizer. This diagnostic was added after the
original source freeze. The reviewed source runs it automatically before verification/reporting; the measured
run executed it separately. Both source histories and the original/corrected gate outputs are preserved.

Each run freezes code, configuration, source revisions, selected data, and the release policy before training.
Do not overwrite failed runs. A fresh run ID is required after a failed stage or code/protocol change.
Adapter/optimizer checkpoints preserve partial work, but automatic cross-run optimizer resume is not implemented.

For the declared Brev fallback, use Python 3.11, `torch==2.6.0` from the CUDA 12.4 wheel index,
then `requirements.txt`. A clean Ubuntu VM also needs `sudo apt-get install build-essential` for
Triton. Set `XLAM_LOCAL_FILE` to the authorized source JSON, prepare with `--config config.brev.json`,
review the references, then run the same pipeline. Save `pip freeze` and raw hardware output; the pipeline does this.

## What is measured

- Actual gradients and optimizer steps; initial/final effective LoRA BA updates; zero-LR and fresh-adapter controls.
- Enabled/disabled repeat-noise comparison, and active adapter vs reloaded FP32 merged logits.
- Saved/reloaded packed NF4 module count, quantization state, artifact sizes, and exact weight hashes.
- Teacher-forced response+EOT loss, strict typed function/argument correctness, JSON/schema validity, and stopping.
- Family-bootstrap paired intervals; 48 templated abstention probes; Soup's bundled general suites.
- Per-phase PyTorch allocated/reserved peaks, raw `nvidia-smi`, sampled RSS and process highwater.

Scoring does not extract a convenient JSON substring from prose, coerce strings into objects, equate booleans
with numbers, or accept a valid call to the wrong function. Broad general prompts use their own user chat
template, not the task's tool-only system instruction. Runtime failures must not silently become benchmark zeros.
The primary exact-call metric permits omission/inclusion of schema-documented optional defaults; raw
`strict_exact` is retained separately. Only default metadata is converted to its declared type. Generated
arguments are never coerced. Source schemas without explicit required flags treat no-default fields as required.

## Release scope and limitations

The selected scope is automatic execution. This study predicts calls offline and calls **no real external APIs**.
Benchmark gates and artifact integrity are reported separately from deployment readiness. Without representative
execution/permission/sandbox validation, the release verdict is DON'T SHIP even if offline model checks pass.
The verdict lists concrete failed conditions; it is not an automatic claim that a trained model is useful.

Naming-based API families can miss aliases; public datasets can be in pretraining; exact references can reject
equivalent calls; generic list/object schemas may omit nested constraints. The 48 probes are correlated and narrow.
The subset deliberately restricts arguments to literal request values or documented defaults. This excludes
legitimate derivations and conversions as well as unsupported assumptions, so exclusion counts are not source-error rates.
Report these limits. Source-card research-purpose language and declared licenses are retained, not converted into
an unsupported claim of unrestricted commercial clearance.

## Evidence and submission

- [DECISIONS.md](DECISIONS.md): choices, alternatives, reasons, sources, and changes.
- [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md): observations, failures, fixes, lessons, and report takeaways.
- [MEMORY_ANALYSIS.md](MEMORY_ANALYSIS.md), [SILENT_FAILURES.md](SILENT_FAILURES.md),
  [ERROR_ANALYSIS.md](ERROR_ANALYSIS.md), [AI_USE.md](AI_USE.md): supporting interpretation and review status.
- `runs/<id>/evidence/`: immutable timestamped commands, raw output, predictions, measurements, and controls.
- `runs/<id>/artifacts/`: base, initial/zero-LR/final adapters, merged and saved NF4 models, and checkpoints.
- `runs/<id>/submission/`: original automatic report and draft materials, retained unchanged.
- `output/submission/final/`: reviewed two-page report, supporting archive, reflection and email draft.

The email archive includes the adapter, code, data selections, results, and logs. Large full weights and full
logit arrays are retained separately; their hashes and reproduction source are included. Download every model
shard, shard index, config, and tokenizer file before releasing Colab. The archive excludes `.env`, credentials,
virtual environments, caches, optimizer snapshots, and multi-gigabyte full models.

Reply to the original task email at **team@trysoup.dev**, attaching the report and supporting files.
The project never sends email. Review the PDF visually and replace the reflection draft with your own response
after reviewing the evidence. AI assistance and actual human review must be described accurately.

## Attribution

- Qwen Team: [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B), Apache 2.0;
  pinned revision is recorded in `config.json`; the copied license is in `licenses/Qwen3-Apache-2.0.txt`.
- Liu et al., *APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets*
  (2024): [dataset](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k), declared CC BY 4.0;
  [paper](https://arxiv.org/abs/2406.18518), [license](https://creativecommons.org/licenses/by/4.0/).
  The selected, filtered subset is an adaptation; exclusions/source IDs and original revision are recorded.
- Soup CLI: [source](https://github.com/MakazhanAlpamys/Soup), Apache 2.0. Its diagnostic outputs and scorer
  version are recorded, with live and offline gate behavior distinguished.
