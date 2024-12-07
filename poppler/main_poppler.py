from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import aiofiles
import time
import os
import zipfile
from process_pdf import process_pdf_file

app = FastAPI()

@app.post("/process-pdf/")
async def process_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF files are allowed.")
    
    pdf_path = f"uploaded_{int(time.time())}.pdf"
    async with aiofiles.open(pdf_path, "wb") as f:
        await f.write(await file.read())
    
    processed_images = await process_pdf_file(pdf_path)
    
    zip_filename = f"processed_images_{int(time.time())}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for idx, image_path in enumerate(processed_images):
            zipf.write(image_path, os.path.basename(image_path))
    
    return FileResponse(zip_filename, media_type="application/zip", filename=zip_filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
