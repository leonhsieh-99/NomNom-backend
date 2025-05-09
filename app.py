from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import random
import traceback
from typing import Dict, Any, Union

app = Flask(__name__)
CORS(app)
load_dotenv()
YELP_API_KEY = os.getenv("YELP_API_KEY")


def make_yelp_request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    try:
        response = requests.get(f"https://api.yelp.com/v3{endpoint}",
                                headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if response.status_code == 401:
            raise Exception("Invalid Yelp API key")
        elif response.status_code == 429:
            raise Exception("Yelp rate limit exceeded")
        else:
            raise Exception(f"Yelp API error: {str(e)}")


def get_search_params() -> Union[Dict[str, any], tuple]:
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")
    term = request.args.get("term") or "restaurants"
    price = request.args.get("price")
    rating = request.args.get("rating", type=float)
    open_now = request.args.get("open_now")

    # Verification of required params
    if not latitude or not longitude:
        return jsonify({"error": "Coordinates required"}), 400

    if price:
        price_list = price.split(",")
        if len(price_list) > 4:
            return jsonify({"error": "Too many prices selected"}), 400
        for price in price_list:
            if price not in {'1', '2', '3', '4'}:
                return jsonify({"error": "Invalid price input"}), 400

    if rating is not None and (rating < 0 or rating > 5):
        return jsonify({"error:": "Invalid rating"}), 400

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "term": term,
    }

    if price:
        params["price"] = price

    if rating:
        params["rating"] = rating

    if open_now and open_now.lower() == "true":
        params["open_now"] = True

    return params


@app.route('/api/random_restaurant', methods=["GET"])
def random_restaurant():
    try:
        params = get_search_params()
        if isinstance(params, tuple):
            return params
        data = make_yelp_request("/businesses/search", params)
        businesses = data.get("businesses", [])

        if not businesses:
            return jsonify({"error": "No restuarants found matching your criteria"}), 404

        if "rating" in params:
            min_rating = params["rating"]
            businesses = [b for b in businesses if b.get('rating', 0) >= min_rating]
            if not businesses:
                return jsonify({"error": "No restaurants found matching your criteria"}), 404

        business = random.choice(businesses)

        # Fetch detailed information including hours
        business_id = business['id']
        details_data = make_yelp_request(f"/businesses/{business_id}", {})

        # Merge the hours information into the business data
        business['hours'] = details_data.get('hours', [])

        return jsonify(business)
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Only runs when executing locally
    app.run(host='localhost', port=5050, debug=True)
