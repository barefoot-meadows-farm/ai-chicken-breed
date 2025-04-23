import os
from io import BytesIO
from dotenv import load_dotenv
from claude_integration import predict_breed_with_claude

# Load environment variables
load_dotenv()

def test_claude_integration():
    """
    Test the Claude integration by sending a simple image.
    This is a basic test to verify that the API call works.
    """
    # Create a simple test image (1x1 pixel)
    # This won't give meaningful results but will test the API call
    test_image = BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82')
    
    try:
        # Call the function
        results = predict_breed_with_claude(test_image)
        print("Test successful!")
        print("Results:", results)
        return True
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    test_claude_integration()