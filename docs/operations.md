# Operations and evaluation status

## Verified in this workspace

- Python 3.12.3, four CPU cores, about 15 GiB system RAM, and no visible NVIDIA GPU.
- The repository contains no InfiniteTalk source archive, model cache, checkpoint, or existing application code.
- No model weights or expensive cloud resources were downloaded or started.
- InfiniteTalk upstream instructions specify Python 3.10 and PyTorch 2.4.1/CUDA 12.1; the service requirements are intentionally separate from that uninstalled model stack.
- No inference-time, VRAM, quality, cost, Arabic/Emirati, or training benchmark was run. Video generation is **not tested on GPU**.

## Resource and cost policy

Do not guess VRAM, storage, output cost, or accepted-video cost. Obtain exact weight sizes/checksums from the selected artifact host, measure a small authorized inference on the selected GPU, and include failed attempts in cost-per-accepted-output estimates. The Wan upstream README reports a 1.3B text-to-video example; that is not an InfiniteTalk benchmark and does not establish this pipeline's needs.

No model downloads or paid compute are part of setup. Before downloading, record file size, revision, license, checksum if supplied, destination/cache, and required user authorization. Keep model weights out of Git.

## Evaluation plan (not yet run)

Use a consented, versioned evaluation set with separate train/dev/test partitions. Include Modern Standard Arabic and Emirati Arabic recordings, diacritics/shadda, brand names, varied speaking rates, product photos and multiple scene prompts. Record transcript/audio provenance and consent. Do not claim Arabic support based solely on a Whisper/Wav2Vec2 component.

For the same input and seed where supported, compare the base adapter and any tuned variant. Record lip/audio sync, face and product identity, instruction following, motion artifacts, resolution/duration, latency, peak VRAM, failed attempts and cost per accepted result. Combine suitable automatic metrics with blinded human ratings; report uncertainty and failure cases. No comparisons with Veo/Kling or other closed systems are currently claimed.

| Integration / experiment | Status | Evidence |
|---|---|---|
| FastAPI upload/job skeleton | Programmed | Unit/API tests in `tests/`; CPU only |
| InfiniteTalk adapter | Planned | No upstream code or weights integrated |
| Arabic/emirati evaluation | Planned | No recordings or metrics |
| LoRA/fine-tuning | Planned | No verified training path, dataset, run, or budget |
| Production service / billing | Planned | No production isolation, durable queue, billing, or operational audit |
