import aiofiles
import time
from fastapi import File, UploadFile, HTTPException
import httpx
import os
import logging
from PIL import Image
import shutil
from pdf2image import convert_from_path
from torchvision import transforms
import concurrent.futures
from typing import Callable

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to Poppler for PDF to image conversion
poppler_path = r"C:\Program Files\Release-24.08.0-0\poppler-24.08.0\Library\bin"

# Directory for storing processed images
IMAGES_DIR = os.path.normpath("E:/Project/SIH 2024 I/NER/SIH-Entity-mapping/poppler/images")

# Clear images directory
def clear_images_directory():
    if os.path.exists(IMAGES_DIR):
        shutil.rmtree(IMAGES_DIR)
    os.makedirs(IMAGES_DIR)

clear_images_directory()

# Dynamically import `update_webhook_data` from `main.py`
update_webhook_data: Callable[[str, str], None] = None  # Define as a placeholder

def set_update_webhook_func(func: Callable[[str, str], None]):
    """Set the WebSocket update function dynamically."""
    global update_webhook_data
    update_webhook_data = func

# Save uploaded files
async def save_file(file: UploadFile, extension: str) -> str:
    file_path = os.path.join(IMAGES_DIR, f"uploaded_{int(time.time())}.{extension}")
    file.file.seek(0)

    if extension in ["png", "jpg", "jpeg"]:
        try:
            image = Image.open(file.file)
            image.verify()  # Verify the integrity of the image
            image = Image.open(file.file)
            image.save(file_path, format=extension.upper() if extension != "jpg" else "JPEG")
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
    else:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(await file.read())

    logger.info(f"File saved at {file_path}")
    return file_path

# Extract text from an image using an external OCR API
async def extract_text_from_image(image_path: str) -> dict:
    async with aiofiles.open(image_path, "rb") as f:
        image_data = await f.read()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"http://localhost:8001/extract-text",
                files={"file": (os.path.basename(image_path), image_data, "image/png")}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API Error: {e.response.text}")
            raise HTTPException(status_code=500, detail="Text extraction API failed")

# Convert PDF to images
async def convert_pdf_to_images(pdf_path: str) -> list:
    images = convert_from_path(pdf_path, poppler_path=poppler_path, dpi=200)
    transform = transforms.ToTensor()

    def process_image(i, image):
        image_tensor = transform(image)
        output_image = transforms.ToPILImage()(image_tensor.cpu())
        image_path = os.path.join(IMAGES_DIR, f"page_{i + 1}.png")
        output_image.save(image_path, quality=95)
        return image_path

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_image, i, image) for i, image in enumerate(images)]
        processed_images = [future.result() for future in concurrent.futures.as_completed(futures)]

    return processed_images

# Process PDF file
async def process_pdf_file(file: UploadFile, webhook_id: str):
    try:
        if update_webhook_data is None:
            raise RuntimeError("update_webhook_data function is not set.")

        # Step 1: Save the file
        if file.content_type == "application/pdf":
            pdf_path = await save_file(file, "pdf")
            await update_webhook_data(webhook_id, "PDF saved, converting to images...")

            # Step 2: Convert PDF to images
            processed_images = await convert_pdf_to_images(pdf_path)
            await update_webhook_data(webhook_id, f"Converted {len(processed_images)} images from the PDF.")

            # Step 3: Extract text from images
            extracted_texts = []
            for i, image_path in enumerate(processed_images):
                await update_webhook_data(webhook_id, f"Processing image {i + 1}...")
                text = await extract_text_from_image(image_path)
                extracted_texts.append(text.get("extracted_text", ""))
                await update_webhook_data(webhook_id, f"Extracted text from image {i + 1}.")

            combined_text = "\n\n".join(extracted_texts)
            await update_webhook_data(webhook_id, "Text extraction completed. Sending data for processing...")

            # Step 4: Send extracted text for further processing
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8002/process-data",
                    json={"raw_text": combined_text}
                )
                if response.status_code == 200:
                    await update_webhook_data(webhook_id, "Data processing completed successfully!")
                else:
                    await update_webhook_data(webhook_id, "Data processing failed.")
        else:
            await update_webhook_data(webhook_id, "Unsupported file format.")
            raise HTTPException(status_code=400, detail="Invalid file format.")
    except Exception as e:
        await update_webhook_data(webhook_id, f"Error: {str(e)}")
        logger.error(f"Error processing file: {e}")
    finally:
        # Clean up temporary files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        for image_path in processed_images:
            if os.path.exists(image_path):
                os.remove(image_path)
