import time
from pdf2image import convert_from_path
import torch
from torchvision import transforms
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import uvicorn
import os
import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

poppler_path = r"D:\Program Files\poppler-24.08.0\Library\bin"
dpi = 300  # Set the DPI value as needed
first_page = 1  # Set the first page number
last_page = 2  # Set the last page number

device = 'cuda' if torch.cuda.is_available() else 'cpu'
if torch.cuda.is_available():
    print("Using CUDA")
else:
    print("CUDA not available")

transform = transforms.ToTensor()

executor = ThreadPoolExecutor()

async def process_pdf_file(pdf_path: str):
    start_time = time.time()
    loop = asyncio.get_event_loop()
    images = await loop.run_in_executor(executor, convert_from_path, pdf_path, poppler_path, dpi, first_page, last_page)
    
    processed_images = []
    for i, image in enumerate(images):
        image_tensor = transform(image).to(device)
        image = transforms.ToPILImage()(image_tensor.cpu())
        output_path = f'page_{i+1}.png'
        await loop.run_in_executor(executor, image.save, output_path, 'PNG', 95)
        processed_images.append(output_path)
    
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time} seconds")
    
    return processed_images

@app.post("/process-pdf/")
async def process_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF files are allowed.")
    
    pdf_path = f"uploaded_{int(time.time())}.pdf"
    async with aiofiles.open(pdf_path, "wb") as f:
        await f.write(await file.read())
    
    processed_images = await process_pdf_file(pdf_path)
    
    return FileResponse(processed_images[0], media_type="image/png", filename="processed_image.png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
