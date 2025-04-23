"""
Supabase integration for the chicken breed classifier application.
This module provides functions to connect to Supabase and store data.
"""
import os
import base64
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(supabase_url, supabase_key)

def get_supabase_client() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Client: The Supabase client instance.
    """
    return supabase

def store_image_upload(
    image_data: BytesIO,
    user_email: str,
    results: Dict[str, Any],
    model_type: str = "local"
) -> Dict[str, Any]:
    """
    Store an image upload and its prediction results in Supabase.
    
    Args:
        image_data (BytesIO): The uploaded image data.
        user_email (str): The email of the user who uploaded the image.
        results (Dict[str, Any]): The prediction results.
        model_type (str, optional): The type of model used for prediction. Defaults to "local".
        
    Returns:
        Dict[str, Any]: The response from Supabase.
    """
    # Convert image to base64 for storage
    image_data.seek(0)
    image_base64 = base64.b64encode(image_data.read()).decode('utf-8')
    
    # Create record in uploads table
    upload_data = {
        "user_email": user_email,
        "image": image_base64,
        "model_type": model_type,
        "results": results,
        "created_at": datetime.now().isoformat()
    }
    
    response = supabase.table("uploads").insert(upload_data).execute()
    
    return response.data

def get_user_uploads(user_email: str) -> Dict[str, Any]:
    """
    Get all uploads for a specific user.
    
    Args:
        user_email (str): The email of the user.
        
    Returns:
        Dict[str, Any]: The uploads for the user.
    """
    response = supabase.table("uploads").select("*").eq("user_email", user_email).execute()
    
    return response.data

def get_upload_by_id(upload_id: str) -> Optional[Dict[str, Any]]:
    """
    Get an upload by its ID.
    
    Args:
        upload_id (str): The ID of the upload.
        
    Returns:
        Optional[Dict[str, Any]]: The upload data if found, None otherwise.
    """
    response = supabase.table("uploads").select("*").eq("id", upload_id).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    
    return None