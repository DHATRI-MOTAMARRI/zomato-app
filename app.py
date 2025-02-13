from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import math
import google.generativeai as genai
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

uri = "mongodb+srv://mdhatri26:Vinayaka%2626@cluster0.6rgez.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client["zomato_restaurants"]
collection = db["restaurants"]

API_KEY = "AIzaSyDnArxi9YkbGGE9UYhxzA8GsvKIXZWRJ9U" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash-exp")


@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# Add route to serve static files (like script.js)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

def calculate_distance(lat1, lon1, lat2, lon2):
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371 # Radius of Earth in kilometers
    return c * r

@app.route('/predict-cuisine', methods=['POST'])
def predict_cuisine():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        image_data = image_file.read()
        
        # Prepare image for Gemini
        image_part = {
            "mime_type": image_file.content_type,
            "data": image_data
        }

        # Get prediction from Gemini
        response = model.generate_content(["What type of cuisine does this image represent? Just respond with the cuisine type ['Afghani', 'African', 'American', 'Andhra', 'Arabian', 'Argentine', 'Armenian', 'Asian', 'Asian Fusion', 'Assamese', 'Australian', 'Awadhi', 'BBQ', 'Bakery', 'Bar Food', 'Belgian', 'Bengali', 'Beverages', 'Bihari', 'Biryani', 'Brazilian', 'Breakfast', 'British', 'Bubble Tea', 'Burger', 'Burmese', 'Bí_rek', 'Cafe', 'Cajun', 'Canadian', 'Cantonese', 'Caribbean', 'Charcoal Grill', 'Chettinad', 'Chinese', 'Coffee and Tea', 'Contemporary', 'Continental', 'Cuban', 'Cuisine Varies', 'Curry', 'Deli', 'Desserts', 'Dim Sum', 'Diner', 'Drinks Only', 'Durban', 'Dí_ner', 'European', 'Fast Food', 'Filipino', 'Finger Food', 'Fish and Chips', 'French', 'Fusion', 'German', 'Goan', 'Gourmet Fast Food', 'Greek', 'Grill', 'Gujarati', 'Hawaiian', 'Healthy Food', 'Hyderabadi', 'Ice Cream', 'Indian', 'Indonesian', 'International', 'Iranian', 'Irish', 'Italian', 'Izgara', 'Japanese', 'Juices', 'Kashmiri', 'Kebab', 'Kerala', 'Kiwi', 'Korean', 'Latin American', 'Lebanese', 'Lucknowi', 'Maharashtrian', 'Malay', 'Malaysian', 'Malwani', 'Mangalorean', 'Mediterranean', 'Mexican', 'Middle Eastern', 'Mineira', 'Mithai', 'Modern Australian', 'Modern Indian', 'Moroccan', 'Mughlai', 'Naga', 'Nepalese', 'New American', 'North Eastern', 'North Indian', 'Oriya', 'Pakistani', 'Parsi', 'Patisserie', 'Peranakan', 'Persian', 'Peruvian', 'Pizza', 'Portuguese', 'Pub Food', 'Rajasthani', 'Ramen', 'Raw Meats', 'Restaurant Cafe', 'Salad', 'Sandwich', 'Scottish', 'Seafood', 'Singaporean', 'Soul Food', 'South African', 'South American', 'South Indian', 'Southern', 'Southwestern', 'Spanish', 'Sri Lankan', 'Steak', 'Street Food', 'Sunda', 'Sushi', 'Taiwanese', 'Tapas', 'Tea', 'Teriyaki', 'Tex-Mex', 'Thai', 'Tibetan', 'Turkish', 'Turkish Pizza', 'Vegetarian', 'Vietnamese', 'Western', 'World Cuisine'].", image_part]
        )
        
        predicted_cuisine = response.text.strip()

        if predicted_cuisine.startswith('[') and predicted_cuisine.endswith(']'):
            
            predicted_cuisine = predicted_cuisine.strip('[]').strip("'").strip('"')
        
        # If multiple cuisines are returned (comma-separated), take the first one
        if ',' in predicted_cuisine:
            predicted_cuisine = predicted_cuisine.split(',')[0].strip()
        
        return jsonify({"cuisine": predicted_cuisine}), 200

    except Exception as e:
        return jsonify({"error": f"Error processing image: {str(e)}"}), 500


@app.route('/restaurant/<string:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    try:
        restaurant = collection.find_one({"_id": ObjectId(restaurant_id)})
        if restaurant:
            restaurant["_id"] = str(restaurant["_id"])
            return jsonify(restaurant), 200
        return jsonify({"error": "Restaurant not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Invalid ID format: {str(e)}"}), 400

@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Get location search parameters
        lat = request.args.get('latitude')
        lon = request.args.get('longitude')
        radius = float(request.args.get('radius', 3.0))  # Default 3km radius
        
        # Get cuisine filter from predicted cuisine
        cuisine = request.args.get('cuisine')

        if lat and lon:
            lat = float(lat)
            lon = float(lon)
            
            # Find all restaurants and filter by distance and cuisine
            query = {}
            if cuisine:
                query = {
                    "restaurant.cuisines": {
                        "$regex": cuisine,
                        "$options": "i"
                    }
                }
            
            all_restaurants = list(collection.find(query))
            filtered_restaurants = []
            
            for restaurant in all_restaurants:
                rest_location = restaurant.get('restaurant', {}).get('location', {})
                rest_lat = float(rest_location.get('latitude', 0))
                rest_lon = float(rest_location.get('longitude', 0))
                
                distance = calculate_distance(lat, lon, rest_lat, rest_lon)
                if distance <= radius:
                    restaurant['distance'] = round(distance, 2)
                    restaurant["_id"] = str(restaurant["_id"])
                    filtered_restaurants.append(restaurant)
            
            filtered_restaurants.sort(key=lambda x: x['distance'])
            
            start_idx = skip
            end_idx = start_idx + limit
            paginated_restaurants = filtered_restaurants[start_idx:end_idx]
            
            return jsonify({
                "page": page,
                "limit": limit,
                "total": len(filtered_restaurants),
                "restaurants": paginated_restaurants
            }), 200
        else:
            # Regular pagination without location filtering, but with cuisine filtering
            query = {}
            if cuisine:
                query = {
                    "restaurant.cuisines": {
                        "$regex": cuisine,
                        "$options": "i"
                    }
                }
            
            restaurants = list(collection.find(query).skip(skip).limit(limit))
            for restaurant in restaurants:
                restaurant["_id"] = str(restaurant["_id"])

            return jsonify({
                "page": page,
                "limit": limit,
                "total": collection.count_documents(query),
                "restaurants": restaurants
            }), 200

    except Exception as e:
        return jsonify({"error": f"Error retrieving data: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)