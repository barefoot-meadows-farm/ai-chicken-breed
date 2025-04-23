import base64
import os
from io import BytesIO
from typing import List, Dict, Any

from anthropic import Anthropic

def predict_breed_with_claude(image_data: BytesIO) -> List[Dict[str, Any]]:
    """
    Use Claude Sonnet API to detect chicken breeds from an image.
    
    Args:
        image_data: BytesIO object containing the image data
        
    Returns:
        List of dictionaries containing breed predictions and confidence scores
    """
    # Get API key from environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)
    
    # Convert image to base64
    image_data.seek(0)
    image_base64 = base64.b64encode(image_data.read()).decode("utf-8")
    
    # Create a detailed prompt for Claude
    prompt = """
    You are an expert in poultry identification, specializing in chicken breeds. 
    Please analyze the provided image and identify the chicken breed(s) present.
    
    For each breed you identify, provide:
    1. The breed name
    2. Your confidence level (as a percentage)
    3. Key identifying characteristics you observed
    
    If possible, identify the top 3 most likely breeds based on the visual evidence.
    If you cannot identify the breed with certainty, please explain why and suggest possible options.
    
    Please format your response as a JSON array of objects with the following structure:
    [
        {
            "breed": "Breed Name",
            "confidence": 95.5,
            "characteristics": "Key identifying features"
        },
        ...
    ]
    
    Only include the JSON in your response, no other text.
    """
    
    # Call Claude API with the image and prompt
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }
        ]
    )
    
    # Extract and parse the response
    try:
        # The response should be a JSON string containing the breed predictions
        import json
        results = json.loads(response.content[0].text)
        
        # Format the results to match the existing API format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "breed": result["breed"],
                "confidence": result["confidence"],
                "characteristics": result.get("characteristics", "")
            })
        
        return formatted_results
    except Exception as e:
        # If parsing fails, return the error
        return [{"error": f"Failed to parse Claude response: {str(e)}"}]