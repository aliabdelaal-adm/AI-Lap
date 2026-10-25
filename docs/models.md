# Model and adapter inventory

`studio_ai_lab/models.json` is a source-linked initial shortlist, not a claim that the candidates are deployable. Unknown values are explicitly `null`, `not assessed`, or `unverified`; keep them that way until a primary source is checked. Research claims are not local test results. The request to review 30 candidates has **not** been completed.

## Current lead: InfiniteTalk

Primary sources checked on 2026-10-25:

- [Official code and README](https://github.com/MeiGen-AI/InfiniteTalk), commit [`50aa0a94184315407a991ae804d9b58d6d311ba8`](https://github.com/MeiGen-AI/InfiniteTalk/commit/50aa0a94184315407a991ae804d9b58d6d311ba8), commit date 2026-05-22.
- [Official LICENSE.txt](https://github.com/MeiGen-AI/InfiniteTalk/blob/main/LICENSE.txt) is Apache-2.0. The upstream README states the repository's models are under Apache-2.0; keep that separate from the base Wan model and audio encoder terms.
- [Official checkpoint page](https://huggingface.co/MeiGen-AI/InfiniteTalk); upstream README lists Wan2.1-I2V-14B-480P and TencentGameMate/chinese-wav2vec2-base as additional model components.
- [Technical report](https://arxiv.org/abs/2508.14033). The authors describe sparse-frame audio-driven video dubbing and image+audio-to-video. Those claims have not been reproduced in this project.

Upstream instructions show Python 3.10, PyTorch 2.4.1/torchvision 0.19.1/torchaudio 2.4.1 with CUDA 12.1, plus FlashAttention and FFmpeg. Its README does not provide a verified minimum VRAM, total checkpoint size/checksum, Arabic benchmark, or independent quality result. The repository notes long-clip color-shift/identity trade-offs. There is no GPU or model checkpoint in this workspace.

## Other candidates

Wan2.1, HunyuanVideo, LongCat-Video, Stable Video Infinity, and SkyReels-V2 are in the initial research backlog. Their per-version weights terms, hosted-service rights, resource envelope, Arabic performance, and operational fit must be reviewed before selection. HunyuanVideo's source repository contains a custom license and NOTICE; do not treat it as a permissive license. InfiniteTalk's upstream README points to LongCat avatar releases; compare the exact release and weights rather than transferring claims across versions.

No closed-service model (Veo, Kling, or Gemini/Nano Banana) is represented as an open weight or as a training source. Official API connectors, if added, must be separate, opt-in, and display price/terms.

## Required fields before integration

For each checkpoint/version, record exact source and immutable revision, model card/weights URL, verification date, source-code license, weights license, commercial use/redistribution/hosting terms, file sizes/checksums, storage/VRAM requirements, training code, language evidence, upstream-reported results, limitations, integration status, and our own hardware/test results. A missing field blocks commercial enablement; it is not evidence of permission.
