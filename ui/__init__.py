"""Streamlit UI package.

The app entry point (streamlit_app.py) only configures the page and dispatches the
four tabs; every widget, table and panel lives here.

  constants.py    option tables shared by the widgets and the save / load layer
  paths.py        repo-root anchors for assets and the user manual
  state.py        session-state helpers (tab jumps, toasts, cache invalidation)
  page.css        the page stylesheet (__WALLPAPER__ placeholder)
  style.py        stylesheet / wallpaper loader and audit-table styling
  table.py        event / audit table builder
  editors.py      catalogue lookups for the sequence / rotation / trial editors
  cards.py        character cards and talent validation
  build_panel.py  save / load build panel
  tabs/           one module per tab, each exposing render(); tab 3 is split into
                  trial_runner.py (selection + run) and rotation_editors.py
                  (the [Advanced] editors)

Modules are side-effect free at import time: the entry point must be able to call
st.set_page_config() before any page content exists.
"""
