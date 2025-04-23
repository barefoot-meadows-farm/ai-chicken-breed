import os
import base64
from io import BytesIO
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Get API key from environment variable
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

# Initialize Anthropic client
client = Anthropic(api_key=api_key)

# Create a simple test image (1x1 pixel)
test_image = BytesIO(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82')

# Convert image to base64
test_image.seek(0)
image_base64 = base64.b64encode(test_image.read()).decode("utf-8")

# Simple prompt for Claude
prompt = "What do you see in this image?"

try:
    # Call Claude API with the image and prompt
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=100,
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
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    }
                ]
            }
        ]
    )

    # Print the response
    print("API call successful!")
    print("Response:", response.content[0].text)

except Exception as e:
    print(f"Test failed with error: {str(e)}")