"""Graph packer: Refine / upscale config for MiniMax H3 Director.refine."""

from __future__ import annotations

import comfy.samplers

from ..director.h3_latent_upscale import list_h3_latent_upscale_models
from ..director.refine_pack import (
    ASPECT_RATIO_CHOICES,
    DEFAULT_REFINE_SIGMA_SAMPLER,
    DEFAULT_UPSCALE_MEGAPIXELS,
    FOLLOW_DIRECTOR_ASPECT,
    MAX_REFINE_PASSES,
    MMX_DIR_REFINE,
    REFINE_MODES,
    SEED_MODES,
    UPSCALE_METHODS,
    infer_upscale_target,
    pack_refine,
)

_CATEGORY = "MiniMaxH3"


class MiniMaxH3DirectorRefine:
    """Pack refine/upscale settings. Connect ``refine`` to Director.refine.

    ``refine``: same-resolution second sample.
    ``upscale``: enlarge to target canvas then second-sample.
    ``latent_upscale``: H3 latent enlarge only, no second sample.
    Second sample uses SIGMAS from BasicScheduler / ManualSigmas.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (
                    list(REFINE_MODES),
                    {
                        "default": "refine",
                        "tooltip": (
                            "refine = same-resolution second sample (refine)."
                            "upscale = enlarge to the target canvas first, then second-sample."
                            "latent_upscale = enlarge only the H3 latent, no second sample."
                        ),
                    },
                ),
                "upscale_method": (
                    list(UPSCALE_METHODS),
                    {
                        "default": "h3_latent",
                        "tooltip": (
                            "Only applies when mode=upscale."
                            "h3_latent = enlarge the H3 video latent to the target canvas first, then second-sample"
                            "(select the 3D weights below)."
                            "lanczos = pixel interpolation; can also connect an upscale_model (RealESRGAN, etc.)."
                            "nvidia_rtx_vsr = NVIDIA RTX Video Super Resolution"
                            "(requires nvidia-vfx + an NVIDIA GPU)."
                        ),
                    },
                ),
                "latent_upscale_model": (
                    list_h3_latent_upscale_models(),
                    {
                        "tooltip": (
                            "H3 3D latent upscale weights."
                            "Place them in ComfyUI/models/latent_upscale_models/ with"
                            "a filename containing 3d (e.g. minimax_h3_latent_upscaler_3d_*.safetensors)."
                            "Used when mode=latent_upscale, or upscale + h3_latent."
                        ),
                    },
                ),
                "sampler": (
                    comfy.samplers.KSampler.SAMPLERS,
                    {
                        "default": DEFAULT_REFINE_SIGMA_SAMPLER,
                        "tooltip": (
                            "Second-pass sampler. Hailuo examples use euler;"
                            "BasicScheduler high-quality second passes commonly use res_multistep."
                        ),
                    },
                ),
                "passes": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": MAX_REFINE_PASSES,
                        "tooltip": (
                            "Number of refine passes. 1 = a single second sample."
                            "With upscale, only the first pass enlarges; later passes refine at the same resolution."
                            "latent_upscale does not second-sample, so this value is ignored."
                        ),
                    },
                ),
            },
            "optional": {
                "refine_model": (
                    "MODEL",
                    {
                        "tooltip": (
                            "Second-pass UNET (refine model)."
                            "If not connected, uses the Director's main model."
                            "Useful for applying a Turbo LoRA on the first pass and removing or swapping it on the second pass."
                        ),
                    },
                ),
                "sigmas": (
                    "SIGMAS",
                    {
                        "forceInput": True,
                        "tooltip": (
                            "Second-pass noise schedule. Connect ComfyUI's BasicScheduler or ManualSigmas."
                            "Required when mode=refine / upscale."
                            "For BasicScheduler, connect the same MODEL used for the second pass (Director main model or refine_model)."
                            "H3's SigmaShift is still applied internally by Refine."
                        ),
                    },
                ),
                "upscale_model": (
                    "UPSCALE_MODEL",
                    {
                        "tooltip": (
                            "Optional. Connect a Load Upscale Model node, e.g. RealESRGAN_x2plus."
                            "Only used when mode=upscale and upscale_method=lanczos."
                            "If not connected, plain lanczos interpolation is used. Ignored with nvidia_rtx_vsr / h3_latent."
                        ),
                    },
                ),
                "seed_mode": (
                    list(SEED_MODES),
                    {
                        "default": "inherit",
                        "tooltip": "inherit = use the Director seed; offset = seed+1, +2… each pass.",
                    },
                ),
                "aspect_ratio": (
                    list(ASPECT_RATIO_CHOICES),
                    {
                        "default": FOLLOW_DIRECTOR_ASPECT,
                        "tooltip": (
                            "Upscale target canvas, same algorithm as the Director's Output Resolution."
                            "The Director is the first-pass resolution (e.g. 0.4 MP); this is the enlarged target"
                            "(e.g. 1.0 MP). Follow Director: derive the 720P tier from the Director canvas ratio."
                            "Ratio presets: pair with megapixels."
                            "Custom: enter width/height directly (aligned to ×32)."
                        ),
                    },
                ),
                "megapixels": (
                    "FLOAT",
                    {
                        "default": DEFAULT_UPSCALE_MEGAPIXELS,
                        "min": 0.0,
                        "max": 16.0,
                        "step": 0.1,
                        "tooltip": (
                            "Megapixels, same as the Director's ResolutionSelector."
                            "1.0 MP at 16:9 is roughly 1376×768 (aligned to 32). Only used with ratio presets."
                        ),
                    },
                ),
                "width": (
                    "INT",
                    {
                        "default": 1280,
                        "min": 0,
                        "max": 8192,
                        "step": 32,
                        "tooltip": "Custom width (×32). Only used with Custom.",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 720,
                        "min": 0,
                        "max": 8192,
                        "step": 32,
                        "tooltip": "Custom height (×32). Only used with Custom.",
                    },
                ),
                "skip_fl2v": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "Skip the second sample / upscale for first-last frame (fl2v) shots."
                            "The second sample alters the image and can drift locked first/last frames; skipped by default to protect keyframes."
                            "When off, fl2v also goes through refine / latent upscale."
                        ),
                    },
                ),
                "confirm_first_pass": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Confirm the first pass before the second pass. Default off: the second sample runs right after the first pass (same as before)."
                            "On: with no first-pass cache, only the first pass runs and writes cache/_pre.mp4;"
                            "with an exactly matching first-pass cache (same seed and first-pass params), the first pass is skipped and only the second pass runs."
                            "For seed, use fixed, or set the seed back to the one used when the cache was written before the second Queue."
                        ),
                    },
                ),
                "enable_latent_chunking": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Temporal chunking for H3 latent upscale (saves VRAM, off by default)."
                            "On: latent over 24 frames is split into 24-frame chunks with weighted overlap blending,"
                            "lowering upscale-net peak VRAM so long segments are less likely to OOM here; seams may differ from a whole-segment forward."
                            "≤24 frames still runs whole. Off is identical to the current behavior."
                        ),
                    },
                ),
                "enable_tiling": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Spatial tiling for the second sample (saves VRAM, off by default)."
                            "On: the video latent is split along the long image edge, each step runs tiled forwards and composites back;"
                            "audio participates as a whole, not spatially split."
                            "Off: whole image sampled in one go, identical to the current behavior."
                            "Ignored when mode=latent_upscale (no second sample)."
                        ),
                    },
                ),
                "tile_count": (
                    "INT",
                    {
                        "default": 2,
                        "min": 1,
                        "max": 8,
                        "step": 1,
                        "tooltip": (
                            "Number of tiles. More tiles lower per-tile VRAM but increase forward passes and are slower."
                            "1 is equivalent to no tiling."
                        ),
                    },
                ),
                "tile_overlap": (
                    "INT",
                    {
                        "default": 128,
                        "min": 0,
                        "max": 2048,
                        "step": 64,
                        "tooltip": (
                            "Overlap between tiles, in output pixels (step 64)."
                            "Larger reduces seams but makes each tile bigger and saves less VRAM."
                        ),
                    },
                ),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, input_types=None, **_kwargs):
        # Skip combo/min checks so old workflows (target_width=0 → aspect_ratio) can load.
        return True

    RETURN_TYPES = (MMX_DIR_REFINE, "INT", "INT")
    RETURN_NAMES = ("refine", "width", "height")
    FUNCTION = "pack"
    CATEGORY = _CATEGORY
    DESCRIPTION = (
        "MiniMax H3 Director Refine: connect to Director.refine. "
        "Director.images is the refined / upscaled result; "
        "Director.images_pre_refine is the first-pass video (before second sample). "
        "Second sample uses SIGMAS from BasicScheduler / ManualSigmas. "
        "Upscale / latent_upscale canvas uses the same aspect + megapixels / custom W×H as Director. "
        "Director first-pass stays at its own resolution; Refine target is the enlarge size. "
        "width / height are the resolved target canvas (×32). "
        "Does not sample by itself — no IMAGE output. "
        "confirm_first_pass: first Queue writes first-pass cache; "
        "second Queue with the same seed runs refine only."
    )

    def pack(
        self,
        mode="refine",
        upscale_method="h3_latent",
        sampler="",
        passes=1,
        seed_mode="inherit",
        aspect_ratio=FOLLOW_DIRECTOR_ASPECT,
        megapixels=DEFAULT_UPSCALE_MEGAPIXELS,
        width=1280,
        height=720,
        skip_fl2v=True,
        confirm_first_pass=False,
        enable_latent_chunking=False,
        enable_tiling=False,
        tile_count=2,
        tile_overlap=128,
        latent_upscale_model=None,
        upscale_model=None,
        h3_latent_model="",
        sigmas=None,
        refine_model=None,
        model=None,
        target_width=0,
        target_height=0,
        **kwargs,
    ):
        del kwargs
        try:
            mp = float(megapixels)
        except (TypeError, ValueError):
            mp = DEFAULT_UPSCALE_MEGAPIXELS
        if mp < 0.1:
            mp = DEFAULT_UPSCALE_MEGAPIXELS
        try:
            w = int(width or 0)
        except (TypeError, ValueError):
            w = 1280
        try:
            h = int(height or 0)
        except (TypeError, ValueError):
            h = 720
        if w < 32:
            w = 1280
        if h < 32:
            h = 720
        try:
            n_passes = int(passes or 1)
        except (TypeError, ValueError):
            n_passes = 1
        if n_passes < 1:
            n_passes = 1
        pack = pack_refine(
            mode=mode,
            passes=n_passes,
            seed_mode=seed_mode,
            aspect_ratio=aspect_ratio,
            megapixels=mp,
            width=w,
            height=h,
            target_width=target_width,
            target_height=target_height,
            skip_fl2v=skip_fl2v,
            confirm_first_pass=bool(confirm_first_pass),
            enable_latent_chunking=bool(enable_latent_chunking),
            enable_tiling=bool(enable_tiling),
            tile_count=tile_count,
            tile_overlap=tile_overlap,
            upscale_method=upscale_method,
            sample_model=refine_model if refine_model is not None else model,
            latent_upscale_model=latent_upscale_model if latent_upscale_model is not None else h3_latent_model,
            upscale_model=upscale_model,
            sampler=sampler,
            sigmas=sigmas,
        )
        out_w = int(pack.get("target_width") or 0)
        out_h = int(pack.get("target_height") or 0)
        if out_w <= 0 or out_h <= 0:
            out_w, out_h = infer_upscale_target(0, 0)
        return (pack, int(out_w), int(out_h))
