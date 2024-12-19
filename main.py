from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import random
import requests
import os
import uvicorn
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

# Function to check if the phone number is valid (implement validation logic as needed)
def is_valid_phone_number(phone_number: str, country_code: str):
    # Add validation logic if needed
    return True

# Generate phone numbers and validate them
def generate_phone_numbers(country_code: str, prefix: str, amount: int):
    valid_numbers = []
    for _ in range(amount):
        phone_number = generate_phone_number(country_code, prefix)
        if is_valid_phone_number(phone_number, country_code):
            valid_numbers.append({"phone_number": phone_number})
    return valid_numbers

# Endpoint to generate phone numbers and send to PHP API
class PhoneNumberRequest(BaseModel):
    country_code: str
    prefix: str
    amount: int

@app.post("/generate-and-send")
async def generate_and_send(request: PhoneNumberRequest):
    if not request.country_code.startswith("+"):
        raise HTTPException(status_code=400, detail="Country code must start with '+'")
    if not request.prefix.isdigit() or len(request.prefix) < 3:
        raise HTTPException(status_code=400, detail="Prefix must be a number with at least 3 digits")
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    valid_numbers = generate_phone_numbers(request.country_code, request.prefix, request.amount)
    
    # Send the phone numbers to the PHP API
    php_api_url = "https://topkonnect.net/phone404.php"
    headers = {'Content-Type': 'application/json'}  # Set headers
    
    try:
        # Disable SSL verification and set a timeout of 30 seconds
        response = requests.post(php_api_url, json={"numbers": valid_numbers}, headers=headers, verify=False, timeout=30)
        response_data = response.json()

        if response.status_code == 200:
            file_name = response_data.get("file_name")
            if file_name:
                return {"message": "File saved successfully", "download_link": f"https://topkonnect.net/generated_files/{file_name}"}
            else:
                raise HTTPException(status_code=500, detail="Failed to get file name from PHP API")
        else:
            raise HTTPException(status_code=500, detail="PHP API error: " + response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to PHP API: {e}")

# Endpoint to download the CSV file saved by the PHP API
@app.get("/download-csv")
async def download_csv(file_name: str):
    file_path = os.path.join("generated_files", file_name)  # Adjust path as needed
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/csv", filename=file_name)
    else:
        raise HTTPException(status_code=404, detail="File not found")

# Home route to serve the frontend with Bootstrap
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
