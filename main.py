from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import random
import requests
import os
import phonenumbers
from phonenumbers import carrier, number_type, PhoneNumberType
from phonenumbers.phonenumberutil import NumberParseException

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

# Function to get carrier and line type information for a generated phone number
def get_phone_number_info(phone_number: str, country_code: str):
    try:
        # Parse the phone number with the country code
        parsed_number = phonenumbers.parse(phone_number, country_code)

        # Check if the phone number is valid
        phone_carrier = carrier.name_for_number(parsed_number, 'en')  # Get carrier info
        phone_number_type = phonenumbers.number_type(parsed_number)

        # Determine if the number is mobile or landline
        if phone_number_type == PhoneNumberType.MOBILE:
            line_type = 'mobile'
        elif phone_number_type == PhoneNumberType.FIXED_LINE:
            line_type = 'landline'
        else:
            line_type = 'unknown'

        return {
            "phone_number": phone_number,
            "carrier": phone_carrier if phone_carrier else "Unknown",
            "line_type": line_type,
            "valid": True
        }
    except NumberParseException as e:
        print(f"Error parsing number: {e}")
        return {"phone_number": phone_number, "valid": False, "carrier": "Unknown", "line_type": "unknown"}

# Function to generate phone numbers with carrier and line type information
def generate_phone_numbers(country_code: str, prefix: str, amount: int):
    valid_numbers = []
    for _ in range(amount):
        phone_number = generate_phone_number(country_code, prefix)
        number_info = get_phone_number_info(phone_number, country_code)
        if number_info['valid']:
            valid_numbers.append({
                "phone_number": number_info['phone_number'],
                "carrier": number_info['carrier'],
                "line_type": number_info['line_type']
            })
    return valid_numbers

# Request model for the phone number generation API
class PhoneNumberRequest(BaseModel):
    country_code: str
    prefix: str
    amount: int

# In your /generate-and-send endpoint, you send more detailed data to the PHP API
@app.post("/generate-and-send")
async def generate_and_send(request: PhoneNumberRequest):
    if not request.country_code.startswith("+"):
        raise HTTPException(status_code=400, detail="Country code must start with '+'")
    if not request.prefix.isdigit() or len(request.prefix) < 3:
        raise HTTPException(status_code=400, detail="Prefix must be a number with at least 3 digits")
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    valid_numbers = generate_phone_numbers(request.country_code, request.prefix, request.amount)
    
    if len(valid_numbers) == 0:
        raise HTTPException(status_code=400, detail="No valid phone numbers generated")

    # Send the phone numbers to the PHP API (replace with your API URL)
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
