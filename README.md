# Mizuki-simulator

Rotation damage calculator for Yumemizuki Mizuki and the custom character roster
shipped with this repository.

## Run

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Manual

`user_manual.txt` (downloadable from **Team & Gear Setup → Save / Load Build**)
explains party setup, the rotation and trial editors, the results tab and the
build file format.

## Implementation notes

`text/Implementation_Backlog.md` tracks the game-mechanics status of every
character, weapon and artifact set. `text/How_to_add_hits.txt` documents how to
add a new ability or hit to the engine.

`streamlit_app.py` is only the entry point (page config, stylesheet, the four
tabs). The UI itself lives in `ui/`: `page.css` + `style.py` (stylesheet,
wallpaper and table styling), `constants.py` (option tables), `paths.py`
(repo-root anchors), `state.py` (session-state helpers), `table.py` (audit
table), `editors.py` (catalogue lookups), `cards.py` (character cards),
`build_panel.py` (save / load) and `tabs/` (one module per tab, each exposing
`render()`; tab 3 is split into `trial_runner.py` and `rotation_editors.py`).
