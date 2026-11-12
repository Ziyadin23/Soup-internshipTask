# Soup AI Engineer submission

This repository provides access to the existing report and supporting code/evidence archive submitted by Ziyadinkhan Kudaibergenuly. The report and ZIP are unchanged, and the ZIP is also extracted below for browser review. No new experiments or model runs were performed for this publication.

| Material | Link |
| --- | --- |
| Final two-page report | [report.pdf](report.pdf) |
| Original supporting archive | [supporting_files.zip](supporting_files.zip) |
| Extracted bundle and detailed review notes | [supporting_files/](supporting_files/README.md) |
| Latest reviewed source and verification script | [reviewed_code/](supporting_files/reviewed_code/) |
| Original source used for the measured run | [code/](supporting_files/code/) |
| Recorded results, including original and corrected verification | [results/](supporting_files/results/) |
| Raw logs, GPU telemetry, predictions, and failure controls | [evidence/](supporting_files/evidence/) |
| Reproduction notebook | [Soup_Submission.ipynb](supporting_files/Soup_Submission.ipynb) |
| Decisions, experiment log, analyses, and AI-use disclosure | [docs/](supporting_files/docs/) |
| Per-file hashes from the submitted bundle | [FILE_MANIFEST.json](supporting_files/FILE_MANIFEST.json) |

The measured source and reviewed source are retained separately. [SOURCE_VERSIONS.md](supporting_files/docs/SOURCE_VERSIONS.md) explains the corrected verification gate and later diagnostic/documentation changes. Historical submission notes are preserved as they appeared in the archive.

Large base/merged/4-bit model weights, full probe arrays, and optimizer checkpoints were already excluded from the submitted ZIP; their recorded manifests remain in the extracted bundle. The existing publication redactions in two training-data files are unchanged and documented in [DATA_REDACTIONS.json](supporting_files/DATA_REDACTIONS.json). Consult the [bundle README](supporting_files/README.md) for reproduction requirements and limitations.

The original report and archive hashes are listed in [SHA256SUMS](SHA256SUMS). Run `sha256sum -c SHA256SUMS` after downloading both files to check them. The extracted files retain the original paths and bytes from the ZIP.

Model and dataset attributions are preserved in the [original project README](supporting_files/docs/README.md#attribution), [decision record](supporting_files/docs/DECISIONS.md), and [licenses/](supporting_files/licenses/).
