"""The trial editor: a port of the reference editor, driven by our engine.

  catalog.py    our registries, shaped for the UI (ids come from the registry keys)
  store.py      the session spec, seeded from the presets, plus cached simulations
  engine.py     spec -> our engine -> blocks / hits / totals (headless, testable)
  mutations.py  the only writer of the spec: CRUD and ordered-list edits, pure
  validate.py   pre-flight warnings: structure, party fit, window fit, cooldowns
  payloads.py   the strip payloads (trial / rotation / field sequence)
  strips.py     the vendored strip component and its intent accessors
  timings.py    the ability hit-timing table (draft, apply / reset / undo)
  results.py    the slim hit log, per-slot damage, the metrics and the rotation table
  screens.py    the three screens: Trial / Rotation / Field sequence
  publish.py    spec -> Trial/Rotation/FieldSequence objects for the runner pools
  importer.py   Trial/Rotation/FieldSequence objects -> spec entries (the inverse)
  view.py       the host: screen switch, error slot, one fragment

catalog / engine / mutations / validate / payloads / importer are plain Python, so
the smoke test drives them without Streamlit. store, publish, results, screens,
strips and view talk to it.
"""

from ui.editor.view import open_trial, render

__all__ = ["open_trial", "render"]
