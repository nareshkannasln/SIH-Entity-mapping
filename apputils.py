import mimetypes
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse


def get_local_ip():
    try:
        # Use a dummy connection to determine the local IP address
        print("\tRetrieving local IP address...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip

    except Exception as e:
        print(f"\tError retrieving local IP: {e}")


@asynccontextmanager  # type: ignore
async def lifespan(app: FastAPI):

    print("\n[1] APPLICATION SETUP")
    print("\tStarting the application...")

    print("\n[2] IMPORTING LIBRARIES")
    print("\tImporting required library function...")

    from torch.cuda import is_available as is_cuda_available

    print("\tLibrary import successful!")

    print("\n[3] CHECKING FOR GPU AVAILABILITY")
    print("\tChecking for GPU availability with NVIDIA CUDA enabled...")
    if is_cuda_available():
        print("\tFound GPU with NVIDIA CUDA enabled!")
    else:
        print("\tCould not find GPU with NVIDIA CUDA enabled. Exiting...")
        exit()

    print("\n[4] RETRIEVING LOCAL IP ADDRESS")

    local_ip = get_local_ip()
    if local_ip:
        print(f"\tDetected local IP address: {local_ip}")
        print(
            f"\tShare this IP with the port (e.g., {local_ip}:12345) for local communication.\n"
        )
    else:
        print("\tCould not retrieve the local IP address.\n")

    yield

    print(
        "\nAPPLICATION SHUTDOWN TRIGGER RECEIVED!\n\tShutting down the application...\n"
    )


async def health_check():
    return JSONResponse(content={"status": "ok"})


async def validate(file: UploadFile = File(...)):
    mime_type, _ = mimetypes.guess_type(file.filename)  # type: ignore
    if mime_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only images (jpeg, png) and PDFs are allowed.",
        )

    return JSONResponse(content={"filename": file.filename, "content_type": mime_type})
