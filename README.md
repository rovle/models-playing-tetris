# README

## Development Setup Instructions

```python
# create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# install the dependencies
pip install -r requirements.txt

# Set API key in .env
cp .env.example .env
```

## Running the game

Run this files in separate terminals:

```bash
python gemini_side.py
python game.py
```

To save a video of the screenshots:

```bash
cd screens && ffmpeg -framerate 2 -i screenshot_%d.png -c:v libx264 -r 30 -pix_fmt yuv420p ../tetris.mp4
```
