# MiniMax H3 Director — Example workflows

Drag a JSON onto the ComfyUI canvas to use it. Requires this plugin installed and a ComfyUI core with MiniMax H3 (v0.30.0+).

| File | Task | UNET | Notes |
|------|------|------|-------|
| `minimax_h3_director_t2v.json` | t2v | fl2va | Text-to audio-video; Queue directly |
| `minimax_h3_director_fl2v.json` | fl2v | fl2va | First/last frame; click "Add shot" and upload a start and/or end frame (end-only OK) |
| `minimax_h3_director_r2v.json` | r2v | **ref2va** | Reference-to-video; asset groups: Picture 1–9 / Audio 1–3 / Video 1–3 |
| `minimax_h3_director_v2v.json` | v2v | **ref2va** | Source-video edit; upload video in the Director and split segments (same as Bernini v2v) |
| `minimax_h3_director_rv2v.json` | rv2v | **ref2va** | Reference-to-video; source video + Picture 1–9 |
| `minimax_h3_director_external_groups_i2v.json` | fl2v | fl2va | External Group (Image to Video) → Combine → Director.`i2v_groups`; duration/assets follow the wiring |
| `minimax_h3_director_external_groups_r2v.json` | r2v | **ref2va** | External Group (Reference to Video) → Combine → Director.`r2v_groups`; use "Select to run" to pick group indices |
| `minimax_h3_director_refine_second_pass.json` | r2v | **ref2va** | Wire **MiniMax H3 Director Refine** → Director.`refine` (SIGMAS + H3 latent). `images` is the refined clip; `images_pre_refine` is the first-pass comparison clip |

## Model paths (same as the official template)

| Role | Filename | Directory |
|------|----------|-----------|
| UNET (t2v/i2v/fl2v) | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | `models/diffusion_models/` |
| UNET (r2v / v2v / rv2v) | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `models/diffusion_models/` |
| CLIP | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `models/text_encoders/` |
| Video VAE | `minimax_h3_video_vae_fp16.safetensors` | `models/vae/` |
| Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` | `models/vae/` |

CLIP Loader **type must be `minimax`**.

## Default sampling

- Canvas default **0.4MP 16:9 (864×480)**, **5s / 124** frames @ **24 fps** (17k+5 grid)
- **25** steps, `res_multistep` + `simple`, CFG **1.0**
- Sigma shift: video **12** / audio **3**

## Output

Director → `CreateVideo` → `SaveVideo` (prefix `video/MiniMaxH3_Director_*`), with the report wired to `PreviewAny`.

The Refine example also wires `images_pre_refine` into a second `CreateVideo` / `SaveVideo` for comparison against the refined clip. When Refine is not connected, that output matches `images`.

## Refine second pass

- The second pass always uses SIGMAS: wire `BasicScheduler` or `ManualSigmas` into the Refine `sigmas` input. For `BasicScheduler`, wire the same MODEL used for the second pass
- No Refine node connected = the original single-pass sampling
- `mode=refine`: same-resolution refine; `mode=upscale`: enlarge to the target canvas then second-sample; `mode=latent_upscale`: enlarge H3 latent only
- The Director resolution is the first pass; the Refine canvas (aspect + megapixels / custom) is the upscale target
- `passes`: refine rounds (default 1); `upscale` enlarges only on the first round; `latent_upscale` does not second-sample
- Optional `refine_model` (second-pass UNET); unwired uses the Director main model
- `upscale` defaults to `h3_latent`: pick the 3D weights in the dropdown under the Refine `upscale_method` (also shown for `mode=latent_upscale`). Put the file in `ComfyUI/models/latent_upscale_models/`. `lanczos` can take an optional `upscale_model` (RealESRGAN, etc.); unwired uses plain interpolation. You can also switch to `nvidia_rtx_vsr`
- fl2v skips the second pass by default; turn off `skip_fl2v` to include first/last-frame shots
