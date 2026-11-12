# Post-run backup operations

These files document byte transport and cloud cleanup after scientific work finished. They are not training/evaluation source. Helpers were executed from the project tmp/ directory against the dedicated Brev instance; copied helpers here are inspection records. Interrupted attempts and original logs are retained.

The pinned base was reused only as an rsync candidate; actual trained bytes were retrieved from the original cloud files. Final NF4 ranges were reassembled from preserved prefixes and original remote byte ranges. Every complete artifact was checked against the original artifact_manifest.json. backup_verification.json at the run root records all 70 matches and the confirmed STOPPED state. The local verifier replay is recorded separately in evidence/local-backup-verifier.raw.log and results/. No fresh inference was claimed for that replay.
