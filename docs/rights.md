# Rights and attribution matrix

This is an engineering inventory, not legal advice. Review the exact code, weight, dataset, and version terms before use.

| Component | Current finding | Commercial/redistribution decision |
|---|---|---|
| Dubai Studio AI Lab code written here | No third-party model code or weights are bundled. Runtime dependencies are pinned in requirements files. | Project owner must choose and publish a project license before release. |
| InfiniteTalk source code | Official repository contains Apache-2.0 `LICENSE.txt` (commit recorded in `models.json`). | Apache-2.0 conditions apply; preserve notices and review patent/trademark terms. |
| InfiniteTalk weights | Upstream README says models in its repository are Apache-2.0. | Verify the actual weight card and each file before redistribution or hosted inference. |
| Wan2.1 base weights | Used as a separate required component by InfiniteTalk instructions. | Check the exact checkpoint terms; no commercial approval is inferred here. |
| Chinese Wav2Vec2 audio encoder | Separate third-party model listed by InfiniteTalk. | License and service rights not verified; block commercial use until reviewed. |
| HunyuanVideo and other candidates | Not integrated; several need a version-specific/custom-license review. | Not approved for use, hosting, or redistribution. |
| Customer media and outputs | Must be governed by customer consent, privacy, publicity, and applicable law. | No rights are granted by this repository; retain only as long as configured and authorized. |
| Third-party APIs | No connector is configured. | If added, disclose provider, pricing, data handling, and API restrictions independently. |

Serving a model as a service and redistributing its weights are distinct legal questions. Keep model attribution, license texts, notices, revisions, and artifacts in an auditable manifest. Never merge weights across unrelated architectures or describe model routing as training a new foundation model.
