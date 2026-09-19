/** MiniMax H3 Director Refine — show canvas widgets like Director output bar. */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import {
    CUSTOM_ASPECT_RATIO,
    resolutionFromSelector,
    snapResolutionDim,
} from "./minimax_gen_timeline.js";
import { injectExternalGroupsWitness } from "./minimax_external_witness.js";
import { t } from "./minimax_i18n.js";
import { collectSelfLiftWitness } from "./minimax_selflift.js";

const REFINE_CLASS = "MiniMaxH3DirectorRefine";
const DIRECTOR_CLASSES = new Set(["MiniMaxH3Director", "ComfyMiniMaxH3Director"]);
const CACHE_STATUS_WIDGET = "first_pass_cache_status";
const FOLLOW_DIRECTOR_ASPECT = "Follow Director";

function isRefineNode(node) {
    const cls = node?.comfyClass || node?.type || "";
    return cls === REFINE_CLASS;
}

function widgetByName(node, name) {
    return node.widgets?.find((w) => w.name === name);
}

function widgetValue(w) {
    if (!w) return undefined;
    const v = w.value;
    if (v && typeof v === "object") {
        if (typeof v.content === "string") return v.content;
        if (typeof v.value === "string") return v.value;
    }
    return v;
}

function setWidgetVisible(node, name, visible) {
    const w = widgetByName(node, name);
    if (!w) return;
    w.hidden = !visible;
    if (!w.options) w.options = {};
    w.options.hidden = !visible;
    if (visible) {
        if (w._mmxOrigComputeSize) {
            w.computeSize = w._mmxOrigComputeSize;
            delete w._mmxOrigComputeSize;
        } else if (w.computeSize) {
            delete w.computeSize;
        }
        if (w.element) w.element.style.display = "";
    } else {
        if (!w._mmxOrigComputeSize && typeof w.computeSize === "function") {
            w._mmxOrigComputeSize = w.computeSize.bind(w);
        }
        w.computeSize = () => [0, -4];
        if (w.element) w.element.style.display = "none";
    }
}

function isCustomAspect(value) {
    const v = String(value ?? "").trim();
    return v === CUSTOM_ASPECT_RATIO || v === "Custom" || v.startsWith("自定义");
}

const ASPECT_CHOICES = new Set([
    FOLLOW_DIRECTOR_ASPECT,
    "Follow Director",
    CUSTOM_ASPECT_RATIO,
    "Custom",
    "1:1 (Square)",
    "2:3 (Portrait photo)",
    "3:2 (Landscape photo)",
    "3:4 (Portrait standard)",
    "4:3 (Standard)",
    "9:16 (Portrait)",
    "16:9 (Widescreen)",
    "21:9 (Ultrawide)",
]);

const UPSCALE_METHOD_VALUES = new Set(["lanczos", "nvidia_rtx_vsr", "h3_latent"]);
const SEED_MODE_VALUES = new Set(["inherit", "offset"]);
const SAMPLER_HINTS = new Set([
    "euler", "euler_ancestral", "heun", "heunpp2", "dpm_2", "dpm_2_ancestral",
    "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_sde",
    "dpmpp_sde_gpu", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu",
    "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm", "ipndm", "ipndm_v",
    "deis", "res_multistep", "res_multistep_ancestral", "gradient_estimation",
    "er_sde", "seeds_2", "seeds_3", "sa_solver", "sa_solver_pece",
    "uni_pc", "uni_pc_bh2", "ddim",
]);

function looksLikeUpscaleMethod(value) {
    return UPSCALE_METHOD_VALUES.has(String(value ?? "").trim().toLowerCase());
}

function looksLikeSampler(value) {
    return SAMPLER_HINTS.has(String(value ?? "").trim().toLowerCase());
}

function clampPasses(value) {
    const n = Math.round(Number(value));
    if (!Number.isFinite(n) || n < 1) return 1;
    return Math.min(9999, n);
}

