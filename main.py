from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import easyocr
import numpy as np
from PIL import Image
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

        # --- Heading/Goals extraction (unchanged) ---
        h = image_np.shape[0]
        heading_area = image_np[:int(h*0.18), :, :]  # You can tweak the 0.18 if needed

        results = reader.readtext(heading_area)
        results_sorted = sorted(
            results, key=lambda r: (r[0][1][1] - r[0][0][1]) * (r[0][2][0] - r[0][0][0]), reverse=True)
        candidate_lines = [r[1] for r in results_sorted[:3]]

        print("OCR Candidate Lines:", candidate_lines)

        player_team, player_goals, opponent_team, opponent_goals = extract_teams_and_scores_from_lines(candidate_lines)

        # --- NEW: Only Shots, Passes, Tackles, Saves ---
        player_stats, opponent_stats = extract_selected_stats_from_image(image)

        response = {
            "Player_Team": player_team,
            "Player_Goals": player_goals,
            "Opponent_Team": opponent_team,
            "Opponent_Goals": opponent_goals,
            "Player_Stats": player_stats,
            "Opponent_Stats": opponent_stats
        }

        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_teams_and_scores_from_lines(lines):
    full_line = " ".join(lines)
    clean = re.sub(r"[^A-Za-z0-9:\-\s]", "", full_line)
    print("Cleaned header line:", clean)
    match = re.search(
        r"([A-Z]+)\s+(\d+)\s*[:\-\|Iil]\s*(\d+)\s+([A-Z]+)", clean
    )
    if match:
        player_team = match.group(1).title()
        player_goals = int(match.group(2))
        opponent_goals = int(match.group(3))
        opponent_team = match.group(4).title()
        return player_team, player_goals, opponent_team, opponent_goals
    match = re.search(r"([A-Z]+)\s+(\d+)\s+(\d+)\s+([A-Z]+)", clean)
    if match:
        player_team = match.group(1).title()
        player_goals = int(match.group(2))
        opponent_goals = int(match.group(3))
        opponent_team = match.group(4).title()
        return player_team, player_goals, opponent_team, opponent_goals
    return "Team1", 0, "Team2", 0


def extract_selected_stats_from_image(image):
    image_np = np.array(image)
    h = image_np.shape[0]
    stats_area = image_np[int(h*0.18):, :, :]
    results = reader.readtext(stats_area, detail=0)
    joined = "\n".join(results)
    lines = [
        l.strip().upper().replace("0", "O").replace("5", "S")
        for l in joined.split('\n') if l.strip()
    ]
    print("STATS OCR LINES:", lines)

    label_map = {
        "SHOTS": "Shots",
        "PASSES": "Passes",
        "TACKLES": "Tackles",
        "SAVES": "Saves"
    }
    player_stats = {}
    opponent_stats = {}

    for idx, line in enumerate(lines):
        for label, field_name in label_map.items():
            if line == label:
                try:
                    player_val = lines[idx - 1]
                    opponent_val = lines[idx + 1]
                    player_stats[field_name] = int(re.sub(r"\D", "", player_val)) if re.search(r"\d", player_val) else 0
                    opponent_stats[field_name] = int(re.sub(r"\D", "", opponent_val)) if re.search(r"\d", opponent_val) else 0
                except Exception:
                    player_stats[field_name] = 0
                    opponent_stats[field_name] = 0

    return player_stats, opponent_stats
