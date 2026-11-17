"""The one non-native widget: a zoomable, draggable strip.

Vendored from the reference editor (Trial Editor/ui/timeline.py) and trimmed to
what this engine produces - no buff lanes, no crit marker. Python still decides
what to draw: a flat payload of rows plus absolutely positioned items. The JS
draws that payload and emits intents; it never keeps a model of its own.

Intents, read back with event():
    select   {"kind", "id", "t"}      a band, hit or marker was clicked
    moved    {"kind", "id", "value"}  a draggable band was dropped at "value"
    retimed  {"value"}               the swap-out handle was dragged
    seek     {"t"}                   the ruler was scrubbed

Every intent needs a callback: pass a no-op rather than None for the ones a
screen does not use, or the component will not mount.
"""

from __future__ import annotations

import streamlit as st

TIMELINE_KEY = "editor_strip"
RULER_H = 22
ROW_H = 24
ROW_GAP = 2
BOTTOM_PAD = 6

HTML = """
<div class="tl">
  <div class="labels">
    <div class="lbl-spacer"></div>
    <div class="lbl-list"></div>
  </div>
  <div class="scroll">
    <div class="canvas">
      <div class="ruler"></div>
      <div class="rows"></div>
      <div class="cursor"></div>
    </div>
  </div>
</div>
"""


CSS = """
.tl {
  /* The strip is an iframe: the page :root variables do not reach it, so the app
     palette is repeated here (ui/page.css: --page-ink / --page-panel / --page-edge). */
  --strip-ink: #0e1117;
  --strip-panel: #1a2130;
  --strip-edge: rgba(255, 255, 255, 0.08);
  --strip-text: #e8ecf2;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 8px 10px 6px;
  background: var(--strip-ink);
  border: 1px solid var(--strip-edge);
  border-radius: 12px;
  color: var(--strip-text);
  font-family: var(--st-font, inherit);
  user-select: none;
}

.labels { flex: 0 0 134px; }
.lbl-spacer { height: 22px; border-bottom: 1px solid var(--strip-edge); }
.lbl {
  height: 24px;
  margin-bottom: 2px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  line-height: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  padding-right: 6px;
}
.lbl.buff { color: var(--st-text-color); opacity: 0.75; font-size: 10px; padding-left: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 8px; }
.scroll { flex: 1 1 auto; min-width: 0; overflow-x: auto; overflow-y: hidden; padding-bottom: 2px; }
.canvas { position: relative; }
.ruler {
  position: relative;
  height: 22px;
  border-bottom: 1px solid var(--strip-edge);
  cursor: crosshair;
}
.tick { position: absolute; top: 0; bottom: 0; border-left: 1px solid var(--strip-edge); }
.tick.minor { top: 15px; }
.tick span {
  position: absolute;
  left: 3px;
  top: 4px;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  opacity: 0.7;
}
.rows { position: relative; }
.rowbg { position: absolute; left: 0; right: 0; border-radius: 3px; }
.rowbg.alt { background: var(--strip-panel); opacity: 0.55; }
.band {
  position: absolute;
  border-radius: 3px;
  font-size: 10px;
  line-height: 1;
  display: flex;
  align-items: center;
  padding: 0 4px;
  white-space: nowrap;
  color: #10131a;
  font-weight: 600;
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.18);
  /* A band is the runtime of what it draws, not the point of interest: it stays
     behind its own hit ticks so the ticks are never swallowed by it. */
  z-index: 1;
}
.band .bl {
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* A zero-span ability (single hit) has no room for a label inside it. */
.band .bl.out {
  position: absolute;
  left: calc(100% + 5px);
  top: 0;
  max-width: 150px;
  color: var(--st-text-color);
  font-weight: 500;
  text-shadow: none;
}
.band.draggable { cursor: grab; }
.band.draggable:active { cursor: grabbing; }
.band.locked { cursor: pointer; }
.band.soft { opacity: 0.55; }
.band.dim { opacity: 0.35; }
.band.selected { outline: 2px solid var(--st-primary-color, #7aa2f7); outline-offset: 1px; }
.band .tail {
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  background-image: repeating-linear-gradient(
    45deg, rgba(0, 0, 0, 0.22) 0 3px, transparent 3px 6px
  );
}
.hit {
  position: absolute;
  width: 4px;
  border-radius: 1px;
  cursor: pointer;
  box-sizing: border-box;
  z-index: 2;
}
.hit.crit { width: 6px; }
.hit.off { opacity: 0.4; border: 1px solid currentColor; background: transparent !important; }
.hit.dim { opacity: 0.3; }
.hit.selected { outline: 1px solid var(--st-primary-color, #7aa2f7); outline-offset: 1px; z-index: 4; }
.seg { position: absolute; height: 8px; border-radius: 4px; cursor: default; }
.seg span {
  position: absolute;
  left: 3px;
  top: -7px;
  font-size: 8px;
  opacity: 0.8;
  white-space: nowrap;
}
.marker { position: absolute; top: 0; bottom: 0; width: 0; border-left: 1px dashed; z-index: 2; }
.marker span {
  position: absolute;
  left: 3px;
  top: -1px;
  font-size: 9px;
  padding: 0 2px;
  background: var(--st-background-color);
  white-space: nowrap;
  opacity: 0.85;
}
.marker.out { border-color: var(--st-red-color); }
.marker.in { border-color: var(--st-green-color); }
.marker.seam { border-color: var(--st-primary-color); border-left-style: solid; }
.marker.end { border-color: var(--st-border-color); }
.handle {
  position: absolute;
  top: -3px;
  left: -5px;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: var(--st-red-color);
  cursor: ew-resize;
}
.cursor { position: absolute; width: 0; border-left: 1.5px solid var(--st-primary-color); z-index: 5; pointer-events: none; }
.cursor::before {
  content: "";
  position: absolute;
  left: -4px;
  top: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid var(--st-primary-color);
}
.empty { padding: 18px 8px; font-size: 12px; opacity: 0.6; }
"""


