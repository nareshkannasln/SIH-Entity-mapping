from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
from gemma import extract_entity
import uvicorn
from load_loader import load_model
# import torch

# if torch.cuda.is_available():
#     print("GPU Available")
# else:
#     print("GPU not accessible, stopping program")
#     exit()

model = load_model()
print(f"Model loaded successfully\nModel Ref: {model}")

app = FastAPI()

request_id = 1

@app.post("/process-data")
async def process_data(request: Request):
    try:
        global request_id
        print(f"Request received {request_id}")

        data = await request.json()
        schema = data.get("schema")
        raw_text = data.get("raw_text")

        # Check if schema is a valid JSON
        try:
            json.loads(json.dumps(schema))
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid JSON format for schema")

        # Call the extract_entity function from gemma.py
        result = await extract_entity(schema, raw_text, model)

        # return StreamingResponse(result, media_type="application/json")
        return {"result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        request_id += 1

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)