"""Graph packer: face-refine config for MiniMax H3 Director.face_refine."""

from __future__ import annotations

import comfy.samplers

from ..director.face_refine.pack import (
    CANVAS_MODES,
    DEFAULT_DETECTOR,
    DEFAULT_SAMPLER,
    DEFAULT_SCHEDULER,
    MMX_DIR_FACE_REFINE,
    PASTE_REGIONS,
    SEED_MODES,
    SELECT_MODES,
    detector_choices,
    pack_face_refine,
)

_CATEGORY = "MiniMaxH3"


class MiniMaxH3DirectorFaceRefine:
    """Pack face-refine settings. Connect ``face_refine`` to Director.face_refine.

    Unconnected Director skips this entirely. When wired, Director tracks the
    face on the final decoded frames (after Refine if that node is also wired),
    re-samples the crop with MiniMax H3, and pastes only the face back.
    """

    @classmethod
    def INPUT_TYPES(cls):
        detectors = detector_choices()
        return {
            "required": {
                "bd_grp_face_detect": ("BDGROUP", {"default": "Face detection settings"}),
                "detector": (
                    detectors,
                    {
                        "default": DEFAULT_DETECTOR if DEFAULT_DETECTOR in detectors else detectors[0],
                        "tooltip": (
                            "Face detection weights; put them in models/ultralytics/bbox/ (e.g. face_yolov8m.pt)."
                        ),
                    },
                ),
                "confidence": (
                    "FLOAT",
                    {
                        "default": 0.35,
                        "min": 0.05,
                        "max": 0.95,
                        "step": 0.05,
                        "tooltip": "Detection threshold. Lower values catch profile and small faces more easily.",
                    },
                ),
                "crop_factor": (
                    "FLOAT",
                    {
                        "default": 2.5,
                        "min": 1.2,
                        "max": 8.0,
                        "step": 0.1,
                        "tooltip": "Crop edge length = face height x this multiplier. 2.0-3.0 is typical.",
                    },
                ),
                "canvas_width": (
                    "INT",
                    {
                        "default": 768,
                        "min": 128,
                        "max": 1344,
                        "step": 32,
                        "tooltip": "Width of the H3 generated crop. Used in manual mode.",
                    },
                ),
                "canvas_height": (
                    "INT",
                    {
                        "default": 768,
                        "min": 128,
                        "max": 1344,
                        "step": 32,
                        "tooltip": "Height of the H3 generated crop. Used in manual mode.",
                    },
                ),
                "canvas_mode": (
                    list(CANVAS_MODES),
                    {
                        "default": "manual",
                        "tooltip": (
                            "manual = use the width/height above."
                            "auto_capped_768 = adapt to the largest crop, capped at 768."
                        ),
                    },
                ),
                "select": (
                    list(SELECT_MODES),
                    {
                        "default": "largest_face",
                        "tooltip": "Lock target: the largest face, or the one nearest the frame centre. Once locked, tracking follows the nearest box.",
                    },
                ),
                "bd_grp_face_sample": ("BDGROUP", {"default": "Sampling settings"}),
                "denoise": (
                    "FLOAT",
                    {
                        "default": 0.40,
                        "min": 0.02,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": (
                            "Denoise for re-sampling the crop (BasicScheduler). Do not use FaceDetailer's 0.25 on H3; "
                            "the template uses about 0.40. Ignored when the sigmas input is connected."
                        ),
                    },
                ),
                "steps": (
                    "INT",
                    {
                        "default": 8,
                        "min": 1,
                        "max": 50,
                        "tooltip": "Face refine sampling steps. 8 is typical with a turbo LoRA. Ignored when sigmas is connected.",
                    },
                ),
                "sampler": (
                    comfy.samplers.KSampler.SAMPLERS,
                    {
                        "default": DEFAULT_SAMPLER,
                        "tooltip": "Face refine sampler. The example workflows use euler.",
                    },
                ),
                "scheduler": (
                    comfy.samplers.KSampler.SCHEDULERS,
                    {
                        "default": DEFAULT_SCHEDULER,
                        "tooltip": "Face refine scheduler. Ignored when the sigmas input is connected.",
                    },
                ),
            },
            "optional": {
                "seed_mode": (
                    list(SEED_MODES),
                    {
                        "default": "inherit",
                        "tooltip": "inherit = use the Director seed; offset = seed + 1 + segment number.",
                    },
                ),
                "bd_grp_face_paste": ("BDGROUP", {"default": "Paste-back settings"}),
                "paste_region": (
                    list(PASTE_REGIONS),
                    {
                        "default": "face_only",
                        "tooltip": "Paste only the detected face box (recommended). full_crop pastes the whole crop and tends to leave a visible square.",
                    },
                ),
                "mask_dilation": (
                    "INT",
                    {"default": 16, "min": 0, "max": 256, "step": 2},
                ),
                "feather": (
                    "INT",
                    {
                        "default": 24,
                        "min": 0,
                        "max": 256,
                        "step": 2,
                        "tooltip": "Paste-back feather radius, in finished-clip pixels. About 24 suits a rectangular mask.",
                    },
                ),
                "colour_match": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05},
                ),
                "blend": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05},
                ),
                "sigmas": (
                    "SIGMAS",
                    {
                        "forceInput": True,
                        "tooltip": "Optional. When connected it overrides steps / scheduler / denoise.",
                    },
                ),
            },
        }

    RETURN_TYPES = (MMX_DIR_FACE_REFINE,)
    RETURN_NAMES = ("face_refine",)
    FUNCTION = "pack"
    CATEGORY = _CATEGORY
    DESCRIPTION = (
        "Connect to Director.face_refine. Director then face-refines the final decoded "
        "segment (after Director Refine if that is also connected). "
        "images is the stitched result; images_pre_face_refine is the video before stitch "
        "when Director 'Export pre-face-refine' is on. "
        "Unconnected Director is unchanged. Requires ultralytics + a face YOLO weight."
    )

    def pack(
        self,
        detector=DEFAULT_DETECTOR,
        confidence=0.35,
        crop_factor=2.5,
        canvas_width=768,
        canvas_height=768,
        canvas_mode="manual",
        select="largest_face",
        denoise=0.40,
        steps=8,
        sampler=DEFAULT_SAMPLER,
        scheduler=DEFAULT_SCHEDULER,
        seed_mode="inherit",
        paste_region="face_only",
        mask_dilation=16,
        feather=24,
        colour_match=1.0,
        blend=1.0,
        sigmas=None,
        **kwargs,
    ):
        del kwargs
        return (
            pack_face_refine(
                detector=detector,
                confidence=confidence,
                crop_factor=crop_factor,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                canvas_mode=canvas_mode,
                select=select,
                denoise=denoise,
                steps=steps,
                sampler=sampler,
                scheduler=scheduler,
                seed_mode=seed_mode,
                paste_region=paste_region,
                mask_dilation=mask_dilation,
                feather=feather,
                colour_match=colour_match,
                blend=blend,
                sigmas=sigmas,
            ),
        )
