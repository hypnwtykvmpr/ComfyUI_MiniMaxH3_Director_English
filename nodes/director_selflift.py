"""Graph packer: SelfLift (progressive first-pass) for MiniMax H3 Director.selflift."""

from __future__ import annotations

from ..director.h3_latent_upscale import list_h3_latent_upscale_models
from ..director.refine_pack import DEFAULT_SPATIAL_TILES, DEFAULT_TILE_OVERLAP, MAX_SPATIAL_TILES
from ..director.selflift.pack import (
    DEFAULT_HIGHRES_STEPS,
    DEFAULT_LOWRES_SCALE,
    DEFAULT_RHO,
    DEFAULT_TRANSITION_STEP,
    DEFAULT_W_MAX,
    DEFAULT_W_MIN,
    MMX_DIR_SELFLIFT,
    SPLIT_MODES,
    UPSAMPLE_MODES,
    pack_selflift,
)

_CATEGORY = "MiniMaxH3"


class MiniMaxH3DirectorSelfLift:
    """Pack SelfLift settings. Connect ``selflift`` to Director.selflift.

    Unconnected Director is unchanged (same first-pass as today). When wired,
    each segment's first sample is low-res prefix + 3D lift + high-res tail
    on the Director canvas. Timeline continuity keeps a native low-res tail
    plus the existing high-res pin so segment seams stay stable.

    Does not sample by itself. TST (temporal stability) is not bundled —
    patch Director.model before this graph if you use a TST node.
    """

    @classmethod
    def INPUT_TYPES(cls):
        models = list_h3_latent_upscale_models()
        default_model = models[0] if models else ""
        return {
            "required": {
                "bd_grp_selflift_sample": ("BDGROUP", {"default": "Progressive sampling"}),
                "split_mode": (
                    list(SPLIT_MODES),
                    {
                        "default": "highres_steps",
                        "tooltip": (
                            "highres_steps = number of high-res finishing steps (default 2 of 8, i.e. 6 low-res + 2 high-res)."
                            "transition_step = k from the SelfLift paper (default 6 of 8)."
                        ),
                    },
                ),
                "highres_steps": (
                    "INT",
                    {
                        "default": DEFAULT_HIGHRES_STEPS,
                        "min": 1,
                        "max": 64,
                        "tooltip": "split_mode=highres_steps only. Steps in the high-res stage; about 25% of the total is recommended.",
                    },
                ),
                "transition_step": (
                    "INT",
                    {
                        "default": DEFAULT_TRANSITION_STEP,
                        "min": 1,
                        "max": 200,
                        "tooltip": "split_mode=transition_step only. Low-res prefix step count k. Use 6 for 8-step turbo.",
                    },
                ),
                "lowres_scale": (
                    "FLOAT",
                    {
                        "default": DEFAULT_LOWRES_SCALE,
                        "min": 0.25,
                        "max": 1.0,
                        "step": 0.05,
                        "tooltip": (
                            "Low-res canvas = Director canvas x this scale, then snapped to a multiple of 32."
                            "1.0 = no progressive pass; use the original single-stage first pass."
                        ),
                    },
                ),
                "sampler_mode": (
                    ["euler", "follow_director"],
                    {
                        "default": "euler",
                        "tooltip": (
                            "Default euler: SelfLift uses Euler for both stages (the paper's path, s_churn=0)."
                            "It does not change the Director sampler. follow_director = follow the Director, which must also be euler or this raises an error."
                        ),
                    },
                ),
                "native_low_carry": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "Between segments, write the previous segment's native low-res tail into the current low-res prefix (together with the high-res pin)."
                            "Turned off, the low-res prefix is just the high-res tail downgraded again, and seams tend to flicker or blur."
                            "Inert when Director segment continuity is off."
                        ),
                    },
                ),
                "bd_grp_selflift_lift": ("BDGROUP", {"default": "Lift / 3D"}),
                "latent_upscale_model": (
                    models,
                    {
                        "default": default_model,
                        "tooltip": (
                            "H3 3D latent upscale weights, in the same directory as Refine: "
                            "ComfyUI/models/latent_upscale_models/. "
                            "Required when rho=0 (the default)."
                        ),
                    },
                ),
                "latent_upsample": (
                    list(UPSAMPLE_MODES),
                    {
                        "default": "bilinear",
                        "tooltip": "Interpolation for downgrading cond / upsampling the transition state x. The clean endpoint x0 goes through the 3D network.",
                    },
                ),
                "rho": (
                    "FLOAT",
                    {
                        "default": DEFAULT_RHO,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.05,
                        "tooltip": (
                            "Pixel-anchor blend from the paper. 0 = use the 3D lift only (recommended; avoids a VAE round trip)."
                            "Above 0 it decodes the low-res x0, upscales the pixels with lanczos, re-encodes, and blends that into the 3D result using w_min/w_max."
                            "The actual 3D weights are the latent_upscale_model above."
                        ),
                    },
                ),
                "w_min": (
                    "FLOAT",
                    {
                        "default": DEFAULT_W_MIN,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.05,
                        "tooltip": "rho>0 only. Pixel-anchor weight in low-frequency regions.",
                    },
                ),
                "w_max": (
                    "FLOAT",
                    {
                        "default": DEFAULT_W_MAX,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.05,
                        "tooltip": "rho>0 only. Pixel-anchor weight in high-frequency residual regions.",
                    },
                ),
                "enable_latent_chunking": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Temporal chunking for the 3D lift (saves VRAM, off by default). Seams may differ from a whole-segment forward pass.",
                    },
                ),
                "bd_grp_selflift_tile": ("BDGROUP", {"default": "High-res tiling"}),
                "enable_tiling": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Spatial tiling for the high-res finish only (off by default). The low-res stage is not tiled."
                            "Audio is not tiled spatially."
                        ),
                    },
                ),
                "tile_count": (
                    "INT",
                    {
                        "default": DEFAULT_SPATIAL_TILES,
                        "min": 1,
                        "max": MAX_SPATIAL_TILES,
                        "tooltip": "Number of high-res tiles. 1 is the same as no tiling.",
                    },
                ),
                "tile_overlap": (
                    "INT",
                    {
                        "default": DEFAULT_TILE_OVERLAP,
                        "min": 0,
                        "max": 2048,
                        "step": 64,
                        "tooltip": "Overlap between tiles, in output pixels.",
                    },
                ),
            },
            "optional": {
                "model_hires": (
                    "MODEL",
                    {
                        "tooltip": (
                            "Optional UNET for the high-res stage. Unconnected, both the low-res and high-res stages use the Director's main model."
                            "Useful for running Turbo on the low-res stage and a different model on high-res."
                        ),
                    },
                ),
            },
        }

    RETURN_TYPES = (MMX_DIR_SELFLIFT,)
    RETURN_NAMES = ("selflift",)
    FUNCTION = "pack"
    CATEGORY = _CATEGORY
    DESCRIPTION = (
        "Connect to Director.selflift (above refine). Director first-pass becomes "
        "low-res prefix + 3D lift + high-res tail on the timeline canvas. "
        "Unconnected = current single-stage sample. "
        "Refine may still enlarge afterward (upscale / latent_upscale) or stay "
        "same-canvas. FaceRefine still runs after decode. "
        "Timeline continuity keeps native low-res carry + high-res pin. "
        "Euler only. TST is not bundled; patch Director.model if needed."
    )

    def pack(
        self,
        split_mode="highres_steps",
        highres_steps=DEFAULT_HIGHRES_STEPS,
        transition_step=DEFAULT_TRANSITION_STEP,
        lowres_scale=DEFAULT_LOWRES_SCALE,
        sampler_mode="euler",
        native_low_carry=True,
        latent_upscale_model=None,
        latent_upsample="bilinear",
        rho=DEFAULT_RHO,
        w_min=DEFAULT_W_MIN,
        w_max=DEFAULT_W_MAX,
        enable_latent_chunking=False,
        enable_tiling=False,
        tile_count=DEFAULT_SPATIAL_TILES,
        tile_overlap=DEFAULT_TILE_OVERLAP,
        model_hires=None,
        **kwargs,
    ):
        del kwargs
        return (
            pack_selflift(
                split_mode=split_mode,
                highres_steps=highres_steps,
                transition_step=transition_step,
                lowres_scale=lowres_scale,
                latent_upscale_model=latent_upscale_model,
                sampler_mode=sampler_mode,
                native_low_carry=native_low_carry,
                rho=rho,
                w_min=w_min,
                w_max=w_max,
                latent_upsample=latent_upsample,
                enable_latent_chunking=enable_latent_chunking,
                enable_tiling=enable_tiling,
                tile_count=tile_count,
                tile_overlap=tile_overlap,
                model_hires=model_hires,
            ),
        )
