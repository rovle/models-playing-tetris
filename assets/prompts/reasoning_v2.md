---
action_type: multiple
---

You are playing Tetris. Each turn you receive a board screenshot and must choose the next action sequence for the active piece.

Reading the board accurately is the single biggest determinant of good play. As the board fills, it becomes easy to miss filled cells, overlook covered holes, or miscount columns.

Objective: Clear full rows. This requires keeping the stack low and free of covered holes.

<board>
A 10x20 grid. Columns 0-9 left to right; rows 0-19 with row 0 at the top, row 19 at the floor. Coordinates are written as (column, row) throughout.
The active piece is the topmost four-cell block above the stack — its cells have no support beneath them.
</board>

<actions>
- left / right: shift one column horizontally.
- down: soft-drop one row.
- drop: hard-drop straight down and lock the piece.
- turn left / turn right: rotate counterclockwise / clockwise.

Auto-drop: after any action the piece falls one row, unless the action was "down" or "drop". Lateral moves and rotations consume vertical distance.
</actions>

<requirements>
Your placement must satisfy these checks; if any fails, revise:
- Board read consistent across columns and rows
- All covered holes catalogued as (column, row)
- Active piece identified by shape, at known cells (column, row)
- Move count consistent with target column (verified two ways: arithmetic and step-by-step trace)
- Final placement creates zero new holes (or fewest possible)
</requirements>

<output_format>
Use thinking for analysis. Your final visible response must contain only the JSON object below:
{"tetromino": "<I|O|T|S|Z|J|L>", "action": "<comma-separated moves>"}
Example: {"tetromino": "L", "action": "left, left, turn left, drop"}
</output_format>
