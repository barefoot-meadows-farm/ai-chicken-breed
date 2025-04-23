import base64
import os
from io import BytesIO
from typing import List, Dict, Any
from PIL import Image

from anthropic import Anthropic


def compress_image(image_data: BytesIO, max_size_mb: float = 4.5) -> BytesIO:
    """
    Compress an image to ensure it's below the specified maximum size.

    Args:
        image_data: BytesIO object containing the image data
        max_size_mb: Maximum size in MB (default 4.5 to have some buffer)

    Returns:
        BytesIO object containing the compressed image data
    """
    max_size_bytes = max_size_mb * 1024 * 1024

    # Open the image
    image_data.seek(0)
    img = Image.open(image_data)
    img_format = img.format or 'JPEG'

    # If image has transparency (RGBA mode) and we want to save as JPEG,
    # we need to convert it to RGB first
    if img.mode == 'RGBA':
        # Create a white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        # Paste the image on the background using the alpha channel as mask
        background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
        img = background

    # Check if the image is already below the threshold
    img_bytes = BytesIO()
    save_kwargs = {'format': img_format}
    if img_format in ['JPEG', 'JPG']:
        save_kwargs['quality'] = 95
        save_kwargs['optimize'] = True

    img.save(img_bytes, **save_kwargs)
    img_bytes.seek(0)

    if len(img_bytes.getvalue()) <= max_size_bytes:
        return img_bytes

    # Start with a high quality and gradually reduce until size is acceptable
    quality = 90
    width, height = img.size

    while True:
        # Resize the image if it's still too large at lowest quality
        if quality < 30:
            # Calculate new dimensions (reduce by 20%)
            width = int(width * 0.8)
            height = int(height * 0.8)
            img = img.resize((width, height), Image.LANCZOS)
            quality = 80  # Reset quality after resize

        # Try compressing with current quality
        img_bytes = BytesIO()
        if img_format in ['JPEG', 'JPG']:
            img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
        else:
            # For non-JPEG formats, just use resize to reduce size
            img.save(img_bytes, format='JPEG', quality=quality, optimize=True)

        img_bytes.seek(0)

        if len(img_bytes.getvalue()) <= max_size_bytes:
            print(f"Compressed image to {len(img_bytes.getvalue()) / (1024 * 1024):.2f} MB with quality {quality}")
            return img_bytes

        # Reduce quality and try again
        quality -= 10


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

    # Compress image to ensure it's under 5MB
    compressed_image = compress_image(image_data)

    # Convert image to base64
    compressed_image.seek(0)
    image_base64 = base64.b64encode(compressed_image.read()).decode("utf-8")

    # Create a detailed prompt for Claude
    prompt = """
    You are an expert poultry identification specialist with years of experience judging at chicken shows and working with breeders. Your task is to analyze the provided image and identify the chicken breed(s) with maximum accuracy.

    When identifying chicken breeds, focus on these key characteristics:
    1. Comb type (single, pea, rose, buttercup, etc.)
    2. Feather patterns and coloration
    3. Body size and shape
    4. Leg color and features (feathered vs clean)
    5. Distinctive features like muffs, beards, crests, or unique plumage
    
    For each breed you identify, provide:
    1. The specific breed name, including variety/color if identifiable
    2. Your confidence level (as a percentage)
    3. A detailed explanation of the identifying characteristics you observed in the image
    4. Any potential similar breeds it might be confused with, and how you distinguished them
    
    If you cannot identify the breed with high confidence, explain why and list the most likely possibilities based on visible traits.
    
    If the image quality, angle, or lighting makes identification difficult, please note this in your analysis.

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
        model="claude-3-7-sonnet-20250219",
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