function migrateRefineWidgetOrder(node) {
    const samplerW = widgetByName(node, "sampler");
    const passesW = widgetByName(node, "passes");
    const methodW = widgetByName(node, "upscale_method");
    if (samplerW && !looksLikeSampler(widgetValue(samplerW))) {
        samplerW.value = "euler";
    }
    if (passesW) {
        passesW.value = clampPasses(widgetValue(passesW));
    }
    if (methodW && !looksLikeUpscaleMethod(widgetValue(methodW))) {
        methodW.value = "h3_latent";
    }
}

function migrateLegacyPrePassesValues(node) {
    const seedW = widgetByName(node, "seed_mode");
    const aspectW = widgetByName(node, "aspect_ratio");
    const mpW = widgetByName(node, "megapixels");
    const widthW = widgetByName(node, "width");
    const heightW = widgetByName(node, "height");
    const skipW = widgetByName(node, "skip_fl2v");
    const rawSeed = widgetValue(seedW);
    if (!seedW || SEED_MODE_VALUES.has(String(rawSeed ?? "").trim().toLowerCase())) return;

    // Workflows saved before `passes` was inserted load every following value
    // one slot early: seed_mode gets the aspect ratio, aspect gets MP, etc.
    if (ASPECT_CHOICES.has(rawSeed)) {
        const rawAspect = widgetValue(aspectW);
        const rawMp = widgetValue(mpW);
        const rawWidth = widgetValue(widthW);
        const rawHeight = widgetValue(heightW);
        seedW.value = "inherit";
        if (aspectW) aspectW.value = rawSeed;
        const mp = Number(rawAspect);
        if (mpW && Number.isFinite(mp) && mp >= 0.1 && mp <= 16) mpW.value = mp;
        const width = Number(rawMp);
        if (widthW && Number.isFinite(width) && width >= 32 && width <= 8192) widthW.value = width;
        const height = Number(rawWidth);
        if (heightW && Number.isFinite(height) && height >= 32 && height <= 8192) heightW.value = height;
        if (skipW && (rawHeight === true || rawHeight === false)) skipW.value = rawHeight;
        node._mmxRecoveredLegacyRefineValues = true;
        return;
    }
    seedW.value = "inherit";
}

function migrateRefineWidgets(node) {
    migrateLegacyPrePassesValues(node);
    migrateRefineWidgetOrder(node);
    const seedW = widgetByName(node, "seed_mode");
    const aspectW = widgetByName(node, "aspect_ratio");
    const mpW = widgetByName(node, "megapixels");
    const widthW = widgetByName(node, "width");
    const heightW = widgetByName(node, "height");
    if (seedW && !SEED_MODE_VALUES.has(String(widgetValue(seedW) ?? "").trim().toLowerCase())) {
        seedW.value = "inherit";
    }
    if (aspectW && !ASPECT_CHOICES.has(widgetValue(aspectW))) {
        aspectW.value = FOLLOW_DIRECTOR_ASPECT;
    }
    if (mpW) {
        const n = Number(widgetValue(mpW));
        if (!Number.isFinite(n) || n < 0.1 || n > 16) mpW.value = 1.0;
    }
    if (widthW) {
        const n = Number(widgetValue(widthW));
        if (!Number.isFinite(n) || n < 32 || n > 8192) widthW.value = 1280;
    }
    if (heightW) {
        const n = Number(widgetValue(heightW));
        if (!Number.isFinite(n) || n < 32 || n > 8192) heightW.value = 720;
    }
    setWidgetVisible(node, "schedule", false);
    setWidgetVisible(node, "denoise", false);
    setWidgetVisible(node, "steps", false);
    setWidgetVisible(node, "sigmas_text", false);
    setWidgetVisible(node, "sigmas", false);
    setWidgetVisible(node, "h3_latent_model", false);
    setWidgetVisible(node, "upscale_model", false);
}

function isFollowAspect(value) {
    const v = String(value ?? "").trim();
    if (v === "0" || v === "0.0") return true;
    return !v || v === FOLLOW_DIRECTOR_ASPECT || v === "Follow Director";
}

