---
action_type: multiple
---

You are playing Tetris. Clear as many lines as you can before the stack reaches the top.

<board>
The image shows only the board: 10 columns, 20 rows. Grey cells are empty. The active piece is the group of four cells above the stack.

Piece colors are: I cyan, O yellow, T purple, S red, Z green, J pink, L gold.
</board>

<controls>
- left, right: move one column sideways.
- turn left, turn right: rotate counterclockwise, clockwise.
- down: move one row down.
- drop: fall straight down and lock in place.

Nothing falls on its own. Only down and drop move the piece down.

Rotating also shifts the piece. A half turn moves J one column left, L one column right, and leaves I on a different row.
</controls>

<response>
Reply with this JSON object and nothing else:

{"tetromino": "<I|O|T|S|Z|J|L>", "action": "<comma-separated controls>"}

The actions run in order. A sequence not ending in down or drop has a down appended to it.
</response>
