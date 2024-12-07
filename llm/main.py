from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
from gemma import extract_entity
import uvicorn

app = FastAPI()

@app.post("/extract_entity")
async def process_data(request: Request):
    try:
        data = await request.json()
        schema = data.get("schema")
        raw_text = data.get("raw_text")

        # Check if schema is a valid JSON
        try:
            json.loads(json.dumps(schema))
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid JSON format for schema")

        # Call the extract_entity function from gemma.py
        result = extract_entity(schema, raw_text)

        # Stream the response
        async def response_generator():
            for chunk in result:
                yield chunk

        return StreamingResponse(response_generator(), media_type="application/json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)