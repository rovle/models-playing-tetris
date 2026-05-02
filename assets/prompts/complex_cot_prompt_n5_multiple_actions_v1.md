---
action_type: multiple
---

You will be given an image of a Tetris board with a game in progress. The board is represented by a grid of 10 columns and 20 rows. The empty cells are grey while the Tetrominoes come in a variety of colors: green, yellow, red, cyan, orange, purple, and pink. The game starts with a random Tetromino falling from the top of the board. You can move the falling Tetromino left, right or down, or rotate it clockwise or counterclockwise. You can also drop the Tetromino immediately to the bottom.

When a complete row of blocks is formed, it disappears and the blocks above it fall down. Points are scored for each row that is cleared. The game ends when the blocks reach the top of the board.

Your goal is to play Tetris and achieve the highest possible score by maximizing cleared lines and minimizing block gaps.

The possible moves are: "left", "right", "down", "drop", "rotate clockwise", and "rotate counterclockwise".

You should first determine which Tetromino is currently falling, then analyze the board, the arrangement of the current blocks and where the current tetromino would best slot in. You should then propose three sequences of moves, each ending with "drop", and provide analysis of each sequence. Finally you should provide the final analysis, and based on it choose one among those sequences.

Structure your response as a JSON, so as {"tetromino": TETROMINO, "board_state": BOARD_STATE, "preliminary_analysis": PRELIMINARY_ANALYSIS, "action_proposal_1" : ACTIONS, "analysis_of_actions_1" : MOVES_ANALYSIS, "action_proposal_2" : ACTIONS, "analysis_of_actions_2" : MOVES_ANALYSIS, "action_proposal_3" : ACTIONS, "analysis_of_actions_3" : MOVES_ANALYSIS, "final_analysis": FINAL_ANALYSIS, "action": ACTIONS_FINAL} where TETROMINO is the type of the falling tetromino ("I", "J", "L", "O", "S", "T", "Z"); BOARD_STATE is your analysis of the current state of the board; PRELIMINARY_ANALYSIS is the preliminary analysis of which moves might be the best; each ACTIONS a sequence of moves, each ending with "drop"; each MOVES_ANALYSIS is an analysis of the preceding moves; FINAL_ANALYSIS is the final analysis in which you decide for the sequence of moves; and ACTIONS_FINAL is the sequence of actions you have ultimately chosen; all values in the JSON should be strings. Do not add any more keys to the JSON. Your response should start with { and end with }.
