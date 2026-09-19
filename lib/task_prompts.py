"""MiniMax H3 task_type labels and combo options (freeform Qwen prompts — no T5 system prefix)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskPromptSpec:
    key: str
    label: str
    system_prompt: str
    description_zh: str


TASK_PROMPT_SPECS: tuple[TaskPromptSpec, ...] = (
    TaskPromptSpec(
        "default",
        "Default",
        "",
        "MiniMax H3 uses freeform Qwen3-VL prompts; no T5 system prefix is needed.",
    ),
    TaskPromptSpec(
        "t2v",
        "Text to Video",
        "",
        "Text-to audio-video; no first frame / reference images.",
    ),
    TaskPromptSpec(
        "i2v",
        "Image to Video",
        "",
        "First-frame image-to audio-video (ImageToVideo + first_frame).",
    ),
    TaskPromptSpec(
        "fl2v",
        "First-Last Frame to Video",
        "",
        "First + last frame constraints (may omit images = text-to-video; ImageToVideo supports optional first/last).",
    ),
    TaskPromptSpec(
        "r2v",
        "Reference to Video",
        "",
        "Grouped reference-to-video (similar to first-last frame groups): each group can upload pictures 1–9, audios 1–3, videos 1–3;"
        " prompts use <Picture N> / <Video K> / <Audio J>. Use v2v/rv2v for source-video timeline editing.",
    ),
    TaskPromptSpec(
        "v2v",
        "Video to Video",
        "",
        "Upload a source video and edit by timeline segment; each segment's source frames are fed as <Video 1> into ReferenceToVideo (no reference-image slots).",
    ),
    TaskPromptSpec(
        "rv2v",
        "Reference Video Edit",
        "",
        "Source-video timeline editing with optional reference images (pictures 1–9) and reference audio (audios 1–3);"
        " each segment's source frames are <Video 1>, reference images use <Picture N>, reference audio uses <Audio J>; identical to v2v when no reference media is present.",
    ),
    TaskPromptSpec(
        "mixed",
        "Mixed Segments",
        "",
        "Each segment on the same timeline picks its own t2v / i2v / fl2v / r2v; sampling uses the official conditioning for that segment's mode."
        " Do not connect a source video (use a dedicated task for v2v/rv2v).",
    ),
)

TASK_PROMPT_BY_KEY = {spec.key: spec for spec in TASK_PROMPT_SPECS}
HIDDEN_TASK_TYPE_KEYS: frozenset[str] = frozenset()


def task_type_option_label(spec: TaskPromptSpec) -> str:
    return f"{spec.key} — {spec.label}"


def task_type_combo_options() -> tuple[list[str], dict]:
    options = [
        task_type_option_label(spec)
        for spec in TASK_PROMPT_SPECS
        if spec.key not in HIDDEN_TASK_TYPE_KEYS and spec.key != "default"
    ]
    default_spec = TASK_PROMPT_BY_KEY["t2v"]
    return options, {
        "default": task_type_option_label(default_spec),
        "tooltip": (
            "MiniMax H3 supports t2v / i2v / fl2v / r2v / v2v / rv2v / mixed."
            " Prompts are sent directly to MiniMaxH3ImageToVideo or MiniMaxH3ReferenceToVideo (tokenized internally)."
            " mixed lets each segment pick t2v/i2v/fl2v/r2v; r2v uses <Picture 1>;"
            " v2v/rv2v are source-video timeline edits (auto-bind <Video 1>); rv2v can also attach reference images."
        ),
    }


def resolve_task_key(task_type_value: str) -> str:
    value = task_type_value.split(",[object Object]", 1)[0].strip()
    if " · " in value:
        value = value.split(" · ", 1)[0].strip()
    for sep in (" — ", " —— ", " - ", " – "):
        if sep in value:
            return value.split(sep, 1)[0].strip()
    return value


def get_task_prompt_spec(task_type_value: str) -> TaskPromptSpec:
    key = resolve_task_key(task_type_value)
    return TASK_PROMPT_BY_KEY.get(key, TASK_PROMPT_BY_KEY["default"])


def apply_task_system_prompt(task_type_value: str, positive_prompt: str) -> str:
    """H3 nodes tokenize raw user prompt — no system prefix injection."""
    del task_type_value
    return positive_prompt
