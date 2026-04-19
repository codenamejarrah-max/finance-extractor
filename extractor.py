import google.generativeai as genai
import os
import json
import logging
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def extract_multiple_api(image_path: str, provided_key: str = None) -> list:
    """
    Takes an image path and uses Gemini Vision to extract multiple transactions.
    Returns a LIST of dictionaries.
    """
    # Use provided key or reload from environment
    target_key = provided_key or os.getenv("GEMINI_API_KEY")
    
    if not target_key:
        logging.error("Gemini API Key is not set in .env")
        return []

    try:
        # Configure API every time to ensure the latest key is used if it changed
        genai.configure(api_key=target_key)
        
        # Load the image
        img = Image.open(image_path)
        
        # Use the flash model for speed and cost-efficiency
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = """
        You are an expert financial assistant. Look at this bank transaction screenshot which may contain SEVERAL transactions.
        Extract the following information for EACH transaction and return ONLY a valid JSON ARRAY of objects. 
        Do not include any markdown formatting like ```json.
        
        Requirements for each object:
        1. "Date": The date of the transaction (format: YYYY-MM-DD).
        2. "Amount": The absolute total amount as a number (e.g., 250000, no currency symbols or commas).
        3. "Merchant": The name of the store, person, or entity.
        4. "Wallet": The name of the bank or wallet this screenshot belongs to.
        
        Example Output:
        [
            {
                "Date": "2023-10-25",
                "Amount": 150000,
                "Merchant": "Coffee Shop",
                "Wallet": "Bank A"
            }
        ]
        """
        
        response = model.generate_content([prompt, img])
        
        # Extract and clean JSON response
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[::-1].replace("```", "", 1)[::-1]
            
        data = json.loads(response_text.strip())
        
        # Ensure it's always a list
        if isinstance(data, dict):
            return [data]
        return data

    except Exception as e:
        logging.error(f"Failed to extract API data: {e}")
        return []
