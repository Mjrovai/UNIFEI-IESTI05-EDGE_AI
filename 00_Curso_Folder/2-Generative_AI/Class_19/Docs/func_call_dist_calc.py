import time
import json
from haversine import haversine
from ollama import chat

# Reference coordinates for Santiago, Chile
mylat, mylon = -33.33, -70.51
MODEL = "llama3.2:3B"

# Define a Python function that Ollama can call
def calc_distance(lat, lon, city):
    """Compute distance and print a descriptive message."""
    distance = haversine((mylat, mylon), (lat, lon), unit="km")
    msg = f"\nSantiago de Chile is about {int(round(distance, -1)):,} kilometers away from {city}."
    return {"city": city, "distance_km": int(round(distance, -1)), "message": msg}

# Define the tool descriptor (schema)
tools = [
    {
        "type": "function",
        "function": {
            "name": "calc_distance",
            "description": "Calculates the distance from Santiago, Chile to a given city's coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude of the city"},
                    "lon": {"type": "number", "description": "Longitude of the city"},
                    "city": {"type": "string", "description": "Name of the city"}
                },
                "required": ["lat", "lon", "city"]
            }
        }
    }
]

def ask_and_measure(country):
    """Let Ollama find the capital and call the local Python function."""
    start = time.perf_counter()

    # Send initial message asking for the capital coordinates
    response = chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": f"Find the decimal latitude and longitude of the capital of {country},"
                       " then use the calc_distance tool to determine how far it is from Santiago de Chile."
        }],
        tools=tools
    )

    # If the model returns a tool call, execute it locally
    if hasattr(response.message, "tool_calls") and response.message.tool_calls:
        for call in response.message.tool_calls:
            if call["function"]["name"] == "calc_distance":
                raw_args = call["function"]["arguments"]

                # Decode JSON if necessary
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

                # Normalize key names
                if "lat1" in args or "lat2" in args:
                    args["lat"] = args.get("lat2") or args.get("lat1")
                    args["lon"] = args.get("lon2") or args.get("lon1")
                if "latitude" in args:
                    args["lat"] = args["latitude"]
                if "longitude" in args:
                    args["lon"] = args["longitude"]
                args = {k: v for k, v in args.items() if k in ("lat", "lon", "city")}

                # Convert numbers
                args["lat"] = float(args["lat"])
                args["lon"] = float(args["lon"])

                result = calc_distance(**args)
                print(result["message"])
    
    elapsed = time.perf_counter() - start
    print(f"[INFO] ==> Model {MODEL} : {elapsed:.1f} s")

# Example runs
ask_and_measure("France")
ask_and_measure("Colombia")
ask_and_measure("United States")
