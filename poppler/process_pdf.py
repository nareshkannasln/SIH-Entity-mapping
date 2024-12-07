import time
from pdf2image import convert_from_path
import torch
from torchvision import transforms
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import asyncio
from concurrent.futures import ThreadPoolExecutor

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
