from fastapi import FastAPI, Form, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from PIL import Image
import time
import logging
from pymongo import MongoClient
from surya.ocr import run_ocr  # Ensure the OCR functionality is imported properly
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
import torch

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for front-end connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific front-end URL for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"  # Replace with your MongoDB URI
DB_NAME = "Applicant_Details"
APPLICATION_COLLECTION = "Applicant_data"
UPLOAD_COLLECTION = "uploads"

# Initialize MongoDB client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
application_collection = db[APPLICATION_COLLECTION]
upload_collection = db[UPLOAD_COLLECTION]

# Directory to save uploaded files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Model variables (lazy-loaded)
det_processor, det_model, rec_model, rec_processor = None, None, None, None

# Configuration
detection_batch_size = 30
recognition_batch_size = 30
langs = ["en", "ta"]  # Supported languages
device = "cuda"  # Use GPU if available
device = torch.device("cuda")

if not torch.cuda.is_available():
    print("GPU not available, stopping programming")
    # exit()

# Load models function (load only once)
def load_models_once():
    global det_processor, det_model, rec_model, rec_processor
    if not all([det_processor, det_model, rec_model, rec_processor]):
        logger.info("Loading models...")
        det_processor, det_model = load_det_processor(), load_det_model()
        rec_model, rec_processor = load_rec_model(), load_rec_processor()

        # Move models to appropriate device (CPU or GPU)
        det_model.to(device)
        rec_model.to(device)
        logger.info("Models loaded successfully.")

# Function to process image and run OCR
def process_image(image, langs, det_model, det_processor, rec_model, rec_processor):
    """
    Run OCR on the provided image.
    """
    predictions = run_ocr(
        [image],
        [langs],
        det_model,
        det_processor,
        rec_model,
        rec_processor,
        detection_batch_size=detection_batch_size,
        recognition_batch_size=recognition_batch_size,
    )
    return predictions

# Function to extract text from uploaded file using Surya OCR
def extract_text_from_file(file: UploadFile):
    try:
        # Read the uploaded file into a PIL Image object
        image = Image.open(file.file)
        
        # Resize image to improve OCR accuracy
        image.thumbnail((1024, 1024), Image.LANCZOS)  # Use LANCZOS for high-quality downsizing
        
        # Load OCR models once
        load_models_once()

        # Perform OCR
        start_time = time.time()
        predictions = process_image(image, langs, det_model, det_processor, rec_model, rec_processor)
        execution_time = time.time() - start_time
        logger.info("Execution time: %.2f seconds", execution_time)

        # Extract text from predictions
        extracted_text = " ".join([each.text for each in predictions[0].text_lines])
        print(extracted_text)

        return {"extracted_text": extracted_text, "execution_time": execution_time}

    except Exception as e:
        logging.error(f"Error extracting text from file: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract text from the file.")

# Function to fetch applicant data by name from MongoDB
def get_applicant_by_name(name: str):
    applicant = application_collection.find_one({"name": name})
    return applicant

# Function to validate the extracted data with the applicant's data from MongoDB
def validate_uploaded_documents(extracted_text, applicant):
    mismatches = {}

    # Example validation checks for Aadhar and PAN based on the extracted text
    if "Aadhar" in extracted_text:
        if applicant.get('aadhar_number') not in extracted_text:
            mismatches["Aadhar"] = "Aadhar document mismatch."
    
    if "PAN" in extracted_text:
        if applicant.get('pan_number') not in extracted_text:
            mismatches["PAN"] = "PAN document mismatch."
    
    if "Gate Score" in extracted_text:
        if str(applicant.get('gateScore')) not in extracted_text:
            mismatches["Gate Score"] = "Gate Score document mismatch."
    
    if "Community" in extracted_text:
        if applicant.get('community_certificate') not in extracted_text:
            mismatches["Community Certificate"] = "Community Certificate mismatch."
    
    if "PWD" in extracted_text:
        if applicant.get('pwd_certificate') not in extracted_text:
            mismatches["PWD Certificate"] = "PWD Certificate mismatch."

    return mismatches

