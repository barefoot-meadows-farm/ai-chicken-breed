from io import BytesIO
import os

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends, HTTPException, status
from fastapi_auth0 import Auth0, Auth0User

from run import predict_breed
from claude_integration import predict_breed_with_claude
from webscraper.cackle.chicken_scraper import get_chicken_info
from webscraper.chickencoopcompany.chicken_scraper import scrape_chickens
from webscraper.hoover.hoover_scraper import scrape_chicken_page
from webscraper.mcmurray.chicken_scraper import scrape_mcmurray_chicken_info
from webscraper.meyer.chicken_scraper import scrape_chicken_prices

# Create a Fast API with an upload endpoint that accepts an image
app = FastAPI()

# Configure Auth0
auth = Auth0(domain=os.environ.get("AUTH0_DOMAIN", "dev-gxmlklv8ian2jrku.us.auth0.com"),
             api_audience=os.environ.get("AUTH0_API_AUDIENCE", "https://chicken-id.fly.dev"))

# Helper function to get the current user
async def get_user(user: Auth0User = Depends(auth.get_user)):
    return user

@app.post("/upload/")
async def upload_image(image: UploadFile = File(...), user: Auth0User = Depends(auth.get_user(scopes=["write:breeds"]))):
    """
    Endpoint that accepts an image upload and uses the local model to identify the chicken breed.
    Requires authentication with write:breeds scope.
    """
    image_data = BytesIO(await image.read())
    results = predict_breed(image_data)
    return {"results": results, "user": user.email}

@app.post("/upload-claude/")
async def upload_image_claude(image: UploadFile = File(...), user: Auth0User = Depends(auth.get_user(scopes=["write:breeds"]))):
    """
    Endpoint that accepts an image upload and uses Claude Sonnet API to identify the chicken breed.
    Returns more detailed information including breed characteristics.
    Requires authentication with write:breeds scope.
    """
    image_data = BytesIO(await image.read())
    results = predict_breed_with_claude(image_data)
    return {"results": results, "user": user.email}


@app.get("/meyer/chick-breed/")
async def get_meyer_breed(breed: str, user: Auth0User = Depends(auth.get_user(scopes=["read:breeds"]))):
    """
    Get information about a specific breed from Meyer Hatchery.
    Requires authentication with read:breeds scope.
    """
    return scrape_chicken_prices(f"https://meyerhatchery.com/products/{breed}-day-old-chicks")

@app.get("/hoover/chick-breed")
async def get_hoover_breed(breed: str, user: Auth0User = Depends(auth.get_user(scopes=["read:breeds"]))):
    """
    Get information about a specific breed from Hoover's Hatchery.
    Requires authentication with read:breeds scope.
    """
    return scrape_chicken_page(f"https://www.hoovershatchery.com/{breed}")

@app.get("/cackle/chick-breed")
async def get_cackle_breed(breed: str, user: Auth0User = Depends(auth.get_user(scopes=["read:breeds"]))):
    """
    Get information about a specific breed from Cackle Hatchery.
    Requires authentication with read:breeds scope.
    """
    return get_chicken_info(f"https://www.cacklehatchery.com/product/{breed}")

@app.get("/mcmurray/chick-breed")
async def get_mcmurray_breed(breed: str, user: Auth0User = Depends(auth.get_user(scopes=["read:breeds"]))):
    """
    Get information about a specific breed from McMurray Hatchery.
    Requires authentication with read:breeds scope.
    """
    chicken = {"name": breed, "link": f"https://www.mcmurrayhatchery.com/{breed}.html"}
    return await scrape_mcmurray_chicken_info(chicken)

@app.post("/scrape-chickencoop")
async def scrape_chickencoop(background_tasks: BackgroundTasks, user: Auth0User = Depends(auth.get_user(scopes=["write:breeds"]))):
    """
    Start a background task to scrape chicken images from chickencoopcompany.com.
    Requires authentication with write:breeds scope.
    """
    background_tasks.add_task(scrape_chickens)
    return {"message": "Scraping started in the background. Images will be saved to ./dataset/train/{breed_name}/", "user": user.email}
