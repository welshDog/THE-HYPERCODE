# 🚀 Suggested "Good First Issues"

Here are some ready-to-go tasks for new contributors. If you're looking for a way to help, grab one of these!

---

## 1. 🧬 Implement Linear Map View for Failed Assemblies
**Labels:** `good-first-issue`, `enhancement`, `frontend`

**Context:**
Currently, the `CompilerPanel` only renders a circular plasmid map when assembly succeeds. When it fails (e.g., mismatched overhangs), users just see a text log. We need a "Linear View" to visualize the broken chain and gaps.

**Task:**
1. Open `hyperflow-editor/src/components/CompilerPanel.tsx`.
2. Locate the `renderPlasmidMap` function.
3. Create a new function `renderLinearMap` (or similar) that draws the parts in a straight line.
4. Visualize gaps/mismatches clearly (e.g., red "X" or "GAP" block).
5. Render this view when `result.isCircular` is `false`.

**Code Pointers:**
- [CompilerPanel.tsx](../../hyperflow-editor/src/components/CompilerPanel.tsx)
- Check `result.parts` data shape from the simulator.

---

## 2. 🐍 Verify Golden Gate Data Shape & isCircular Logic
**Labels:** `good-first-issue`, `backend`, `help-wanted`

**Context:**
The backend simulator now returns structured data for plasmid maps. We need to ensure the `isCircular` logic covers all edge cases (e.g., self-ligating parts, multiple fragments) and that the `parts` list contains all necessary metadata for the frontend.

**Task:**
1. Open `hypercode-core/hypercode/simulator.py`.
2. Review the `simulate_goldengate` function.
3. Verify that `isCircular` is correctly set for 3+ part assemblies.
4. Ensure `parts` list includes `start`, `end`, `overhangs`, and `color` (if available).
5. Add a unit test in `tests/test_golden_gate.py` for a 3-part circular assembly.

**Code Pointers:**
- [simulator.py](../../hypercode-core/hypercode/simulator.py)
- [test_golden_gate.py](../../hypercode-core/tests/test_golden_gate.py)

---

## 3. 📝 Tweak Visual Editor Spec for "Failed Assembly" State
**Labels:** `good-first-issue`, `documentation`

**Context:**
We are adding a "Failed Assembly" view, but it's not fully specified in our design docs. We need to update the visual editor spec to include this state.

**Task:**
1. Locate (or create if missing) `hyperflow-editor/docs/visual_editor_spec.md`.
2. Add a section "Assembly Result States".
3. Describe the "Success" state (Circular Map).
4. Describe the "Failure" state (Linear Map with Gaps).
5. Include a rough ASCII sketch or description of the UI.

**Code Pointers:**
- [visual_editor_spec.md](../../hyperflow-editor/docs/visual_editor_spec.md) (Create if missing)
