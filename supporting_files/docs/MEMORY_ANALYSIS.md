# Memory analysis

All estimates were saved before training at 2026-11-10T14:01:58.445+00:00. Results are from the declared Brev Tesla T4 fallback, not a completed Colab run. Values below are GiB (2^30 bytes).

| Phase | Estimate | Allocated peak | Reserved peak | Sampled device-used peak | Process RSS highwater |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 5.928 | 4.966 | 6.055 | 6.194 | 3.971 |
| merge | 8.616 | 8.447 | 8.762 | 8.890 | 3.879 |
| quantize | 6.621 | 1.739 | 2.262 | 2.380 | 2.455 |

The resident graph has P=1,720,574,976 unique parameters and A=1,605,632 trainable LoRA parameters. Frozen FP16 weights cost 2P bytes. FP32 adapter weights, gradients and two Adam moments cost 16A bytes. The pre-training arithmetic separately budgets checkpoint boundaries, a one-layer activation allowance, logits/loss/backward as B*S*V*(2+4+4), and a 1 GiB context/workspace/allocator allowance. All components and assumptions are preserved in `evidence/memory_estimate_before_training.json`.

Training uses a maximum budget of 1,024 tokens, while actual selected sequences are shorter (maximum 821). Variable-length microbatches are unpadded. This and conservative working allowances reduce allocated peaks. Conversely, reserved memory retains allocator blocks, and device-used telemetry includes CUDA/context and other memory beyond PyTorch's allocated-tensor counter. The estimate includes a mixed context/workspace allowance, so subtracting it from allocated memory is not exact component accounting.

The FP32 merge estimate is 4P plus one largest-tensor overlap, per-target merge work and the allowance. Sharded saving limits CPU staging. Its observed allocated peak is close to this estimate; reserved and device-used peaks answer different questions.

The quantization estimate deliberately allowed simultaneous full FP16 source weights, packed destination weights, largest-tensor work and the allowance. The observed allocated peak is below even the full FP16 source footprint. Together with the low-memory sharded loader/conversion path, this supports a streaming-conversion explanation: the conservative full-source-plus-destination assumption was not realized. Tensor lifetimes were not individually traced, so this is an inference rather than a per-allocation proof. Embeddings/norms remain unquantized; '4-bit' does not mean every tensor occupies four bits.

The pinned source checkpoint stores both embedding and output-head tensors despite tying. A CPU check compared all 311,164,928 elements and found them bitwise identical. Its serialized weight bytes (4,063,479,808) exceed resident FP16 unique weights (3,441,149,952) by exactly the redundant tensor's 622,329,856 bytes. Counting checkpoint size as resident weights would overestimate this graph. See `evidence/local-checks/base-tied-weights-check.json` in the working project.

RSS measures the process, including imports and file-backed pages; it is not the entire machine's RAM. Brev's larger host RAM and absence of a completed Colab reproduction remain explicit limitations. Raw one-second GPU samples can miss short spikes; PyTorch peaks exclude allocations outside its allocator. Background artifact copying/compression may affect wall time; the recorded throughput is for this run, not an isolated hardware benchmark.