function readMode(node) {
    const named = widgetByName(node, "mode");
    const raw = String(widgetValue(named) ?? "").toLowerCase();
    if (raw.includes("latent_upscale") || raw.includes("latent")) return "latent_upscale";
    if (raw.includes("upscale")) return "upscale";
    if (raw.includes("refine")) return "refine";
    for (const w of node.widgets || []) {
        const s = String(widgetValue(w) ?? "").toLowerCase();
        if (s === "latent_upscale") return "latent_upscale";
        if (s === "upscale") return "upscale";
        if (s === "refine") return "refine";
    }
    return null;
}

function syncRefineComputedSize(node) {
    const aspectW = widgetByName(node, "aspect_ratio");
    const mpW = widgetByName(node, "megapixels");
    const widthW = widgetByName(node, "width");
    const heightW = widgetByName(node, "height");
    if (!aspectW || isFollowAspect(widgetValue(aspectW)) || isCustomAspect(widgetValue(aspectW))) return;
    const resolved = resolutionFromSelector(widgetValue(aspectW), widgetValue(mpW) ?? 1.0);
    if (!resolved) return;
    if (widthW) widthW.value = resolved.width;
    if (heightW) heightW.value = resolved.height;
}

function readUpscaleMethod(node) {
    return String(widgetValue(widgetByName(node, "upscale_method")) ?? "").trim().toLowerCase();
}

function boolWidgetValue(node, name) {
    const value = widgetValue(widgetByName(node, name));
    return value === true || value === 1 || String(value).toLowerCase() === "true";
}

function graphNodes() {
    const graph = app.graph ?? app.canvas?.graph;
    return graph?._nodes ?? graph?.nodes ?? [];
}

function connectedDirector(refineNode) {
    const graph = refineNode?.graph ?? app.graph ?? app.canvas?.graph;
    for (const candidate of graphNodes()) {
        const cls = candidate?.comfyClass || candidate?.type || "";
        if (!DIRECTOR_CLASSES.has(cls)) continue;
        const input = candidate.inputs?.find((item) => item?.name === "refine");
        if (input?.link == null) continue;
        const link = graph?.links?.[input.link] ?? graph?._links?.[input.link];
        if (String(link?.origin_id) === String(refineNode.id)) return candidate;
    }
    return null;
}

function directorValue(node, name, fallback) {
    const value = widgetValue(widgetByName(node, name));
    return value == null || value === "" ? fallback : value;
}

/** Fingerprint key → what the user actually changed. */
/** Cache-diff key -> i18n key. Values are resolved through t() at call time so
 *  the panel follows the language toggle like the rest of the UI. */
