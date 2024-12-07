app = FastAPI()

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