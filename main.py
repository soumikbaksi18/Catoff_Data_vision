from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import easyocr
from PIL import Image
import io

# Initialize FastAPI app
app = FastAPI()

# Initialize OCR Reader
reader = easyocr.Reader(['en'])  # Using EasyOCR

# Function to process image and extract statistics
def extract_match_stats(image: Image.Image):
    # Convert image to text using EasyOCR or pytesseract
    text = reader.readtext(image)

    # Example: Extracting specific statistics by pattern matching
    stats = {
        'player_goals': 0,
        'player_passes': 0,
        'player_fouls': 0,
        'player_offsides': 0,
        'player_yellow_cards': 0,
        'player_red_cards': 0,
        'opponent_goals': 0,
        'opponent_passes': 0,
        'opponent_fouls': 0,
        'opponent_offsides': 0,
        'opponent_yellow_cards': 0,
        'opponent_red_cards': 0
    }
    
    # Example logic to process the extracted text
    for detection in text:
        # Match and process keywords to populate stats (simplified example)
        detected_text = detection[1].lower()
        if "goal" in detected_text:
            if "player" in detected_text:
                stats['player_goals'] += 1
            else:
                stats['opponent_goals'] += 1
        elif "pass" in detected_text:
            if "player" in detected_text:
                stats['player_passes'] += 1
            else:
                stats['opponent_passes'] += 1
        elif "foul" in detected_text:
            if "player" in detected_text:
                stats['player_fouls'] += 1
            else:
                stats['opponent_fouls'] += 1
        elif "offside" in detected_text:
            if "player" in detected_text:
                stats['player_offsides'] += 1
            else:
                stats['opponent_offsides'] += 1
        elif "yellow card" in detected_text:
            if "player" in detected_text:
                stats['player_yellow_cards'] += 1
            else:
                stats['opponent_yellow_cards'] += 1
        elif "red card" in detected_text:
            if "player" in detected_text:
                stats['player_red_cards'] += 1
            else:
                stats['opponent_red_cards'] += 1

    return stats

# Endpoint to upload image and process it
@app.post("/upload_match_stats/")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Read the uploaded image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))

        # Extract stats from the image
        stats = extract_match_stats(image)

        # Return the extracted stats
        return JSONResponse(content={"stats": stats})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