const CACHE_DIFF_LABEL_KEYS = {
    seed: "refine.diff.seed",
    start: "refine.diff.start",
    end: "refine.diff.end",
    prompt: "refine.diff.prompt",
    negative: "refine.diff.negative",
    task_key: "refine.diff.task_key",
    width: "refine.diff.width",
    height: "refine.diff.height",
    frame_rate: "refine.diff.frame_rate",
    output_mode: "refine.diff.output_mode",
    refs: "refine.diff.refs",
    ref_audios: "refine.diff.ref_audios",
    ref_videos: "refine.diff.ref_videos",
    ref_video: "refine.diff.ref_video",
    ref_video_start: "refine.diff.ref_video_start",
    ref_max: "refine.diff.ref_max",
    ref_image_size: "refine.diff.ref_image_size",
    source_video: "refine.diff.source_video",
    continuity: "refine.diff.continuity",
    continuity_overlap: "refine.diff.continuity_overlap",
    continuity_mode: "refine.diff.continuity_mode",
    continuity_redraw: "refine.diff.continuity_redraw",
    continuity_keep_tail: "refine.diff.continuity_keep_tail",
    continuity_from_prev: "refine.diff.continuity_from_prev",
    continuity_pipeline: "refine.diff.continuity_pipeline",
    cfg: "refine.diff.cfg",
    steps: "refine.diff.steps",
    sampler: "refine.diff.sampler",
    scheduler: "refine.diff.scheduler",
    sigmas: "refine.diff.sigmas",
    sigmas_source: "refine.diff.sigmas_source",
    shift_video: "refine.diff.shift_video",
    shift_audio: "refine.diff.shift_audio",
    "<invalid-meta>": "refine.diff.invalidMeta",
    external_wiring: "refine.diff.external_wiring",
    external_prompt: "refine.diff.external_prompt",
    external_length: "refine.diff.external_length",
    external_shift: "refine.diff.external_shift",
    external_media: "refine.diff.external_media",
    external_other: "refine.diff.external_other",
    external_groups_off: "refine.diff.external_groups_off",
    "<unverified-external>": "refine.diff.unverifiedExternal",
    selflift: "refine.diff.selflift",
    sl_split: "refine.diff.sl_split",
    sl_high: "refine.diff.sl_high",
    sl_trans: "refine.diff.sl_trans",
    sl_scale: "refine.diff.sl_scale",
    sl_model: "refine.diff.sl_model",
    sl_samp: "refine.diff.sl_samp",
    sl_carry: "refine.diff.sl_carry",
    sl_rho: "refine.diff.sl_rho",
    sl_wmin: "refine.diff.sl_wmin",
    sl_wmax: "refine.diff.sl_wmax",
    sl_up: "refine.diff.sl_up",
    sl_chunk: "refine.diff.sl_chunk",
    sl_tile: "refine.diff.sl_tile",
    sl_tiles: "refine.diff.sl_tiles",
    sl_overlap: "refine.diff.sl_overlap",
    sl_hires_model: "refine.diff.sl_hires_model",
};

function diffLabel(key) {
    const k = CACHE_DIFF_LABEL_KEYS[key];
    return k ? t(k) : key;
}

/**
 * One compact line naming the segments that cannot be reused. 1 group = 1
 * segment = 1 cache slot, and a segment is compared against its own group only,
 * so an edit to one group leaves the others matching — listing every segment
 * would bury that (and the rest of the panel) under a dozen lines.
 */
function externalMismatchLine(data) {
    const rows = Array.isArray(data?.segments) ? data.segments : [];
    const bad = rows.filter((row) => !row?.matches);
    if (!bad.length) return "";
    const sep = t("refine.listSep");
    const reasons = (row) => {
        const keys = (Array.isArray(row?.diff_keys) ? row.diff_keys : [])
            .filter((key) => key !== "<missing-cache>");
        return keys.length ? keys.map(diffLabel).join(sep) : t("refine.mismatch.noCache");
    };
    if (bad.length === rows.length && rows.length > 1) {
        const all = [...new Set(bad.flatMap((row) => reasons(row).split(sep)))].join(sep);
        return t("refine.mismatch.all", { n: rows.length, reasons: all });
    }
    const parts = bad.slice(0, 4).map((row) => t("refine.mismatch.entry", {
        slot: row?.slot || t("refine.mismatch.segment", { n: row?.segment }),
        reasons: reasons(row),
    }));
    if (bad.length > parts.length) parts.push(t("refine.mismatch.more", { n: bad.length }));
    return t("refine.mismatch.some", { parts: parts.join(sep) });
}

function directorHasSigmasLink(node) {
    const inp = (node?.inputs || []).find((i) => String(i.name) === "sigmas");
    if (!inp) return false;
    if (inp.link != null) return true;
    return Array.isArray(inp.links) && inp.links.length > 0;
}

