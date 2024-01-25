The bounty to the amount of min(2*{number of pieces the method achieves}, 200) USD will be awarded to

1) The best solution (in terms of average pieces placed) received by the end of February 2024, tested on at least 10 games, which beats our prompting setup for either of those two models by at least 10 pieces placed.
2) If no solutions are sent by the end of February 2024, then the first solution sent to us after February 2024 which beats our best prompt by at least 10 pieces for one of those two models.

Some additional notes regarding the bounty:
- We expect to be able to reproduce your solution; if we're unable to obtain similar results to your reported ones, the solution will not count. Getting slightly worse results than you reported is okay.
- You shouldn't communicate anything about the state of the board within the textual part of the prompt, nor defer the strategy part to some other software and just instruct the model which moves to make. You also shouldn't write down such things as text on the image, though some text on there is okay, e.g. adding a coordinate system to the board, as long as it is part of a generalizable strategy to help the model see things better, rather doing some part of its visual recognition or reasoning for it. Common sense will be exercised; feel free to contact to ask us about your idea if you are unsure whether it qualifies.
- If you don't wish to share your solution publicly, please let us know, we'll comply with your desired infohazard procedures as long as we're able to verify the solution.
- Using models other than Gemini Pro Vision or GPT-4V does not count. You should use the API checkpoints we used if they are available (`gemini-pro-vision` and `gpt-4-vision-preview`), but if they're not available then the oldest available checkpoint of these models made available after our tests is fine.
- Payment options include: BTC/ETH, Paypal, and anywhere where it's easy to spend money from a credit card to send it.
