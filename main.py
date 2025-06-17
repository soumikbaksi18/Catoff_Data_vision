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
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image_np = np.array(image)

        # Restrict OCR to only top 15% of the image (heading area)
        h = image_np.shape[0]
        heading_area = image_np[:int(h*0.18), :, :]  # you can tweak the 0.18 if needed

        results = reader.readtext(heading_area)
        # Sort and extract top lines as before
        results_sorted = sorted(
            results, key=lambda r: (r[0][1][1] - r[0][0][1]) * (r[0][2][0] - r[0][0][0]), reverse=True)
        candidate_lines = [r[1] for r in results_sorted[:3]]

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