JS = """
const ROW_H = 24, ROW_GAP = 2, RULER_H = 22, PAD = 10, SNAP = 0.05;
// One geometry for every strip: a band is the runtime of whatever it draws, and a
// hit is a tick that pokes out of it top and bottom, so ticks are never swallowed.
const BAND_H = 20, HIT_H = 22;

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
function round(v, d) { const m = Math.pow(10, d); return Math.round(v * m) / m; }
function niceStep(px) {
  const c = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300];
  for (const s of c) if (s * px >= 56) return s;
  return 600;
}
function fmtT(t) {
  if (t >= 60) {
    const m = Math.floor(t / 60), s = Math.round(t % 60);
    return m + ":" + String(s).padStart(2, "0");
  }
  return (Math.round(t * 10) / 10) + "s";
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector(".tl");
  if (!root) return;

  const p = data || {};
  const rows = p.rows || [];
  const items = p.items || [];
  const tMax = Math.max(p.tMax || 1, 0.5);

  const labelsEl = root.querySelector(".lbl-list");
  const scrollEl = root.querySelector(".scroll");
  const canvasEl = root.querySelector(".canvas");
  const rulerEl = root.querySelector(".ruler");
  const rowsEl = root.querySelector(".rows");
  const cursorEl = root.querySelector(".cursor");

  const avail = Math.max(scrollEl.clientWidth || 680, 260);
  let px = p.pxPerSec > 0 ? p.pxPerSec : (avail - 2 * PAD) / tMax;
  px = Math.max(px, 2);
  const X = (t) => PAD + t * px;

  const tops = {};
  let y = 0;
  rows.forEach((r) => { tops[r.id] = y; y += ROW_H + ROW_GAP; });
  const rowsH = Math.max(y - ROW_GAP, 0);

  canvasEl.style.width = Math.ceil(X(tMax) + PAD) + "px";
  canvasEl.style.height = RULER_H + rowsH + "px";

  // ---- labels -----------------------------------------------------------
  labelsEl.innerHTML = rows.map((r) =>
    '<div class="lbl ' + (r.kind === "buff" ? "buff" : "") + '" title="' + esc(r.label) + '">' +
    '<span class="dot" style="background:' + (r.color || "transparent") + '"></span>' +
    '<span>' + esc(r.label) + '</span></div>'
  ).join("");

  // ---- ruler ------------------------------------------------------------
  const step = niceStep(px);
  let ruler = "";
  for (let t = 0; t <= tMax + 1e-9; t += step) {
    ruler += '<div class="tick" style="left:' + X(t) + 'px"><span>' + fmtT(t) + '</span></div>';
    for (let k = 1; k < 5; k++) {
      const tt = t + (step * k) / 5;
      if (tt > tMax) break;
      ruler += '<div class="tick minor" style="left:' + X(tt) + 'px"></div>';
    }
  }
  rulerEl.innerHTML = ruler;
  rulerEl.onclick = (e) => {
    const rect = rulerEl.getBoundingClientRect();
    setTriggerValue("seek", { t: round(clamp((e.clientX - rect.left - PAD) / px, 0, tMax), 2) });
  };

  // ---- rows + items -----------------------------------------------------
  let out = "";
  rows.forEach((r, i) => {
    // A faint wash of the owner colour, so a lane reads as whose time on field it
    // is, without competing with the bands and ticks drawn on top of it.
    const tint = r.kind === "lane" && r.color
      ? "background:" + r.color + ";opacity:0.10"
      : "";
    out += '<div class="rowbg ' + (i % 2 ? "alt" : "") + '" style="top:' + tops[r.id] +
           'px;height:' + ROW_H + 'px;' + tint + '"></div>';
  });


  items.forEach((it) => {
    const rowTop = tops[it.row];
    if (rowTop === undefined) return;

    if (it.kind === "band") {
      const left = X(it.start);
      // A single-hit ability has no span, so give the draggable bar a grab-able
      // minimum width and move the label outside it.
      const w = Math.max(it.minPx || 3, X(it.end) - left);
      const cls = ["band", it.draggable ? "draggable" : "locked", it.dim ? "dim" : "",
                   it.soft ? "soft" : "", it.selected ? "selected" : ""].join(" ");
      const top = rowTop + (ROW_H - BAND_H) / 2;
      let inner = (w > 46 ? '<span class="bl">' : '<span class="bl out">') + esc(it.label) + '</span>';
      if (it.tailFrom != null && it.tailFrom < it.end) {
        const off = Math.max(0, (it.tailFrom - it.start) * px);
        inner += '<div class="tail" style="left:' + off + 'px"></div>';
      }
      out += '<div class="' + cls + '" data-id="' + esc(it.id) + '" data-ref="' + esc(it.refKind) +
             '" data-start="' + it.start + '" data-draggable="' + (it.draggable ? 1 : 0) + '"' +
             ' title="' + esc(it.title || it.label) + '"' +
             ' style="left:' + left + 'px;width:' + w + 'px;top:' + top +
             'px;height:' + BAND_H + 'px;background:' + it.color + '">' + inner + '</div>';
    } else if (it.kind === "hit") {
      const cls = ["hit", it.crit ? "crit" : "", it.off ? "off" : "",
                   it.dim ? "dim" : "", it.selected ? "selected" : ""].join(" ");
      out += '<div class="' + cls + '" data-id="' + esc(it.id) + '" data-t="' + it.t + '"' +
             ' title="' + esc(it.title || "") + '"' +
             ' style="left:' + (X(it.t) - 2 + (it.dx || 0)) + 'px;top:' +
             (rowTop + (ROW_H - HIT_H) / 2) + 'px;height:' + HIT_H + 'px;' +
             'background:' + it.color + ';color:' + it.color + '"></div>';
    } else if (it.kind === "seg") {
      const w = Math.max(2, X(it.end) - X(it.start));
      out += '<div class="seg" title="' + esc(it.title || "") + '"' +
             ' style="left:' + X(it.start) + 'px;width:' + w + 'px;top:' + (rowTop + 8) +
             'px;background:' + it.color + ';opacity:' + (0.3 + 0.2 * (it.stacks || 1)) + '"></div>';
    } else if (it.kind === "marker") {
      out += '<div class="marker ' + (it.kind2 || "") + '" data-t="' + it.t + '"' +
             ' style="left:' + X(it.t) + 'px;top:0;height:' + rowsH + 'px">' +
             '<span>' + esc(it.label) + '</span>' +
             (it.draggable ? '<div class="handle" title="Drag to change field time"></div>' : "") +
             '</div>';
    }
  });

  rowsEl.innerHTML = out;
  if (!rows.length) rowsEl.innerHTML = '<div class="empty">Nothing to draw yet.</div>';

  // ---- cursor -----------------------------------------------------------
  if (p.cursor == null) {
    cursorEl.style.display = "none";
  } else {
    cursorEl.style.display = "block";
    cursorEl.style.left = X(p.cursor) + "px";
    cursorEl.style.top = RULER_H + "px";
    cursorEl.style.height = rowsH + "px";
  }

  // ---- drag: ability bands (moves the first hit only) --------------------
  rowsEl.querySelectorAll('.band[data-draggable="1"]').forEach((el) => {
    el.onpointerdown = (e) => {
      e.preventDefault();
      el.setPointerCapture(e.pointerId);
      const startX = e.clientX;
      const startVal = parseFloat(el.dataset.start);
      el.onpointermove = (ev) => {
        el.style.transform = "translateX(" + (ev.clientX - startX) + "px)";
        el.style.zIndex = "6";
        el.style.opacity = "0.85";
      };
      el.onpointerup = (ev) => {
        const dx = ev.clientX - startX;
        el.onpointermove = null;
        el.onpointerup = null;
        el.style.transform = "";
        el.style.zIndex = "";
        el.style.opacity = "";
        if (Math.abs(dx) > 3) {
          const raw = startVal + dx / px;
          const val = round(Math.max(0, ev.altKey ? raw : Math.round(raw / SNAP) * SNAP), 2);
          setTriggerValue("moved", { kind: el.dataset.ref, id: el.dataset.id, value: val });
        } else {
          setTriggerValue("select", { kind: el.dataset.ref, id: el.dataset.id, t: startVal });
        }
      };
    };
  });

  // ---- drag: swap-out handle (changes field time) ------------------------
  rowsEl.querySelectorAll(".marker .handle").forEach((el) => {
    el.onpointerdown = (e) => {
      e.preventDefault();
      e.stopPropagation();
      el.setPointerCapture(e.pointerId);
      const marker = el.closest(".marker");
      const startX = e.clientX;
      const startVal = parseFloat(marker.dataset.t);
      el.onpointermove = (ev) => {
        marker.style.transform = "translateX(" + (ev.clientX - startX) + "px)";
      };
      el.onpointerup = (ev) => {
        const dx = ev.clientX - startX;
        el.onpointermove = null;
        el.onpointerup = null;
        marker.style.transform = "";
        const raw = Math.max(0.5, startVal + dx / px);
        setTriggerValue("retimed", {
          value: round(ev.altKey ? raw : Math.round(raw / 0.1) * 0.1, 2),
        });
      };
    };
  });

  // ---- click: hits and locked bands -------------------------------------
  rowsEl.querySelectorAll(".hit").forEach((el) => {
    el.onclick = () => setTriggerValue("select", {
      kind: "hit",
      id: el.dataset.id,
      t: parseFloat(el.dataset.t),
    });
  });
  rowsEl.querySelectorAll('.band[data-draggable="0"]').forEach((el) => {
    el.onclick = () => setTriggerValue("select", {
      kind: el.dataset.ref,
      id: el.dataset.id,
      t: parseFloat(el.dataset.start),
    });
  });
}
"""