function cacheStatusPayload(director) {
    try {
        director?._minimaxEditor?._writeTimelineWidget?.();
    } catch {
        /* best effort */
    }
    return {
        node_id: String(director.id),
        // Keep the graph-wired external-group witness current: the status route
        // runs on the backend where i2v_groups / r2v_groups links are invisible.
        timeline_data: injectExternalGroupsWitness(
            director,
            String(directorValue(director, "timeline_data", "")),
        ),
        task_type: String(directorValue(director, "task_type", "")),
        global_prompt: String(directorValue(director, "global_prompt", "")),
        total_frames: Number(directorValue(director, "total_frames", 124)),
        frame_rate: Number(directorValue(director, "frame_rate", 24)),
        width: Number(directorValue(director, "width", 864)),
        height: Number(directorValue(director, "height", 480)),
        ref_max_size: Number(directorValue(director, "ref_max_size", 864)),
        seed: Number(directorValue(director, "seed", 0)),
        cfg: Number(directorValue(director, "cfg", 1)),
        steps: Number(directorValue(director, "steps", 25)),
        sampler: String(directorValue(director, "sampler", "")),
        scheduler: String(directorValue(director, "scheduler", "")),
        shift_video: Number(directorValue(director, "shift_video", 12)),
        shift_audio: Number(directorValue(director, "shift_audio", 3)),
        sigmas_linked: directorHasSigmasLink(director),
        // SelfLift is a graph-wired pack, not a Director widget. The run writes
        // sl_* into first-pass meta; the panel must send the same pack or it
        // always reports those keys as diffs.
        selflift: collectSelfLiftWitness(director),
    };
}

function renderCacheStatus(node, data, kind = "normal") {
    const ui = node._mmxFirstPassCacheUI;
    if (!ui) return;
    const colors = {
        normal: "var(--input-text, #ddd)",
        ok: "#65d68a",
        warn: "#f0bd58",
        error: "#ef7777",
        muted: "#aaa",
    };
    ui.body.style.color = colors[kind] || colors.normal;
    if (typeof data === "string") {
        ui.body.textContent = data;
        return;
    }
    const total = Number(data?.segment_total || 0);
    const cached = Number(data?.cached_count || 0);
    const matched = Number(data?.matched_count || 0);
    const seeds = Array.isArray(data?.cached_seeds) && data.cached_seeds.length
        ? data.cached_seeds.join(", ")
        : "—";
    const diffs = Array.isArray(data?.diff_keys)
        ? data.diff_keys
            .filter((key) => key !== "<missing-cache>")
            .slice(0, 8)
            .map(diffLabel)
        : [];
    const selTotal = data?.selected_total;
    const selMatched = data?.selected_matched;
    const selActive = Number.isFinite(selTotal) && Number(selTotal) !== total;
    const lines = [
        t("refine.cache.firstPass", {
            state: data?.exists
                ? t("refine.cache.present", { cached, total })
                : t("refine.cache.absent"),
        }),
        t("refine.cache.match", {
            state: data?.matches
                ? t("refine.cache.matchYes", { matched, total })
                : t("refine.cache.matchNo"),
        }) + (selActive
            ? t("refine.cache.selected", { sel: selMatched ?? 0, total: selTotal ?? 0 })
            : ""),
    ];
    lines.push(t("refine.cache.seed", { seeds }));
    lines.push(t("refine.cache.currentSeed", { seed: data?.current_seed ?? "—" }));
    const finalCached = Number(data?.final_cached_count || 0);
    lines.push(t("refine.cache.finalCache", { n: finalCached, total }));
    if (diffs.length) lines.push(t("refine.cache.differences", { list: diffs.join(t("refine.listSep")) }));
    if (data?.mode === "external_groups") {
        // External groups are not on the timeline: each segment is compared
        // against its own group (prompt / duration / its reference slots) plus
        // the plan-level knobs.
        lines.push(t("refine.cache.checkedExternal"));
        const mismatch = externalMismatchLine(data);
        if (mismatch) lines.push(mismatch);
    }
    const unverified = Number(data?.unverified_count || 0);
    if (unverified > 0) {
        lines.push(t("refine.cache.noteUnverified", { n: unverified }));
    }
    const staleExternal = Number(data?.stale_external_count || 0);
    if (staleExternal > 0) {
        lines.push(t("refine.cache.noteStale", { n: staleExternal }));
    }
    ui.body.textContent = lines.join("\n");
}

