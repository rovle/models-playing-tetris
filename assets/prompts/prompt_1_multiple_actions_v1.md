---
action_type: multiple
---

You will be given an image of a Tetris board with a game in progress. The board is represented by a grid of 10 columns and 20 rows. The empty cells are grey while the Tetrominoes come in a variety of colors: green, yellow, red, cyan, orange, purple, and pink. The game starts with a random Tetromino falling from the top of the board. You can move the falling Tetromino left, right or down, or rotate it clockwise or counterclockwise. You can also drop the Tetromino immediately to the bottom.

When a complete row of blocks is formed, it disappears and the blocks above it fall down. Points are scored for each row that is cleared. The game ends when the blocks reach the top of the board.

Your goal is to play Tetris and achieve the highest possible score by maximizing cleared lines and minimizing block gaps.

The possible moves are: "left", "right", "down", "drop", "rotate clockwise", and "rotate counterclockwise".

You should first determine which Tetromino is currently falling, then analyze the board, the arrangement of the current blocks and where the current tetromino would best slot in. After that you are to give a sequence of moves ending with "drop".

Structure your response as a JSON, so as {"tetromino": TETROMINO, "board_state": BOARD_STATE, "move_analysis": MOVE_ANALYSIS, "action": ACTIONS} where TETROMINO is the type of the falling tetromino ("I", "J", "L", "O", "S", "T", "Z"), BOARD_STATE is your analysis of the current state of the board, MOVE_ANALYSIS is your analysis of which moves are best to take, and ACTIONS is the comma-separated list of chosen moves; all values in the JSON should be strings. Do not add any more keys to the JSON. Your response should start with { and end with }.
