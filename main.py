from io import BytesIO

from fastapi import FastAPI, UploadFile, File

from run import predict_breed
from webscraper.meyer.chicken_scraper import scrape_chicken_prices

# Create a Fast API with an upload endpoint that accepts an image
app = FastAPI()

@app.post("/upload/")
async def upload_image(image: UploadFile = File(...)):
    image_data = BytesIO(await image.read())
    results = predict_breed(image_data)
    return {"results": results}


@app.get("/chick-breed/")
async def get_breed(breed: str):
    return scrape_chicken_prices(f"https://meyerhatchery.com/products/{breed}-day-old-chicks")