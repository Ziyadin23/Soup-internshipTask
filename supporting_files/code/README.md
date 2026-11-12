# Soup AI Engineer experiment

Qwen3-1.7B + a curated xLAM function-calling subset. The official runtime is **free Google Colab T4**.
The original assignment is [here](Soup-Task-01-AI-Engineer.pdf).

**Current state:** implementation and local verification are in progress. No Colab training, memory peak,
task improvement, merge fidelity, or quantization quality is claimed until a real run produces its evidence.

**Recorded fallback:** Colab allocated a GPU after an initial denial, but browser operations repeatedly
timed out before setup could be verified. The measured run is being prepared on a Brev T4 using
`config.brev.json`. Its host RAM differs from Colab; this deviation and measured RSS will be reported.

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
bash scripts/access_wizard.sh
.venv/bin/python experiment.py prepare --run-dir runs/local-audit
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
- `runs/<id>/evidence/`: immutable timestamped commands, raw output, predictions, measurements, and controls.
- `runs/<id>/artifacts/`: base, initial/zero-LR/final adapters, merged and saved NF4 models, and checkpoints.
- `runs/<id>/submission/`: two-page report, scoped supporting archive, reflection and email drafts.

The email archive includes the adapter, code, data selections, results, and logs. Large full weights and full
logit arrays are retained separately; their hashes and reproduction source are included. Download every model
shard, shard index, config, and tokenizer file before releasing Colab. The archive excludes `.env`, credentials,
virtual environments, caches, optimizer snapshots, and multi-gigabyte full models.

Reply to the original task email at **team@trysoup.dev**, attaching the report and supporting files.
The project never sends email. Review the PDF visually and replace the reflection draft with your own response
after reviewing the evidence. AI assistance and actual human review must be described accurately.

## Attribution

- Qwen Team: [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B), Apache 2.0;
  pinned revision is recorded in `config.json`.
- Liu et al., *APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets*
  (2024): [dataset](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k), declared CC BY 4.0;
  [paper](https://arxiv.org/abs/2406.18518), [license](https://creativecommons.org/licenses/by/4.0/).
  The selected, filtered subset is an adaptation; exclusions/source IDs and original revision are recorded.
- Soup CLI: [source](https://github.com/MakazhanAlpamys/Soup), Apache 2.0. Its diagnostic outputs and scorer
  version are recorded, with live and offline gate behavior distinguished.
