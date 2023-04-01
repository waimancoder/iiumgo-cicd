import requests
from django.core.cache import cache
from datetime import datetime


def get_pricing(
    origin_latitude,
    origin_longitude,
    destination_latitude,
    destination_longitude,
    vehicle_enable="entireRoute",
    transit_enable="",
    taxi_enable="",
    rented_enable="",
):
    api_key = ("m3bxwLAWhIOU8_fSqsx4FL2AeiuPpBtafsRXTCTJVCs",)
    # Check if origin and destination coordinates are already cached
    cache_key = f"{origin_latitude},{origin_longitude},{destination_latitude},{destination_longitude}"
    cached_response = cache.get(cache_key)
    if cached_response:
        print("using cache data")
        json_response = cached_response
    else:
        # Make API request and store response in cache
        base_url = "https://intermodal.router.hereapi.com"
        version = "/v8"
        resource = "/routes"
        params = {
            "origin": f"{origin_latitude},{origin_longitude}",
            "destination": f"{destination_latitude},{destination_longitude}",
            "vehicle[enable]": vehicle_enable,
            "transit[enable]": transit_enable,
            "taxi[enable]": taxi_enable,
            "rented[enable]": rented_enable,
            "apiKey": api_key,
        }
        url = f"{base_url}{version}{resource}"
        response = requests.get(url, params=params)
        json_response = response.json()

    if "notices" in json_response:
        for notice in json_response["notices"]:
            if notice["code"] == "departureArrivalTooClose":
                departure_time = None
                arrival_time = None
    else:
        cache.set(cache_key, json_response, timeout=30)
        departure_time = json_response["routes"][0]["sections"][0]["departure"]["time"]
        arrival_time = json_response["routes"][0]["sections"][0]["arrival"]["time"]

        # Convert departure and arrival time to datetime objects
        departure_datetime = datetime.fromisoformat(departure_time[:-6])
        arrival_datetime = datetime.fromisoformat(arrival_time[:-6])

        duration_seconds = (arrival_datetime - departure_datetime).total_seconds()
        duration_minutes = duration_seconds // 60

    params = {
        "origin": f"{origin_latitude},{origin_longitude}",
        "destination": f"{destination_latitude},{destination_longitude}",
        "return": "summary,typicalDuration",
        "transportMode": "car",
        "apikey": api_key,
    }

    distance_url = "https://router.hereapi.com/v8/routes"
    response = requests.get(distance_url, params=params)
    data = response.json()
    details = data["routes"][0]["sections"][0]["summary"]
    distance = details["length"]

    if departure_time is None and arrival_time is None:
        duration_minutes = details["typicalDuration"]

    fares_4seater_student = 2.50 + (duration_minutes / 60) * 0.45 + (distance * 0.001) * 0.25
    fares_4seater_stuff = 3.00 + (duration_minutes / 60) * 0.45 + (distance * 0.001) * 0.25
    fares_4seater_outsider = 3.80 + (duration_minutes / 60) * 0.45 + (distance * 0.001) * 0.25
    fares_6seater_student = 3.00 + (duration_minutes / 60) * 0.45 + (distance * 0.001) * 0.25
    fares_6seater_stuff = 3.50 + (duration_minutes / 60) * 0.45 + (distance * 0.001) * 0.25
    fares_6seater_outsider = 4.00 + (duration_minutes / 60) * 0.45 + (distance * 0.001) * 0.25

    prices = [
        fares_4seater_student,
        fares_4seater_stuff,
        fares_4seater_outsider,
        fares_6seater_student,
        fares_6seater_stuff,
        fares_6seater_outsider,
    ]

    updated_price = []

    for price in prices:
        if price % 1 < 0.5:
            rounded_price = round(price + 0.15, 1)
        else:
            rounded_price = round(price + 0.5, 1)

        if rounded_price % 1 < 0.5:
            rounded_price = rounded_price if rounded_price % 0.5 == 0 else round(rounded_price / 0.5) * 0.5
        else:
            rounded_price = round(rounded_price, 1)

        updated_price.append(rounded_price)

    fares = {
        "4seater_student": updated_price[0],
        "4seater_stuff": updated_price[1],
        "4seater_outsider": updated_price[2],
        "6seater_student": updated_price[3],
        "6seater_stuff": updated_price[4],
        "6seater_outsider": updated_price[5],
    }
    return fares
