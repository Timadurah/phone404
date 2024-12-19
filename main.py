from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from phonenumbers import parse, is_valid_number, NumberParseException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import random
import csv
import io
import uvicorn
import uuid
from typing import List

app = FastAPI()

# Enable CORS for all domains (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Function to generate a random phone number with a given country code
def generate_phone_number(country_code: str, prefix: str):
    random_number = random.randint(1000000, 9999999)  # Generate a 7-digit number
    phone_number = f"{country_code}{prefix}{random_number}"
    return phone_number

# Function to check if the phone number is valid
def is_valid_phone_number(phone_number: str, country_code: str):
    try:
        parsed_number = parse(phone_number, country_code)
        return is_valid_number(parsed_number)
    except NumberParseException:
        return False

# Generate phone numbers and validate them
def generate_phone_numbers(country_code: str, prefix: str, amount: int):
    valid_numbers = []
    for _ in range(amount):
        phone_number = generate_phone_number(country_code, prefix)
        if is_valid_phone_number(phone_number, country_code):
            valid_numbers.append({"phone_number": phone_number})
    return valid_numbers

# Background task to save phone numbers to a CSV file
def save_to_csv(file_obj, numbers: List[dict]):
    writer = csv.writer(file_obj)
    writer.writerow(["Phone Number"])  # Remove carrier column, only keep phone number
    for item in numbers:
        writer.writerow([item["phone_number"]])

# Endpoint to generate phone numbers and provide a download link for the CSV
class PhoneNumberRequest(BaseModel):
    country_code: str
    prefix: str
    amount: int

@app.post("/generate-and-download")
async def generate_and_download(request: PhoneNumberRequest, background_tasks: BackgroundTasks):
    if not request.country_code.startswith("+"):
        raise HTTPException(status_code=400, detail="Country code must start with '+'")
    if not request.prefix.isdigit() or len(request.prefix) < 3:
        raise HTTPException(status_code=400, detail="Prefix must be a number with at least 3 digits")
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    valid_numbers = generate_phone_numbers(request.country_code, request.prefix, request.amount)
    
    # Create an in-memory file-like object
    file_obj = io.StringIO()
    background_tasks.add_task(save_to_csv, file_obj, valid_numbers)

    # Generate a unique file name (not required, but helpful for user experience)
    file_name = f"phone_numbers_{uuid.uuid4()}.csv"
    
    # Rewind the in-memory file object before returning it
    file_obj.seek(0)
    
    return StreamingResponse(
        file_obj,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={file_name}"}
    )

# Home route to serve the frontend with Bootstrap
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
