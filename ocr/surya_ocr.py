import os
import time
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from io import BytesIO
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuration
detection_batch_size = 20
recognition_batch_size = 20
langs = ["en", "ta"]  # Supported languages
device = "cuda" if torch.cuda.is_available() else "cpu"

# Model variables (lazy-loaded)
det_processor, det_model, rec_model, rec_processor = None, None, None, None

def load_models_once():
    """
    Lazily load the models and ensure they are loaded only once.
    """
    global det_processor, det_model, rec_model, rec_processor
    if not all([det_processor, det_model, rec_model, rec_processor]):
        logger.info("Loading models...")
        det_processor, det_model = load_det_processor(), load_det_model()
        rec_model, rec_processor = load_rec_model(), load_rec_processor()
        
        # Move models to appropriate device (CPU or GPU)
        det_model.to(device)
        rec_model.to(device)
        logger.info("Models loaded successfully.")

def process_image(image, langs, det_model, det_processor, rec_model, rec_processor):
    """
    Run OCR on the provided image.
    """
    predictions = run_ocr(
        [image],
        [langs],
        det_model,
        det_processor,
        rec_model,
        rec_processor,
        detection_batch_size=detection_batch_size,
        recognition_batch_size=recognition_batch_size,
    )
    return predictions

@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """
    Endpoint to extract text from an uploaded image.
    """
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid image format. Only JPEG and PNG are supported.")
    
    try:
        # Open and resize the image
        image = Image.open(BytesIO(await file.read()))
        image.thumbnail((1024, 1024), Image.ANTIALIAS)  # Resize image to a maximum of 1024x1024
        
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file.")
    
    # Load models
    load_models_once()

    # Perform OCR
    start_time = time.time()
    predictions = process_image(image, langs, det_model, det_processor, rec_model, rec_processor)
    execution_time = time.time() - start_time
    logger.info("Execution time: %.2f seconds", execution_time)

    # Extract text from predictions
    ans = " ".join([each.text for each in predictions[0].text_lines])

    return JSONResponse(content={"extracted_text": ans, "execution_time": execution_time})

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)