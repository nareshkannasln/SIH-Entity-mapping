from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
import logging
import uvicorn
import time
from process_pdf_hook import process_pdf_file, set_update_webhook_func

# Initialize the FastAPI application
app = FastAPI()

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, webhook_id: str, websocket: WebSocket):
        await websocket.accept()
        logger.info(f"WebSocket connection established for webhook_id: {webhook_id}")
        if webhook_id not in self.connections:
            self.connections[webhook_id] = []
        self.connections[webhook_id].append(websocket)


    def disconnect(self, webhook_id: str, websocket: WebSocket):
        if webhook_id in self.connections:
            self.connections[webhook_id].remove(websocket)
            if not self.connections[webhook_id]:
                del self.connections[webhook_id]

    async def broadcast(self, webhook_id: str, message: str):
        if webhook_id in self.connections:
            for websocket in self.connections[webhook_id]:
                await websocket.send_text(message)

manager = ConnectionManager()
set_update_webhook_func(manager.broadcast)

# WebSocket endpoint
@app.websocket("/ws/{webhook_id}")
async def websocket_endpoint(webhook_id: str, websocket: WebSocket):
    await manager.connect(webhook_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep the connection alive
    except WebSocketDisconnect:
        manager.disconnect(webhook_id, websocket)

# Override the update_webhook_data function to use WebSocket broadcasting
async def update_webhook_data(webhook_id: str, message: str):
    """Send real-time updates through WebSocket."""
    logger.info(f"Update for {webhook_id}: {message}")
    await manager.broadcast(webhook_id, message)

# Endpoint to process uploaded files
@app.post("/validate")
async def validate(file: UploadFile = File(...)):
    # Generate a webhook_id for this upload
    webhook_id = f"webhook_{int(time.time())}"
    
    # Process the uploaded PDF file
    # You should replace this with the actual logic that processes the file
    await process_pdf_file(file, webhook_id)
    
    # Return the webhook_id so the frontend can connect via WebSocket
    return {"message": "File uploaded and being processed", "webhook_id": webhook_id}

# Main entry point for running the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
