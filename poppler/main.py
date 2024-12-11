from fastapi import FastAPI, File, UploadFile
import logging
import uvicorn
import torch

from process_pdf import process_pdf_file
from pydantic import BaseModel
from typing import Dict

def clear_torch_cache():
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

clear_torch_cache()

# Initialize the FastAPI application
app = FastAPI()


# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Schema(BaseModel):
    schema: Dict

# Endpoint to process uploaded files and schema
@app.post("/validate")
async def validate(file: UploadFile = File(...), schema: Schema = dict):
    return await process_pdf_file(file, schema)

# Main entry point for running the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)