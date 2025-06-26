from io import BytesIO
import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends, HTTPException, status
from fastapi_auth0 import Auth0, Auth0User
from starlette.middleware.cors import CORSMiddleware

from run import predict_breed
from claude_integration import predict_breed_with_claude
# from supabase_integration import store_image_upload, get_user_uploads, get_upload_by_id
from webscraper.cackle.chicken_scraper import get_chicken_info
from webscraper.chickencoopcompany.chicken_scraper import scrape_chickens
from webscraper.hoover.hoover_scraper import scrape_chicken_page
from webscraper.mcmurray.chicken_scraper import scrape_mcmurray_chicken_info
from webscraper.meyer.chicken_scraper import scrape_chicken_prices

# Create a Fast API with an upload endpoint that accepts an image
app = FastAPI(
    title="Chicken Breed Classifier API",
    description="Classify chicken breeds from images and get breed information from various hatcheries.",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "R2u6cixiaKssrdBT0fXVA0Kr55L4Nhaw",
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


load_dotenv()

# Configure Auth0
auth = Auth0(domain=os.getenv("AUTH0_DOMAIN", "dev-gxmlklv8ian2jrku.us.auth0.com"),
             api_audience=os.getenv("AUTH0_API_AUDIENCE", "https://chicken-id.fly.dev"))

# Helper function to get the current user
async def get_user(user: Auth0User = Depends(auth.get_user)):
    return user

@app.post("/upload/", dependencies=[Depends(auth.implicit_scheme)])
async def upload_image(image: UploadFile = File(...), user: Auth0User = Depends(auth.get_user)):
    """
    Endpoint that accepts an image upload and uses the local model to identify the chicken breed.
    Requires authentication with write:breeds scope.
    Stores the image, user, and results in Supabase.
    """
    image_data = BytesIO(await image.read())
    results = predict_breed(image_data)

    # Store in Supabase
    # supabase_response = store_image_upload(
    #     image_data=image_data,
    #     user_email=user.email,
    #     results=results,
    #     model_type="local"
    # )

    # return {"results": results, "user": user.email, "upload_id": supabase_response[0]["id"] if supabase_response else None}
    return {"results": results, "user": user}

@app.post("/upload-claude/", dependencies=[Depends(auth.implicit_scheme)])
async def upload_image_claude(image: UploadFile = File(...), user: Auth0User = Depends(auth.get_user)):
    """
    Endpoint that accepts an image upload and uses Claude Sonnet API to identify the chicken breed.
    Returns more detailed information including breed characteristics.
    Requires authentication with write:breeds scope.
    Stores the image, user, and results in Supabase.
    """
    image_data = BytesIO(await image.read())
    results = predict_breed_with_claude(image_data)

    # Store in Supabase
    # supabase_response = store_image_upload(
    #     image_data=image_data,
    #     user_email=user.email,
    #     results=results,
    #     model_type="claude"
    # )

    # return {"results": results, "user": user.email, "upload_id": supabase_response[0]["id"] if supabase_response else None}
    return {"results": results, "user": user.email}


@app.get("/meyer/chick-breed/")
async def get_meyer_breed(breed: str, user: Auth0User = Depends(auth.get_user)):
    """
    Get information about a specific breed from Meyer Hatchery.
    Requires authentication with read:breeds scope.
    """
    return scrape_chicken_prices(f"https://meyerhatchery.com/products/{breed}-day-old-chicks")

@app.get("/hoover/chick-breed")
async def get_hoover_breed(breed: str, user: Auth0User = Depends(auth.get_user)):
    """
    Get information about a specific breed from Hoover's Hatchery.
    Requires authentication with read:breeds scope.
    """
    return scrape_chicken_page(f"https://www.hoovershatchery.com/{breed}")

@app.get("/cackle/chick-breed")
async def get_cackle_breed(breed: str, user: Auth0User = Depends(auth.get_user)):
    """
    Get information about a specific breed from Cackle Hatchery.
    Requires authentication with read:breeds scope.
    """
    return get_chicken_info(f"https://www.cacklehatchery.com/product/{breed}")

@app.get("/mcmurray/chick-breed")
async def get_mcmurray_breed(breed: str, user: Auth0User = Depends(auth.get_user)):
    """
    Get information about a specific breed from McMurray Hatchery.
    Requires authentication with read:breeds scope.
    """
    chicken = {"name": breed, "link": f"https://www.mcmurrayhatchery.com/{breed}.html"}
    return await scrape_mcmurray_chicken_info(chicken)

@app.post("/scrape-chickencoop")
async def scrape_chickencoop(background_tasks: BackgroundTasks, user: Auth0User = Depends(auth.get_user)):
    """
    Start a background task to scrape chicken images from chickencoopcompany.com.
    Requires authentication with write:breeds scope.
    """
    background_tasks.add_task(scrape_chickens)
    return {"message": "Scraping started in the background. Images will be saved to ./dataset/train/{breed_name}/", "user": user.email}

# @app.get("/uploads/", dependencies=[Depends(auth.implicit_scheme)])
# async def get_uploads(user: Auth0User = Depends(auth.get_user)):
#     """
#     Get all uploads for the authenticated user.
#     Requires authentication.
#     """
#     uploads = get_user_uploads(user.email)
#     return {"uploads": uploads, "user": user.email}
#
# @app.get("/uploads/{upload_id}", dependencies=[Depends(auth.implicit_scheme)])
# async def get_upload(upload_id: str, user: Auth0User = Depends(auth.get_user)):
#     """
#     Get a specific upload by ID.
#     Requires authentication.
#     """
#     upload = get_upload_by_id(upload_id)
#
#     if not upload:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Upload with ID {upload_id} not found"
#         )
#
#     # Check if the upload belongs to the authenticated user
#     if upload["user_email"] != user.email:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You don't have permission to access this upload"
#         )
#
#     return {"upload": upload, "user": user.email}


