from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
import uvicorn
from process_pdf_hook import process_file_via_websocket

# Initialize the FastAPI application
app = FastAPI()

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket endpoint to process files
@app.websocket("/process")
async def process_pdf_via_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await process_file_via_websocket(websocket)
    except WebSocketDisconnect:
        logger.error("WebSocket connection closed unexpectedly.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)