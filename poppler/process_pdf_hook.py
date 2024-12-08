import aiofiles
import time
import os
import logging
import shutil
from pdf2image import convert_from_path
import concurrent.futures
from fastapi import HTTPException, WebSocket
import asyncio
import httpx

schema = {
    "name": "String, Avoid prefix or suffix denotations but Initial should be included",
    "date_of_birth": "Date Format (DD-MM-YYYY) Date format should be in numbers",
    "degree": "String",
    "cgpa": "Float",
    "percentage": "Float",
    "class": "String, Class of the candidate(Such as First Class, Second Class, etc.)"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

poppler_path = r"C:\Program Files\Release-24.08.0-0\poppler-24.08.0\Library\bin"

# Define the directory to save images
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

ocr_server = "localhost"
llm_server = "localhost"

# Clear images directory
def clear_images_directory():
    if os.path.exists(IMAGES_DIR):
        shutil.rmtree(IMAGES_DIR)
    os.makedirs(IMAGES_DIR)

clear_images_directory()

# Save uploaded file
async def save_file(file, extension: str) -> str:
    file_path = os.path.join(IMAGES_DIR, f"uploaded_{int(time.time())}.{extension}")
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file)
    return file_path

# Extract text with timeout
async def extract_text_with_timeout(image_path: str, timeout: int = 30) -> str:
    with open(image_path, "rb") as f:
        image_data = f.read()

    url = f"http://{ocr_server}:8001/extract-text"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, files={"file": (os.path.basename(image_path), image_data, "image/png")}, timeout=timeout)
            response_data = response.json()
            return response_data
        except httpx.TimeoutException:
            logger.error("Text extraction request timed out.")
            raise HTTPException(status_code=504, detail="Text extraction request timed out.")
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to text extraction API.")
async def convert_pdf_to_images(pdf_path: str) -> list:
    images = convert_from_path(pdf_path, dpi=200)
    image_paths = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(lambda img, idx: _save_image(img, idx), image, i)
            for i, image in enumerate(images)
        ]
        image_paths = [future.result() for future in concurrent.futures.as_completed(futures)]
    return image_paths

def _save_image(image, idx):
    image_path = os.path.join(IMAGES_DIR, f'page_{idx + 1}.png')
    image.save(image_path, format="PNG", quality=95)
    return image_path

# Process file via WebSocket
async def process_file_via_websocket(websocket: WebSocket):
    processed_images = []
    pdf_path = None
    try:
        await websocket.send_json({"status": "started", "message": "Processing started."})

        # Receive the file
        file_bytes = await websocket.receive_bytes()
        pdf_path = await save_file(file_bytes, "pdf")

        # Convert PDF to images
        await websocket.send_json({"status": "processing", "message": "Converting PDF to images."})
        processed_images = await convert_pdf_to_images(pdf_path)

        # Extract text from images
        extracted_texts = []
        for image_path in processed_images:
            try:
                text_data = await extract_text_with_timeout(image_path)
                extracted_texts.append(text_data.get("extracted_text", ""))
            except HTTPException as e:
                await websocket.send_json({"status": "failed", "message": e.detail})
                return

        combined_text = "\n\n".join(extracted_texts)
        await websocket.send_json({"status": "processing", "message": "Text extracted from images."})

        # Send text to LLM server
        async with httpx.AsyncClient() as client:
            try:
                response = await asyncio.wait_for(
                    client.post(
                        f"http://{llm_server}:8002/process-data",
                        json={"raw_text": combined_text, "schema": schema}
                    ),
                    timeout=30
                )
                response.raise_for_status()
                await websocket.send_json({
                    "status": "completed",
                    "message": "Data processed successfully.",
                    "data": response.json()
                })
            except asyncio.TimeoutError:
                logger.error("LLM data processing request timed out.")
                await websocket.send_json({"status": "failed", "message": "LLM processing timed out."})
            except httpx.RequestError as e:
                logger.error(f"LLM processing request error: {e}")
                await websocket.send_json({"status": "failed", "message": "Failed to connect to LLM API."})
    finally:
        # Cleanup
        if processed_images:
            for path in processed_images:
                if os.path.exists(path):
                    os.remove(path)
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
