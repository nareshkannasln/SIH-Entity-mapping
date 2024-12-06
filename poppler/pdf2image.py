import time
from pdf2image import convert_from_path
import torch
from torchvision import transforms

pdf_path = "OCR_extraction.pdf"
poppler_path = r"D:\Program Files\poppler-24.08.0\Library\bin"
dpi = 300  # Set the DPI value as needed
first_page = 1  # Set the first page number
last_page = 2  # Set the last page number

device = 'cuda' if torch.cuda.is_available() else 'cpu'
if torch.cuda.is_available():
    print("Using CUDA")
else:
    print("CUDA not available")

start_time = time.time()
# Convert PDF to images
images = convert_from_path(pdf_path, poppler_path=poppler_path, dpi=dpi, first_page=first_page, last_page=last_page)

# Define a transform to convert images to tensors
transform = transforms.ToTensor()

# Process images using GPU
for i, image in enumerate(images):
    # Convert image to tensor and move to GPU
    image_tensor = transform(image).to(device)
    
    # Perform your GPU-accelerated image processing here
    # For example, you can apply some transformations using PyTorch
    
    # Convert tensor back to image and save
    image = transforms.ToPILImage()(image_tensor.cpu())
    image.save(f'page_{i+1}.png', quality=95)  # Adjust the quality parameter if needed

end_time = time.time()
execution_time = end_time - start_time
print(f"Execution time: {execution_time} seconds")