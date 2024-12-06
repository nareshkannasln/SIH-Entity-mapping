from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from langchain_ollama import OllamaLLM  # Updated import for Ollama
import json

app = FastAPI()

# Initialize Llama 3.1 model from Ollama
llm = OllamaLLM(model="gemma2:9b", temperature=0)

# Define the prompt template for JSON validation
template = """
You are a wonderful entity extraction and translation model. You are given a JSON input and a raw text. You need to extract the values from the raw text based on the keys provided in the JSON input. The keys in the JSON input are as follows:

Identify the corresponding value in the raw text and extract the value. The value is a string that follows the key in the raw text.
Try possible variations of the key to extract the value. For example, if the key is "name", try extracting the value using "name", "Name", "NAME", etc.
Transform the extracted value to the correct data type. For example, if the key is "total_mark", the value should be transformed to a number.
Output the result as an array with the extracted values in the order of the keys in the JSON input.
Try translating the raw text to English to check if the raw text is in a different language.
If value for the key is not found, output ''(this is the string with 0 length) for that index.

Translation Requirements:
If any of the field not found in english, then try tranlating the native language to english and extract the value.
If value obtained via this cases, the translated value should be returned.
Note: This is optional, if entity already obtained in english, no need to translate.

Input:
JSON Input: {}

Raw Text: {}

Document Type: 
- marksheet
- community_certificate
- transfer_certificate
- bonafide_certificate
- other

Strict Instructions:
- Output only the array result.
- Ensure the output adheres strictly to array formatting, with no additional characters outside the array structure.
- Include the type of the document in the 0th index of the array.
- Do not include any debugging information in the output.
- Maintain the order of values for each keys in the JSON for the array result.
- Your output should only start from '[' and end with ']'.

Exact output format:
{}

Output the trsnalated value for the key "name" in the raw text.
Array should only contain english translated value for the key.
Translations should be perfect and no errors should be there.
"""

@app.post("/entity")
async def entity_extraction(request: Request):
    data = await request.json()

    # Validate required fields
    if 'json_input' not in data or 'raw_text' not in data or 'document_type' not in data:
        raise HTTPException(status_code=400, detail="Missing required fields: 'json_input', 'raw_text', 'document_type'")

    json_input = data['json_input']
    raw_text = data['raw_text']
    document_type = data['document_type']

    # Validate JSON input format
    if not isinstance(json_input, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON input format. It should be a dictionary.")

    # Format the prompt with the input data
    array_schema = [f"Obtained {key} here" for key in json_input.keys()]
    formatted_prompt = template.format(json_input, raw_text, [document_type] + array_schema)

    # Stream the result
    async def generate():
        result = llm.stream(formatted_prompt)
        async for chunk in result:
            yield chunk

    return StreamingResponse(generate(), media_type='text/plain')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
