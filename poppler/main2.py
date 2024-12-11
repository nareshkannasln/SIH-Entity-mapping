from fastapi import FastAPI, File, UploadFile, Form
import logging
import uvicorn
import torch

from process_pdf2 import process_pdf_file
from fastapi.responses import JSONResponse

def clear_torch_cache():
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

clear_torch_cache()

# Initialize the FastAPI application
app = FastAPI()


prompt_schema = {
    "birth_certificate": {
        "name": "String",
        "date_of_birth": "Date Format (DD-MM-YYYY)"
    },
    "degree_certificate": {
        "name": "String",
        "university": "String",
        "date_of_birth": "Date Format (DD-MM-YYYY)",
        "degree": "String",
        "cgpa": "Float",
        "percentage": "Float",
        "class": "String",
        "qualification_degree": "String"
    },
    "proof_of_class": {
        "name": "String",
        "class": "String"
    },
    "provisional_certificate": {
        "name": "String",
        "degree": "String",
        "university": "String",
        "passing_year": "Number",
        "qualification_degree": "String"
    },
    "experience_certificate": {
        "from_date": "String (YYYY-MM-DD)",
        "to_date": "String (YYYY-MM-DD)"
    },
    "gate_score_card": {
        "name": "String",
        "year": "Number",
        "marks": "Number",
        "rank": "Number"
    },
    "proof_of_category": {
        "name": "String",
        "category": "String"
    },
    "proof_of_address": {
        "name": "String",
        "address": "String"
    },
    "phd_certificate": {
        "name": "String",
        "university": "String",
        "Date_of_reg": "String (YYYY-MM-DD)",
        "title_of_project": "String",
        "no_of_papers_published": "Integer",
        "no_of_conference_attended": "Integer"
    }
}

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_extracted_to_list(extracted_string):
    """
    Convert the extracted entity mapping output from a string to a list.

    Args:
        extracted_string (str): The extracted output in string format.

    Returns:
        list: The extracted output as a list.
    """
    try:
        return eval(extracted_string)
    except Exception as e:
        raise ValueError(f"Error converting extracted string to list: {e}")
    
@app.post("/validate")
async def validate(
    file: UploadFile = File(...),
    schema: str = Form(...)
):

    if schema is None or schema not in prompt_schema:
        return JSONResponse(content={"error": "Schema is required"}, status_code=400)
    
    schema = prompt_schema[schema]
    index = 1
    llm_result = await process_pdf_file(file, schema)
    entity_values = convert_extracted_to_list(llm_result['result'])
    # print(entity_values)
    # for entity, value in schema.items():
    #     if entity_values[index] == input(f"Enter value for {entity}: "):
    #         print("Value matched")
    #     else:
    #         print(f"Value mismatched, extracted value is {entity_values[index]}")
    #     index += 1
            
    return JSONResponse(content={}, status_code=200)

# Main entry point for running the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