async function refreshFirstPassCacheStatus(node) {
    if (!isRefineNode(node)) return;
    ensureFirstPassCacheUI(node);
    const director = connectedDirector(node);
    if (!director) {
        renderCacheStatus(node, "No connected MiniMax H3 Director found.", "warn");
        return;
    }
    const seq = (node._mmxCacheStatusSeq || 0) + 1;
    node._mmxCacheStatusSeq = seq;
    renderCacheStatus(node, "Checking segment cache…", "muted");
    try {
        const response = await api.fetchApi("/minimax/director/first_pass_cache_status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(cacheStatusPayload(director)),
        });
        const data = await response.json();
        if (seq !== node._mmxCacheStatusSeq) return;
        if (!response.ok || data?.error) {
            throw new Error(data?.error || `HTTP ${response.status}`);
        }
        renderCacheStatus(node, data, data.matches ? "ok" : (data.exists ? "warn" : "muted"));
    } catch (error) {
        if (seq !== node._mmxCacheStatusSeq) return;
        renderCacheStatus(node, `Cache check failed: ${error?.message || error}`, "error");
    }
}

function scheduleCacheStatusRefresh(node, delay = 120) {
    clearTimeout(node._mmxCacheStatusTimer);
    node._mmxCacheStatusTimer = setTimeout(() => refreshFirstPassCacheStatus(node), delay);
}

function refreshCacheStatusForDirector(director, delay = 120) {
    for (const node of graphNodes()) {
        if (
            isRefineNode(node)
            && connectedDirector(node) === director
        ) {
            scheduleCacheStatusRefresh(node, delay);
        }
    }
}

function ensureFirstPassCacheUI(node) {
    if (node._mmxFirstPassCacheUI || typeof node.addDOMWidget !== "function") return;
    const root = document.createElement("div");
    root.style.cssText = [
        "box-sizing:border-box",
        "margin:4px 8px",
        "padding:8px 10px",
        "border:1px solid var(--border-color, #555)",
        "border-radius:6px",
        "background:rgba(0,0,0,.16)",
        "font:12px/1.45 sans-serif",
    ].join(";");
    const header = document.createElement("div");
    header.style.cssText = "display:flex;align-items:center;justify-content:space-between;margin-bottom:5px";
    const title = document.createElement("strong");
    title.textContent = t("refine.cache.title");
    const makeHeaderButton = (text, onClick) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = text;
        btn.style.cssText = "padding:2px 8px;cursor:pointer";
        btn.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            onClick();
        });
        return btn;
    };
    const buttons = document.createElement("div");
    buttons.style.cssText = "display:flex;align-items:center;gap:6px";
    const clearBtn = makeHeaderButton(t("refine.cache.clear"), () => clearSegmentCache(node));
    const refresh = makeHeaderButton(t("refine.cache.recheck"), () => refreshFirstPassCacheStatus(node));
    buttons.append(clearBtn, refresh);
    const body = document.createElement("div");
    body.style.cssText = "white-space:pre-wrap;word-break:break-word;user-select:text;cursor:text";
    body.textContent = t("refine.cache.waiting");
    for (const eventName of ["pointerdown", "mousedown", "click"]) {
        body.addEventListener(eventName, (event) => event.stopPropagation());
    }
    header.append(title, buttons);
    root.append(header, body);
    const widget = node.addDOMWidget(CACHE_STATUS_WIDGET, "cache_status", root, {
        getValue: () => "",
        setValue: () => {},
        getMinHeight: () => 148,
        hideOnZoom: false,
    });
    // Status is derived UI, not a positional backend widget value.
    widget.serialize = false;
    if (!widget.options) widget.options = {};
    widget.options.serialize = false;
    node._mmxFirstPassCacheUI = { root, body, refresh, widget };
}