# API for application form submission
@app.post("/submit-application/")
async def submit_application(
    applicationId: str=Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    job: str = Form(...),
    education: str = Form(...),
    gateScore: float = Form(...),
    password: str = Form(...),
):
    """
    Submit application form details to MongoDB.
    """
    try:
        # Save form details to MongoDB
        application_data = {
            "applicationId": applicationId,
            "name": name,
            "email": email,
            "phone": phone,
            "job": job,
            "education": education,
            "gateScore": gateScore,
            "personwithdisablities": password,  # Save personwithdisablities
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        application_collection.insert_one(application_data)

        return {"message": "Application submitted successfully."}

    except Exception as e:
        logger.error(f"Error submitting application: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your application.")

# API to upload and process files
@app.post("/upload/")
async def upload_file(
    applicationId: str = Form(...),  # Applicant's ID to match against
    aadhar: UploadFile = File(None),
    pan: UploadFile = File(None),
    community_certificate: UploadFile = File(None),
    gate_score_card: UploadFile = File(None),
    pwd_certificate: UploadFile = File(None),
):
    """
    Upload and validate individual files, comparing extracted details with applicant data.
    """
    try:
        # Fetch applicant data using the application ID
        applicant = application_collection.find_one({"applicationId": applicationId})
        if not applicant:
            return JSONResponse(status_code=404, content={"message": "Applicant not found."})

        mismatches = {}

        # If an Aadhar file is uploaded
        if aadhar:
            aadhar_text = extract_text_from_file(aadhar)
            aadhar_mismatches = validate_uploaded_documents(aadhar_text["extracted_text"], applicant)
            if aadhar_mismatches:
                return JSONResponse(status_code=400, content={"message": "Mismatch found for Aadhar", "mismatches": aadhar_mismatches})
            # Store extracted text in the applicant's record
            application_collection.update_one(
                {"applicationId": applicationId},
                {"$set": {"aadhar_extracted_text": aadhar_text["extracted_text"]}},
            )
            return {"message": "Aadhar file processed successfully."}

        # If a PAN file is uploaded
        if pan:
            pan_text = extract_text_from_file(pan)
            pan_mismatches = validate_uploaded_documents(pan_text["extracted_text"], applicant)
            if pan_mismatches:
                return JSONResponse(status_code=400, content={"message": "Mismatch found for PAN", "mismatches": pan_mismatches})
            application_collection.update_one(
                {"applicationId": applicationId},
                {"$set": {"pan_extracted_text": pan_text["extracted_text"]}},
            )
            return {"message": "PAN file processed successfully."}

        # If a community certificate file is uploaded
        if community_certificate:
            community_text = extract_text_from_file(community_certificate)
            community_mismatches = validate_uploaded_documents(community_text["extracted_text"], applicant)
            if community_mismatches:
                return JSONResponse(status_code=400, content={"message": "Mismatch found for Community Certificate", "mismatches": community_mismatches})
            application_collection.update_one(
                {"applicationId": applicationId},
                {"$set": {"community_extracted_text": community_text["extracted_text"]}},
            )
            return {"message": "Community Certificate file processed successfully."}

        # If a Gate score card file is uploaded
        if gate_score_card:
            gate_score_text = extract_text_from_file(gate_score_card)
            gate_score_mismatches = validate_uploaded_documents(gate_score_text["extracted_text"], applicant)
            if gate_score_mismatches:
                return JSONResponse(status_code=400, content={"message": "Mismatch found for Gate Score", "mismatches": gate_score_mismatches})
            application_collection.update_one(
                {"applicationId": applicationId},
                {"$set": {"gate_score_extracted_text": gate_score_text["extracted_text"]}},
            )
            return {"message": "Gate Score Card file processed successfully."}

        # If a PWD certificate file is uploaded
        if pwd_certificate:
            pwd_text = extract_text_from_file(pwd_certificate)
            pwd_mismatches = validate_uploaded_documents(pwd_text["extracted_text"], applicant)
            if pwd_mismatches:
                return JSONResponse(status_code=400, content={"message": "Mismatch found for PWD Certificate", "mismatches": pwd_mismatches})
            application_collection.update_one(
                {"applicationId": applicationId},
                {"$set": {"pwd_extracted_text": pwd_text["extracted_text"]}},
            )
            return {"message": "PWD Certificate file processed successfully."}

        # If no file is uploaded
        return JSONResponse(status_code=400, content={"message": "No valid file uploaded."})

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return JSONResponse(status_code=500, content={"message": "An error occurred during file processing."})