from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import easyocr
import numpy as np
from PIL import Image, ImageEnhance
import io
import re

app = FastAPI()
reader = easyocr.Reader(['en'])

@app.post("/upload-scorecard/")
async def upload_scorecard(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        # Enhance contrast for better OCR
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.5)
        image_np = np.array(image)

        # Get OCR results with bounding box and text
        results = reader.readtext(image_np)
        # Filter for largest text (scoreboard is usually the largest text)
        results_sorted = sorted(results, key=lambda r: (r[0][1][1] - r[0][0][1]) * (r[0][2][0] - r[0][0][0]), reverse=True)
        candidate_lines = [r[1] for r in results_sorted[:3]]  # Top 3 largest text boxes

        print("OCR Candidate Lines:", candidate_lines)

        player_team, player_goals, opponent_team, opponent_goals = extract_teams_and_scores_from_lines(candidate_lines)

        response = {
            "Player_Team": player_team,
            "Player_Goals": player_goals,
            "Opponent_Team": opponent_team,
            "Opponent_Goals": opponent_goals
        }

        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_teams_and_scores_from_lines(lines):
    # Try to join all candidate lines in case OCR split "ARGENTINA 4 : 0 BRAZIL" into multiple boxes
    full_line = " ".join(lines)
    # Remove non-ASCII except colon/dash/space
    clean = re.sub(r"[^A-Za-z0-9:\-\s]", "", full_line)
    print("Cleaned header line:", clean)
    # Robust matching for common separators and OCR quirks (I for :, | for : etc)
    match = re.search(
        r"([A-Z]+)\s+(\d+)\s*[:\-\|Iil]\s*(\d+)\s+([A-Z]+)", clean
    )
    if match:
        player_team = match.group(1).title()
        player_goals = int(match.group(2))
        opponent_goals = int(match.group(3))
        opponent_team = match.group(4).title()
        return player_team, player_goals, opponent_team, opponent_goals
    # Fallback: Try (team num num team)
    match = re.search(r"([A-Z]+)\s+(\d+)\s+(\d+)\s+([A-Z]+)", clean)
    if match:
        player_team = match.group(1).title()
        player_goals = int(match.group(2))
        opponent_goals = int(match.group(3))
        opponent_team = match.group(4).title()
        return player_team, player_goals, opponent_team, opponent_goals
    # Final fallback
    return "Team1", 0, "Team2", 0

# To run: uvicorn main:app --reload