async function clearSegmentCache(node) {
    const director = connectedDirector(node);
    if (!director) {
        renderCacheStatus(node, "No connected MiniMax H3 Director found.", "warn");
        return;
    }
    if (!window.confirm("Clear this node's segment cache? Both first-pass and final caches will be deleted and must be regenerated.")) {
        return;
    }
    renderCacheStatus(node, "Clearing cache…", "muted");
    try {
        const response = await api.fetchApi("/minimax/director/clear_segment_cache", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ node_id: String(director.id), kind: "all" }),
        });
        const data = await response.json();
        if (!response.ok || data?.error) {
            throw new Error(data?.error || `HTTP ${response.status}`);
        }
        renderCacheStatus(node, `Cache cleared (deleted ${data.removed} files).`, "ok");
        scheduleCacheStatusRefresh(node, 200);
    } catch (error) {
        renderCacheStatus(node, `Failed to clear cache: ${error?.message || error}`, "error");
    }
}

function syncRefineWidgetVisibility(node) {
    const mode = readMode(node);
    const upscale = mode === "upscale";
    const latentOnly = mode === "latent_upscale";
    const needsCanvas = upscale || latentOnly;
    const aspect = widgetValue(widgetByName(node, "aspect_ratio"));
    const follow = isFollowAspect(aspect);
    const custom = isCustomAspect(aspect);
    setWidgetVisible(node, "aspect_ratio", needsCanvas);
    setWidgetVisible(node, "megapixels", needsCanvas && !follow && !custom);
    setWidgetVisible(node, "width", needsCanvas && custom);
    setWidgetVisible(node, "height", needsCanvas && custom);
    const method = readUpscaleMethod(node);
    const showH3Model = latentOnly || (upscale && method === "h3_latent");
    setWidgetVisible(node, "upscale_method", upscale);
    setWidgetVisible(node, "latent_upscale_model", showH3Model);
    setWidgetVisible(node, "enable_latent_chunking", showH3Model);
    setWidgetVisible(node, "h3_latent_model", false);
    setWidgetVisible(node, "upscale_model", false);
    setWidgetVisible(node, "schedule", false);
    setWidgetVisible(node, "denoise", false);
    setWidgetVisible(node, "steps", false);
    setWidgetVisible(node, "sigmas_text", false);
    setWidgetVisible(node, "sigmas", false);
    setWidgetVisible(node, "sampler", !latentOnly);
    setWidgetVisible(node, "passes", !latentOnly);
    setWidgetVisible(node, "seed_mode", !latentOnly);
    setWidgetVisible(node, "enable_tiling", !latentOnly);
    const tilingOn = !latentOnly && Boolean(widgetValue(widgetByName(node, "enable_tiling")));
    setWidgetVisible(node, "tile_count", tilingOn);
    setWidgetVisible(node, "tile_overlap", tilingOn);
    setWidgetVisible(node, "target_width", false);
    setWidgetVisible(node, "target_height", false);
    ensureFirstPassCacheUI(node);
    setWidgetVisible(node, CACHE_STATUS_WIDGET, true);
    if (needsCanvas && !follow && !custom) syncRefineComputedSize(node);
    try {
        const size = node.computeSize?.();
        if (Array.isArray(size) && size.length >= 2) {
            node.setSize?.([node.size?.[0] || size[0], size[1]]);
        }
    } catch {
        /* ignore */
    }
    node.setDirtyCanvas?.(true, true);
}

function hookWidget(node, name, fn) {
    if (!node._mmxRefineHooked) node._mmxRefineHooked = new Set();
    if (node._mmxRefineHooked.has(name)) return;
    const w = widgetByName(node, name);
    if (!w) return;
    node._mmxRefineHooked.add(name);
    const prev = w.callback;
    w.callback = function (...args) {
        const r = prev?.apply(this, args);
        fn();
        return r;
    };
}

