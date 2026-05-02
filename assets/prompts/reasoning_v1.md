---
action_type: multiple
---

You are playing Tetris. Each turn you receive a board screenshot and must choose the next action sequence for the active piece.

Reading the board accurately is the single biggest determinant of good play. As the board fills, it becomes easy to miss filled cells, overlook covered holes, or miscount columns. The methodology below grounds your analysis before you commit.

<board>
A 10x20 grid. Columns 0-9 left to right; rows 0-19 with row 0 at the top, row 19 at the floor. Coordinates are written as (column, row) throughout.
Pieces: I, O, T, S, Z, J, L.
</board>

<actions>
- left / right: shift one column horizontally.
- down: soft-drop one row.
- drop: hard-drop straight down and lock the piece.
- turn left / turn right: rotate counterclockwise / clockwise.

Auto-drop: after any action the piece falls one row, unless the action was "down" or "drop". Lateral moves and rotations consume vertical distance.
</actions>

<methodology>
Objective: clear full rows. This requires keeping the stack low and free of covered holes.

Before answering, work through these steps:

1. Read the stack two ways and confirm they agree:
   - by column: for each column 0-9, the topmost filled row index (or "empty").
   - by row: from the topmost non-empty row downward, which columns are filled.
   If they disagree on any column, look once more and resolve.

2. List every covered hole (an empty cell with a filled cell above it in the same column) as (column, row).

3. Identify the active piece by its shape (the four occupied cells). Note the piece's cells as (column, row).

4. Pick a target placement: among 2-3 candidates, choose the one that creates zero new holes and minimizes max column height. If all candidates create holes, pick the fewest.

5. Compute the move count two ways and confirm they agree:
   - by arithmetic: target_column − current_column.
   - by tracing: walk each step and confirm arrival without overshoot.
   If they disagree, recompute the arithmetic.
   Add rotations for the target orientation.
</methodology>

<output_format>
Output ONLY this JSON, nothing else: {"tetromino": "<I|O|T|S|Z|J|L>", "action": "<comma-separated moves>"}
</output_format>
