import sys
import time
from haversine import haversine
from ollama import chat
from pydantic import BaseModel, Field

img_path = sys.argv[1]
MODEL = 'gemma3:4b'
mylat = -33.33
mylon = -70.51


class CityCoord(BaseModel):
    city: str = Field(..., description="Name of the city in the image")
    country: str = Field(..., description="Name of the country where the city in the image is located")
    lat: float = Field(..., description="Decimal Latitude of the city in the image")
    lon: float = Field(..., description="Decimal Longitude of the city in the image")


def image_description(img_path):
    with open(img_path, 'rb') as file:
        response = chat(
            model=MODEL,
            messages=[
              {
                'role': 'user',
                'content': '''return the decimal latitude and decimal longitude 
                              of the city in the image, its name, and what 
                              country it is located''',
                'images': [file.read()],
              },
            ],
            options = {
              'temperature': 0,
              }
      )
    #print(response['message']['content'])
    return response['message']['content']


def calc_dist_image (img_path, model=MODEL):
    start_time = time.perf_counter()  # Start timing

    img_descript = image_description(img_path)
    #print("\n",img_descript)
    
    response = chat(
    model=MODEL,
    messages=[{
        "role": "user",
        "content": img_descript # image_description from previous model
    }],
    format=CityCoord.model_json_schema(),  # Structured JSON format
    options={"temperature": 0}
    )

    resp = CityCoord.model_validate_json(response.message.content)
    #print("\n",resp)
    distance = haversine((mylat, mylon), (resp.lat, resp.lon), unit='km')
    
    end_time = time.perf_counter()  # End timing
    elapsed_time = end_time - start_time  # Calculate elapsed time
    
    print(f"\nThe image shows {resp.city}, with lat:{round(resp.lat, 2)} and \
long: {round(resp.lon, 2)}, located in {resp.country} and \
about {int(round(distance, -1)):,} kilometers away from Santiago, Chile.\n")

    print(f" [INFO] ==> The code (running {MODEL}), took {elapsed_time:.1f} \
seconds to execute.\n")

calc_dist_image (img_path, model=MODEL)