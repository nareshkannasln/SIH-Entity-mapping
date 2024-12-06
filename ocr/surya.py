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

# Deallocate additional resources allocated by PyTorch
torch.cuda.empty_cache()

# Reduce batch size (adjust based on your needs)
detection_batch_size = 20
recognition_batch_size = 20

langs = ["en", "ta"]  # Replace with your languages

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def load_models():
    det_processor, det_model = load_det_processor(), load_det_model()
    rec_model, rec_processor = load_rec_model(), load_rec_processor()
    return det_processor, det_model, rec_model, rec_processor

def process_image(image, langs, det_model, det_processor, rec_model, rec_processor):
    predictions = run_ocr([image], [langs], det_model, det_processor, rec_model, rec_processor, detection_batch_size=detection_batch_size, recognition_batch_size=recognition_batch_size)
    return predictions

det_processor, det_model, rec_model, rec_processor = load_models()

@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid image format. Only JPEG and PNG are supported.")
    
    try:
        image = Image.open(BytesIO(await file.read()))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file.")
    
    start_time = time.time()
    predictions = process_image(image, langs, det_model, det_processor, rec_model, rec_processor)
    ans = " ".join([each.text for each in predictions[0].text_lines])
    
    logger.info("Execution time: %s", time.time() - start_time)
    
    return JSONResponse(content={"extracted_text": ans})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)