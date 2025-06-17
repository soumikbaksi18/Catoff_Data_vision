from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import easyocr
import numpy as np
from PIL import Image
import io
import re

app = FastAPI()
reader = easyocr.Reader(['en'])

FIELDS = [
    ("possession_pct", r"Possession\s*%?\s*[:\-]?\s*(\d+)"),
    ("shots", r"Shots\s*[:\-]?\s*(\d+)"),
    ("expected_goals", r"Expected\s*Goals?\s*[:\-]?\s*([\d\.,]+)"),
    ("passes", r"Passes\s*[:\-]?\s*(\d+)"),
    ("tackles", r"Tackles\s*[:\-]?\s*(\d+)"),
    ("tackles_won", r"Tackles\s*Won\s*[:\-]?\s*(\d+)"),
    ("interceptions", r"Interceptions\s*[:\-]?\s*(\d+)"),
    ("saves", r"Saves\s*[:\-]?\s*(\d+)"),
    ("fouls_committed", r"Fouls?\s*Committed\s*[:\-]?\s*(\d+)"),
    ("offsides", r"Offsides?\s*[:\-]?\s*(\d+)"),
    ("corners", r"Corners?\s*[:\-]?\s*(\d+)"),
    ("free_kicks", r"Free\s*Kicks?\s*[:\-]?\s*(\d+)"),
    ("penalty_kicks", r"Penalty\s*Kicks?\s*[:\-]?\s*(\d+)"),
    ("yellow_cards", r"Yellow\s*Cards?\s*[:\-]?\s*(\d+)"),
    ("red_cards", r"Red\s*Cards?\s*[:\-]?\s*(\d+)"),
    ("dribble_success_rate", r"Dribble\s*Success\s*Rate\s*[:\-]?\s*(\d+)%"),
    ("shot_accuracy", r"Shot\s*Accuracy\s*[:\-]?\s*(\d+)%"),
    ("pass_accuracy", r"Pass\s*Accuracy\s*[:\-]?\s*(\d+)%"),
]

@app.post("/upload-scorecard/")
async def upload_scorecard(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image_np = np.array(image)

        results = reader.readtext(image_np, detail=0)
        ocr_text = "\n".join(results)
        print("\n--- OCR Results ---\n", ocr_text, "\n--- END OCR ---\n")

        teams, score = extract_teams_and_score(ocr_text)
        player_stats, opponent_stats = extract_stats(ocr_text)

        player_stats["team"] = teams[0]
        player_stats["score"] = score[0]
        opponent_stats["team"] = teams[1]
        opponent_stats["score"] = score[1]

        scorecard_data = {
            "Player_Data": player_stats,
            "Opponent_Data": opponent_stats
        }

        return JSONResponse(content={
            "scorecard_data": scorecard_data,
            "ocr_text": ocr_text   # For debug, you can remove this in prod
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def extract_teams_and_score(text):
    # Try to find: "ARGENTINA 4 - 0 BRAZIL"
    team_score_pattern = re.compile(r"([A-Z]+)\s+(\d+)[^\d]+(\d+)\s+([A-Z]+)")
    match = team_score_pattern.search(text.replace("\n", " "))
    if match:
        team1, score1, score2, team2 = match.groups()
        return [team1.lower(), team2.lower()], [int(score1), int(score2)]
    # Fallback
    return ["team1", "team2"], [0, 0]

def extract_stats(text):
    # Split lines, try to separate player/opponent by order
    lines = [line for line in text.split("\n") if line.strip()]
    mid = len(lines) // 2
    left_block = "\n".join(lines[:mid])
    right_block = "\n".join(lines[mid:])

    player_stats = extract_stats_from_block(left_block)
    opponent_stats = extract_stats_from_block(right_block)
    return player_stats, opponent_stats

def extract_stats_from_block(block):
    stats = {}
    for key, pattern in FIELDS:
        match = re.search(pattern, block, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", ".")
            if "." in value:
                stats[key] = float(value)
            else:
                stats[key] = int(value)
        else:
            stats[key] = 0
    return stats

# To run: uvicorn main:app --reload
