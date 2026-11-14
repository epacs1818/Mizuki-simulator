"""The one non-native widget: a zoomable, draggable timeline.

Built with Streamlit Custom Components v2 (`st.components.v2.component`), inline
HTML/CSS/JS - no npm, no build step, no separate frontend package.

Contract (the part worth copying into your own variants)
-------------------------------------------------------
* Python sends a **flattened render payload** (`data=`): rows + absolutely
  positioned items + a cursor. Python decides *what* to draw; JS only draws it.
* JS emits **intents** as triggers, never as a running model:
    - `select`   {kind, id, t}      a band, tick or marker was clicked
    - `moved`    {kind, id, value}  a draggable band was dropped (new start)
    - `retimed`  {value}            the swap-out handle was dropped (field time)
* Python applies those intents inside the `on_*_change` callback (callbacks run
  before the script body, so mutating the store there is always legal), then
  re-renders the payload on the next run. Streamlit's round-trip is too slow for
  live recompute mid-drag, so JS moves the DOM locally and only commits on drop.
"""

from __future__ import annotations

import streamlit as st

TIMELINE_KEY = "timeline"
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
  display: flex;
  align-items: flex-start;
  font-family: var(--st-font);
  color: var(--st-text-color);
  user-select: none;
}
.labels { flex: 0 0 134px; }
.lbl-spacer { height: 22px; border-bottom: 1px solid var(--st-border-color-light); }
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
  border-bottom: 1px solid var(--st-border-color-light);
  cursor: crosshair;
}
.tick { position: absolute; top: 0; bottom: 0; border-left: 1px solid var(--st-border-color-light); }
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
.rowbg.alt { background: var(--st-secondary-background-color); opacity: 0.45; }
.band {
  position: absolute;
  border-radius: 3px;
  font-size: 10px;
  line-height: 14px;
  padding: 0 4px;
  white-space: nowrap;
  color: #10131a;
  font-weight: 600;
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.18);
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
.band.dim { opacity: 0.35; }
.band.selected { outline: 2px solid var(--st-primary-color); outline-offset: 1px; }
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
}
.hit.crit { width: 6px; }
.hit.off { opacity: 0.4; border: 1px solid currentColor; background: transparent !important; }
.hit.dim { opacity: 0.3; }
.hit.selected { outline: 1px solid var(--st-primary-color); outline-offset: 1px; z-index: 4; }
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
    out += '<div class="rowbg ' + (i % 2 ? "alt" : "") + '" style="top:' + tops[r.id] +
           'px;height:' + ROW_H + 'px"></div>';
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
                   it.selected ? "selected" : ""].join(" ");
      let inner = (w > 46 ? '<span class="bl">' : '<span class="bl out">') + esc(it.label) + '</span>';
      if (it.tailFrom != null && it.tailFrom < it.end) {
        const off = Math.max(0, (it.tailFrom - it.start) * px);
        inner += '<div class="tail" style="left:' + off + 'px"></div>';
      }
      out += '<div class="' + cls + '" data-id="' + esc(it.id) + '" data-ref="' + esc(it.refKind) +
             '" data-start="' + it.start + '" data-draggable="' + (it.draggable ? 1 : 0) + '"' +
             ' title="' + esc(it.title || it.label) + '"' +
             ' style="left:' + left + 'px;width:' + w + 'px;top:' + (rowTop + 5) +
             'px;background:' + it.color + '">' + inner + '</div>';
    } else if (it.kind === "hit") {
      const cls = ["hit", it.crit ? "crit" : "", it.off ? "off" : "",
                   it.dim ? "dim" : "", it.selected ? "selected" : ""].join(" ");
      out += '<div class="' + cls + '" data-id="' + esc(it.id) + '" data-t="' + it.t + '"' +
             ' title="' + esc(it.title || "") + '"' +
             ' style="left:' + (X(it.t) - 2 + (it.dx || 0)) + 'px;top:' + (rowTop + 4) + 'px;height:16px;' +
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
TIMELINE = st.components.v2.component("sim_timeline", html=HTML, css=CSS, js=JS)


def timeline_height(n_rows: int) -> int:
    # +24 covers the horizontal scrollbar the strip may need.
    return RULER_H + max(n_rows, 1) * (ROW_H + ROW_GAP) + BOTTOM_PAD + 24


def render(
    payload: dict,
    *,
    key: str = TIMELINE_KEY,
    on_select=None,
    on_moved=None,
    on_retimed=None,
    on_seek=None,
):
    """Mount the timeline. Every `on_*` callback is required to exist as a
    trigger key, so pass no-ops rather than None for the ones you don't use."""
    return TIMELINE(
        key=key,
        data=payload,
        height=timeline_height(len(payload.get("rows", []))),
        on_select_change=on_select or (lambda: None),
        on_moved_change=on_moved or (lambda: None),
        on_retimed_change=on_retimed or (lambda: None),
        on_seek_change=on_seek or (lambda: None),
    )


# --------------------------------------------------------------------------
# Payload builders: Python decides *what* to draw, JS only draws it.
# --------------------------------------------------------------------------


def _buff_rows(spec: dict) -> list[dict]:
    return [
        {"id": f"b_{bid}", "label": buff["name"], "kind": "buff", "color": buff["color"]}
        for bid, buff in spec["catalog"]["buffs"].items()
    ]


def _stagger(items: list[dict]) -> list[dict]:
    """Nudge apart hits that share a row and a timestamp.

    Multi-component hits (and Odette's standard + Stellar pairs) land at the
    same instant, so without this one tick hides the other.
    """
    groups: dict[tuple, list[dict]] = {}
    for item in items:
        if item.get("kind") == "hit":
            groups.setdefault((item["row"], round(item["t"], 6)), []).append(item)

    for group in groups.values():
        if len(group) < 2:
            continue
        span = len(group) - 1
        for index, item in enumerate(group):
            item["dx"] = round((index - span / 2) * 3.2, 2)
            item["title"] = f"{item.get('title', '')} · {index + 1}/{len(group)}"
    return items


def trial_payload(
    spec: dict,
    result: dict,
    *,
    cursor: float | None = None,
    selected: tuple | None = None,
    px_per_sec: float = 0.0,
) -> dict:
    chars = spec["catalog"]["characters"]
    buffs = spec["catalog"]["buffs"]

    rows = [{"id": f"c_{cid}", "label": c["name"], "kind": "lane", "color": c["color"]} for cid, c in chars.items()]
    rows += _buff_rows(spec)

    items: list[dict] = []
    duration = result["totals"]["duration"]
    for block in result["blocks"]:
        # Fully truncated blocks live past the trial window; drawing them would
        # only stretch the axis into empty space. Partially overrunning bands
        # still render (and visibly run off the end of the ruler).
        if duration > 0 and block["start"] > duration + 1e-9:
            continue
        c = chars[block["character"]]
        items.append(
            {
                "kind": "band",
                "row": f"c_{block['character']}",
                "id": block["id"],
                "refKind": "block",
                "start": block["start"],
                "end": block["end"],
                "label": "",
                "title": (
                    f"{block['rotation_name']} / {c['name']}  "
                    f"{block['start']:.2f}s → {block['end']:.2f}s "
                    f"({block['end'] - block['start']:.2f}s)"
                ),
                "color": c["color"],
                "draggable": False,
                "dim": block["beyond"],
                "selected": selected == ("block", block["id"]),
            }
        )

    for hit in result["hits"]:
        c = chars[hit["character"]]
        items.append(
            {
                "kind": "hit",
                "row": f"c_{hit['character']}",
                "id": hit["ability"],
                "t": hit["t"],
                "color": c["color"],
                "crit": hit["crit"],
                "off": not hit["on_field"],
                "selected": selected is not None
                and selected[0] == "hit"
                and abs(selected[1] - hit["t"]) < 1e-6,
                "title": f"{hit['ability_name']} #{hit['hit_index'] + 1} · {hit['damage']:,.0f} · {hit['t']:.2f}s",
            }
        )

    for seg in result["buffs"]:
        buff = buffs[seg["buff"]]
        items.append(
            {
                "kind": "seg",
                "row": f"b_{seg['buff']}",
                "start": seg["start"],
                "end": seg["end"],
                "stacks": seg["stacks"],
                "color": buff["color"],
                "title": f"{buff['name']} x{seg['stacks']}  {seg['start']:.2f}s → {seg['end']:.2f}s",
            }
        )

    return {
        "tMax": max(result["totals"]["duration"], 1.0),
        "rows": rows,
        "items": _stagger(items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }


def field_sequence_payload(
    spec: dict,
    fs_id: str,
    *,
    cursor: float | None = None,
    selected: tuple | None = None,
    px_per_sec: float = 0.0,
) -> dict:
    """Focus-mode payload: one row per placement, plus the swap markers.

    The axis ends just past the swap-out, so the field time fills the strip at
    maximum zoom; anything resolving later is drawn beyond the scroll edge.
    Abilities only - buffs belong to the trial and rotation strips.
    """
    cat = spec["catalog"]
    chars, abilities = cat["characters"], cat["abilities"]
    fs = spec["field_seqs"][fs_id]
    color = chars[fs["character"]]["color"]
    field_time = float(fs["field_time"])

    rows: list[dict] = []
    items: list[dict] = []

    for placement in fs["placements"]:
        ability = abilities.get(placement["ability"])
        if ability is None:
            continue
        row_id = f"p_{placement['id']}"
        rows.append({"id": row_id, "label": ability["name"], "kind": "lane", "color": color})

        first = float(placement["first_hit"])
        last = max((h["offset"] for h in ability["hits"]), default=0.0)
        end = first + last

        residual = sum(1 for h in ability["hits"] if first + h["offset"] > field_time + 1e-9)
        items.append(
            {
                "kind": "band",
                "row": row_id,
                "id": placement["id"],
                "refKind": "placement",
                "start": first,
                "end": end,
                "label": ability["name"],
                "title": (
                    f"{ability['name']}  first hit {first:.2f}s, last hit {end:.2f}s  — drag to move"
                ),
                "color": color,
                "draggable": True,
                "dim": False,
                "minPx": 14,
                "tailFrom": field_time if residual else None,
                "selected": selected == ("placement", placement["id"]),
            }
        )

        for i, hit in enumerate(ability["hits"]):
            when = first + hit["offset"]
            late = when > field_time + 1e-9
            items.append(
                {
                    "kind": "hit",
                    "row": row_id,
                    "id": ability["id"],
                    "t": when,
                    "color": color,
                    "crit": hit["crit"],
                    "off": late,
                    "selected": False,
                    "title": f"hit #{i + 1} · {when:.2f}s",
                }
            )

    items.append({"kind": "marker", "t": 0.0, "label": "swap in", "kind2": "in", "draggable": False})
    items.append(
        {
            "kind": "marker",
            "t": field_time,
            "label": f"swap out {field_time:.1f}s",
            "kind2": "out",
            "draggable": True,
        }
    )

    return {
        "tMax": max(field_time, 1.0) * 1.05,
        "rows": rows,
        "items": _stagger(items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }


def _first_loop(preview: dict) -> tuple[list[dict], list[dict]]:
    """The preview simulates the rotation twice; the strip draws one loop.

    Hits are matched through their block id, so a loop-1 cast that resolves after
    the loop end is still part of loop 1 - that is the tail, not the repeat.
    """
    blocks = preview.get("blocks") or []
    if not blocks:
        return [], []
    first_rep = blocks[0]["repeat_index"]
    keep = [block for block in blocks if block["repeat_index"] == first_rep]
    ids = {block["id"] for block in keep}
    return keep, [hit for hit in preview["hits"] if hit["block"] in ids]


def rotation_payload(
    spec: dict,
    rotation_id: str,
    preview: dict,
    *,
    cursor: float | None = None,
    selected: tuple | None = None,
    px_per_sec: float = 0.0,
    loops: int = 1,
    tail: float = 0.0,
) -> dict:
    """One loop of a rotation, plus whatever resolves after it ends.

    The preview is simulated for two loops (so the seam is the engine's answer,
    not a guess), but only the first loop is drawn. Anything a loop-1 cast
    resolves past the loop end still belongs to loop 1 and stays visible in the
    tail; the repeat itself is not drawn.
    """
    cat = spec["catalog"]
    chars, buffs = cat["characters"], cat["buffs"]
    rotation = spec["rotations"][rotation_id]
    loop_time = sum(
        float(spec["field_seqs"][b]["field_time"]) for b in rotation["blocks"] if b in spec["field_seqs"]
    )

    rows = [{"id": f"c_{cid}", "label": c["name"], "kind": "lane", "color": c["color"]} for cid, c in chars.items()]

    blocks, hits = _first_loop(preview)
    items: list[dict] = []
    for block in blocks:
        c = chars[block["character"]]
        fs = spec["field_seqs"].get(block["field_seq"], {})
        items.append(
            {
                "kind": "band",
                "row": f"c_{block['character']}",
                "id": block["id"],
                "refKind": "block",
                "start": block["start"],
                "end": block["end"],
                "label": "",
                "title": (
                    f"block {block['id'].split('~')[-1]} · {fs.get('name', block['field_seq'])} · "
                    f"{c['name']}  {block['start']:.2f}s → {block['end']:.2f}s"
                ),
                "color": c["color"],
                "draggable": False,
                "selected": selected == ("block", block["id"]),
            }
        )

    for hit in hits:
        c = chars[hit["character"]]
        items.append(
            {
                "kind": "hit",
                "row": f"c_{hit['character']}",
                "id": hit["ability"],
                "t": hit["t"],
                "color": c["color"],
                "crit": hit["crit"],
                "off": not hit["on_field"],
                "selected": selected is not None
                and selected[0] == "hit"
                and abs(selected[1] - hit["t"]) < 1e-6,
                "title": f"{hit['ability_name']} #{hit['hit_index'] + 1} · {hit['damage']:,.0f} · {hit['t']:.2f}s",
            }
        )

    for seg in preview["buffs"]:
        # Segments that only start in the repeat belong to the loop we are not drawing.
        if loop_time > 0 and seg["start"] >= loop_time - 1e-9:
            continue
        buff = buffs[seg["buff"]]
        items.append(
            {
                "kind": "seg",
                "row": f"b_{seg['buff']}",
                "start": seg["start"],
                "end": seg["end"],
                "stacks": seg["stacks"],
                "color": buff["color"],
                "title": f"{buff['name']} x{seg['stacks']}  {seg['start']:.2f}s → {seg['end']:.2f}s",
            }
        )

    rows += _buff_rows(spec)

    if loop_time > 0:
        items.append({"kind": "marker", "t": 0.0, "label": "loop start", "kind2": "in", "draggable": False})
        items.append(
            {"kind": "marker", "t": loop_time, "label": f"loop end {loop_time:.1f}s", "kind2": "seam", "draggable": False}
        )
        for n in range(1, loops):
            items.append(
                {
                    "kind": "marker",
                    "t": loop_time * (n + 1),
                    "label": "loop end",
                    "kind2": "end",
                    "draggable": False,
                }
            )

    return {
        "tMax": max(loop_time * loops + tail, 1.0),
        "rows": rows,
        "items": _stagger(items),
        "cursor": cursor,
        "pxPerSec": px_per_sec,
    }