function installRefineResolutionUI(node) {
    const onAspect = () => {
        const aspectW = widgetByName(node, "aspect_ratio");
        const widthW = widgetByName(node, "width");
        const heightW = widgetByName(node, "height");
        if (aspectW && isCustomAspect(widgetValue(aspectW)) && widthW && heightW) {
            widthW.value = snapResolutionDim(widgetValue(widthW) || 1280);
            heightW.value = snapResolutionDim(widgetValue(heightW) || 720);
        }
        syncRefineWidgetVisibility(node);
    };
    hookWidget(node, "mode", () => syncRefineWidgetVisibility(node));
    hookWidget(node, "upscale_method", () => syncRefineWidgetVisibility(node));
    hookWidget(node, "enable_tiling", () => syncRefineWidgetVisibility(node));
    hookWidget(node, "aspect_ratio", onAspect);
    hookWidget(node, "megapixels", () => syncRefineComputedSize(node));
    hookWidget(node, "width", () => {
        const w = widgetByName(node, "width");
        if (w) w.value = snapResolutionDim(widgetValue(w));
    });
    hookWidget(node, "height", () => {
        const w = widgetByName(node, "height");
        if (w) w.value = snapResolutionDim(widgetValue(w));
    });
    hookWidget(node, "confirm_first_pass", () => {
        syncRefineWidgetVisibility(node);
        scheduleCacheStatusRefresh(node, 0);
    });
    if (!node._mmxRefineOnWidgetChanged) {
        node._mmxRefineOnWidgetChanged = true;
        const prev = node.onWidgetChanged;
        node.onWidgetChanged = function (name, ...rest) {
            const r = prev?.apply(this, [name, ...rest]);
            if (name === "mode" || name === "upscale_method" || name === "aspect_ratio" || name === "megapixels" || name === "enable_tiling") {
                migrateRefineWidgets(this);
                syncRefineWidgetVisibility(this);
            }
            return r;
        };
    }
}

function refreshRefineNode(node) {
    if (!isRefineNode(node)) return;
    installRefineResolutionUI(node);
    migrateRefineWidgets(node);
    syncRefineWidgetVisibility(node);
    scheduleCacheStatusRefresh(node);
}

function refreshAllRefineNodes() {
    const graph = app.graph ?? app.canvas?.graph;
    for (const node of graph?._nodes ?? graph?.nodes ?? []) {
        refreshRefineNode(node);
    }
}

function scheduleRefineRefresh(node) {
    refreshRefineNode(node);
    queueMicrotask(() => refreshRefineNode(node));
    setTimeout(() => refreshRefineNode(node), 0);
    setTimeout(() => refreshRefineNode(node), 80);
    setTimeout(() => refreshRefineNode(node), 250);
}

app.registerExtension({
    name: "ComfyUI.MiniMaxH3DirectorRefine",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (DIRECTOR_CLASSES.has(nodeData?.name)) {
            const onWidgetChanged = nodeType.prototype.onWidgetChanged;
            nodeType.prototype.onWidgetChanged = function (...args) {
                const result = onWidgetChanged?.apply(this, args);
                refreshCacheStatusForDirector(this);
                return result;
            };
            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (...args) {
                const result = onConnectionsChange?.apply(this, args);
                refreshCacheStatusForDirector(this);
                return result;
            };
            return;
        }
        if (nodeData?.name !== REFINE_CLASS) return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const r = onNodeCreated?.apply(this, args);
            scheduleRefineRefresh(this);
            return r;
        };
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const r = onConfigure?.apply(this, args);
            scheduleRefineRefresh(this);
            return r;
        };
        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (...args) {
            const r = onConnectionsChange?.apply(this, args);
            syncRefineWidgetVisibility(this);
            scheduleCacheStatusRefresh(this);
            return r;
        };
    },
    nodeCreated(node) {
        const cls = node?.comfyClass || node?.type || "";
        if (DIRECTOR_CLASSES.has(cls)) {
            node._mmxRefreshFirstPassCache = (delay = 0) => {
                refreshCacheStatusForDirector(node, delay);
            };
            return;
        }
        scheduleRefineRefresh(node);
    },
    loadedGraphNode(node) {
        scheduleRefineRefresh(node);
    },
    afterConfigureGraph() {
        refreshAllRefineNodes();
        setTimeout(refreshAllRefineNodes, 100);
    },
});

api.addEventListener?.("executed", () => {
    for (const node of graphNodes()) {
        if (isRefineNode(node)) {
            scheduleCacheStatusRefresh(node, 250);
        }
    }
});