# Registered exactly once, at import time (re-registering inside a function that
# runs per instance logs warnings and can swap the definition under you).


TIMELINE = st.components.v2.component("editor_strip", html=HTML, css=CSS, js=JS)


def strip_height(n_rows: int) -> int:
    # +24 keeps the horizontal scrollbar and its gutter inside the frame.
    return RULER_H + max(n_rows, 1) * (ROW_H + ROW_GAP) + BOTTOM_PAD + 38


def render(payload: dict, *, key: str = TIMELINE_KEY, on_select=None,
           on_moved=None, on_retimed=None, on_seek=None):
    """Mount the strip. Unused intents still need a callback: pass a no-op."""
    return TIMELINE(
        key=key,
        data=payload,
        height=strip_height(len(payload.get("rows", []))),
        on_select_change=on_select or (lambda: None),
        on_moved_change=on_moved or (lambda: None),
        on_retimed_change=on_retimed or (lambda: None),
        on_seek_change=on_seek or (lambda: None),
    )


def event(name: str, key: str = TIMELINE_KEY):
    """The latest intent *name* from the mounted strip, or None.

    Streamlit exposes component triggers as attributes on the component state,
    so this is the read side of the contract in the module docstring.
    """
    state = st.session_state.get(key)
    if state is None:
        return None
    payload = getattr(state, name, None)
    return payload if isinstance(payload, dict) else None

