# Architecture and boundaries

```text
Browser (Arabic/English)
       │ HTTP authorization + multipart
FastAPI ─── per-user media directory (random filenames, private mode)
   │
   ├── SQLite job table (owner-scoped reads, quotas, lifecycle)
   └── VideoEngine protocol ── UnconfiguredEngine (current default)
                                  └── explicit failure; no fabricated output
```

- `studio_ai_lab/app.py` owns HTTP/API orchestration and status rendering.
- `media.py` streams uploads to generated paths and checks a small allow-list of file signatures. It does not fully decode images/audio; a real model adapter must validate and decode inputs before inference.
- `store.py` is a local, single-host job queue. It is not a durable distributed broker. Use a replaceable worker/broker and a transactional metadata store before multi-process or commercial deployment.
- `VideoEngine` is the integration seam. An adapter must inspect GPU/VRAM and checkpoint availability, report actual progress only when its backend supports it, record model/checkpoint versions and seed, honor task cancellation, and write a validated MP4 under the job output directory.
- The current engine deliberately fails with an explicit error. No fake demo output, model download, subprocess, or untrusted command execution is present.
- Access tokens are configured as a JSON mapping of user IDs to unique secrets. Each user can see only their own jobs and a per-user active-job quota is applied. This is token-based tenant scoping, not a complete account/project/billing system.
- The output path is checked against the user/job output directory and the data root before being recorded or served.

## Target pipeline

1. Validate image/audio containers and consent/rights; retain the uploaded audio as the first TTS-independent source.
2. Check model files, model-specific requirements, GPU availability, VRAM, disk capacity and licenses before dispatch.
3. Run a version-pinned talking-avatar adapter (InfiniteTalk is only a research candidate at present).
4. Validate the output and save seed/config/model revision and actual engine logs with the job.
5. Expose a result only after the engine returns a real MP4.

This project currently implements step 1 only partially and the API/storage seams; the generation pipeline is not complete.
