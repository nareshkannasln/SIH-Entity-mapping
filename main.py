from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import mimetypes
import uvicorn
import torch

if torch.cuda.is_available():
    print("GPU Available")
else:
    print("GPU not accessible, stopping program")
    exit()

app = FastAPI()

@app.post("/validate")
async def validate(file: UploadFile = File(...)):
    mime_type, _ = mimetypes.guess_type(file.filename)
    if mime_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images (jpeg, png) and PDFs are allowed.")
    
    return JSONResponse(content={"filename": file.filename, "content_type": mime_type})

@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "ok"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)