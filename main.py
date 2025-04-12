from io import BytesIO

from fastapi import FastAPI, UploadFile, File, BackgroundTasks

from run import predict_breed
from webscraper.cackle.chicken_scraper import get_chicken_info
from webscraper.chickencoopcompany.chicken_scraper import scrape_chickens
from webscraper.hoover.hoover_scraper import scrape_chicken_page
from webscraper.mcmurray.chicken_scraper import scrape_mcmurray_chicken_info
from webscraper.meyer.chicken_scraper import scrape_chicken_prices

# Create a Fast API with an upload endpoint that accepts an image
app = FastAPI()

@app.post("/upload/")
async def upload_image(image: UploadFile = File(...)):
    image_data = BytesIO(await image.read())
    results = predict_breed(image_data)
    return {"results": results}


@app.get("/meyer/chick-breed/")
async def get_breed(breed: str):
    return scrape_chicken_prices(f"https://meyerhatchery.com/products/{breed}-day-old-chicks")

@app.get("/hoover/chick-breed")
async def get_breed(breed: str):
    return scrape_chicken_page(f"https://www.hoovershatchery.com/{breed}")

@app.get("/cackle/chick-breed")
async def get_breed(breed: str):
    return get_chicken_info(f"https://www.cacklehatchery.com/product/{breed}")

@app.get("/mcmurray/chick-breed")
async def get_breed(breed: str):
    chicken = {"name": breed, "link": f"https://www.mcmurrayhatchery.com/{breed}.html"}
    return await scrape_mcmurray_chicken_info(chicken)

@app.post("/scrape-chickencoop")
async def scrape_chickencoop(background_tasks: BackgroundTasks):
    """
    Start a background task to scrape chicken images from chickencoopcompany.com
    """
    background_tasks.add_task(scrape_chickens)
    return {"message": "Scraping started in the background. Images will be saved to ./dataset/train/{breed_name}/"}