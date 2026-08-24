from flask import Flask, request, jsonify
from flask_cors import CORS
import data  # Import module instead of individual variables to get updated references
from data import (
    load_data,
    fetch_user_interactions,
)
import numpy as np
import pandas as pd
import math
import logging
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# CORS configuration - restrict to specific origins in production
CORS(app, resources={r"/*": {"origins": "*"}})  

# Constants
MAX_RECOMMENDATIONS = 5
MAX_CAFE_RECOMMENDATIONS = 10
MIN_RECOMMENDATIONS = 5
SIMILAR_USERS_COUNT = 5
SIMILAR_CAFES_COUNT = 5

# Scoring weights
CAFE_QUALITY_WEIGHT = 0.15
CAFE_DISTANCE_WEIGHT = 0.10
CAFE_ITEM_MATCH_WEIGHT = 0.20
CAFE_AMBIANCE_MATCH_WEIGHT = 0.20  # Match user's preferred ambiance
CAFE_MENU_MATCH_WEIGHT = 0.15  # Match user's favorite coffee type in cafe menu
CAFE_INTERACTION_WEIGHT = 0.20  # Boost from user interactions
DRINK_TYPE_WEIGHT = 0.4
DRINK_ROAST_WEIGHT = 0.15
DRINK_ACIDITY_WEIGHT = 0.15  # Match user's preferred acidity level
DRINK_COSINE_WEIGHT = 0.15
DRINK_INTERACTION_WEIGHT = 0.15  # Boost from user interactions


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _get_user_safely(user_id):
    """Safely retrieve user, refreshing data if needed."""
    if user_id not in data.users_df["userId"].values:
        logger.info(f"User {user_id} not found, refreshing data")
        load_data()
        if user_id not in data.users_df["userId"].values:
            logger.warning(f"User {user_id} still not found after refresh")
            return None
    
    user_query = data.users_df[data.users_df["userId"] == user_id]
    if user_query.empty:
        logger.warning(f"User {user_id} not found")
        return None
    return user_query.iloc[0]


def _process_user_interactions(user_id):
    
    interactions = fetch_user_interactions(user_id)
    
    favorite_cafes = set()
    favorite_drinks = set()
    cafe_ratings = {}
    drink_ratings = {}
    viewed_cafes = set()
    viewed_drinks = set()
    
    # Process interactions - ratings are processed in chronological order to get latest rating
    def get_timestamp_seconds(interaction):
        """Extract timestamp in seconds from Firestore timestamp."""
        created_at = interaction.get('createdAt')
        if created_at is None:
            return 0
        # Handle Firestore Timestamp object (has .seconds attribute)
        if hasattr(created_at, 'seconds'):
            return created_at.seconds
        # Handle dict format with _seconds key
        if isinstance(created_at, dict):
            return created_at.get('_seconds', 0)
        # Handle datetime object
        if hasattr(created_at, 'timestamp'):
            return int(created_at.timestamp())
        return 0
    
    # Sort by timestamp to process ratings chronologically (latest rating wins)
    for interaction in sorted(interactions, key=get_timestamp_seconds):
        entity_type = interaction.get('entityType', '')
        entity_id = interaction.get('entityId', '')
        interaction_type = interaction.get('interactionType', '')
        metadata = interaction.get('metadata', {})
        
        if entity_type == 'cafe':
            if interaction_type == 'favorite':
                favorite_cafes.add(entity_id)
            elif interaction_type == 'rating' and metadata and 'rating' in metadata:
                cafe_ratings[entity_id] = float(metadata['rating'])
            elif interaction_type == 'view':
                viewed_cafes.add(entity_id)
        elif entity_type == 'drink':
            if interaction_type == 'favorite':
                favorite_drinks.add(entity_id)
            elif interaction_type == 'rating' and metadata and 'rating' in metadata:
                drink_ratings[entity_id] = float(metadata['rating'])
            elif interaction_type == 'view':
                viewed_drinks.add(entity_id)
    
    return {
        'favorite_cafes': favorite_cafes,
        'favorite_drinks': favorite_drinks,
        'cafe_ratings': cafe_ratings,
        'drink_ratings': drink_ratings,
        'viewed_cafes': viewed_cafes,
        'viewed_drinks': viewed_drinks,
    }


def _calculate_cafe_scores(cafes_df, user_lat, user_lng, similar_cafes=None, user_interactions=None, user_favorite_coffee_type=None, user_preferred_ambiance=None):
    """Calculate quality, distance, ambiance match, menu match, interaction, and composite scores for cafes."""
    cafes_df = cafes_df.copy()
    
    # Calculate distance
    cafes_df["distance"] = cafes_df.apply(
        lambda row: haversine_distance(user_lat, user_lng, row["latitude"], row["longitude"]),
        axis=1,
    )
    
    # Calculate quality score
    cafes_df["quality_score"] = cafes_df["rating"] * np.log(
        cafes_df["number_rating"].astype(int) + 1
    )
    
    # Calculate distance score
    max_distance = cafes_df["distance"].max() if len(cafes_df) > 0 else 10
    cafes_df["distance_score"] = 1 / (1 + cafes_df["distance"] / max_distance)
    
    # Calculate ambiance match score (check if cafe ambiance matches user's preferred ambiance)
    cafes_df["ambiance_match"] = 0.0
    if user_preferred_ambiance is not None:
        cafes_df["ambiance_match"] = (cafes_df["ambiance_encoded"] == user_preferred_ambiance).astype(float)
    
    # Calculate menu match score (check if user's favorite coffee type is in cafe's menu)
    cafes_df["menu_match"] = 0.0
    if user_favorite_coffee_type:
        for idx, row in cafes_df.iterrows():
            menu = row.get('menu', [])
            if isinstance(menu, list) and user_favorite_coffee_type in menu:
                cafes_df.at[idx, "menu_match"] = 1.0
    
    # Calculate interaction score based on user behavior
    cafes_df["interaction_score"] = 0.0
    if user_interactions:
        favorite_cafes = user_interactions.get('favorite_cafes', set())
        cafe_ratings = user_interactions.get('cafe_ratings', {})
        viewed_cafes = user_interactions.get('viewed_cafes', set())
        
        for idx, row in cafes_df.iterrows():
            cafe_id = str(row.get('id', ''))
            score = 0.0
            
            # Boost for favorites (strong signal)
            if cafe_id in favorite_cafes:
                score += 0.5
            
            # Boost for high ratings (user liked it)
            if cafe_id in cafe_ratings:
                rating = cafe_ratings[cafe_id]
                score += (rating / 5.0) * 0.3  # Normalize to 0-0.3
            
            # Small boost for viewed (user showed interest)
            if cafe_id in viewed_cafes:
                score += 0.1
            
            cafes_df.at[idx, "interaction_score"] = min(score, 1.0)  # Cap at 1.0
    
    # Normalize quality score
    max_quality = cafes_df["quality_score"].max()
    quality_normalized = cafes_df["quality_score"] / max_quality if max_quality > 0 else cafes_df["quality_score"] * 0
    
    # Normalize interaction score
    max_interaction = cafes_df["interaction_score"].max()
    interaction_normalized = cafes_df["interaction_score"] / max_interaction if max_interaction > 0 else cafes_df["interaction_score"]
    
    # Calculate composite score
    if similar_cafes is not None:
        cafes_df["item_based_match"] = cafes_df["id"].isin(similar_cafes["id"].values).astype(float)
        cafes_df["composite_score"] = (
            CAFE_QUALITY_WEIGHT * quality_normalized
            + CAFE_DISTANCE_WEIGHT * cafes_df["distance_score"]
            + CAFE_ITEM_MATCH_WEIGHT * cafes_df["item_based_match"]
            + CAFE_AMBIANCE_MATCH_WEIGHT * cafes_df["ambiance_match"]
            + CAFE_MENU_MATCH_WEIGHT * cafes_df["menu_match"]
            + CAFE_INTERACTION_WEIGHT * interaction_normalized
        )
    else:
        cafes_df["composite_score"] = (
            0.15 * quality_normalized 
            + 0.10 * cafes_df["distance_score"]
            + 0.20 * cafes_df["ambiance_match"]
            + 0.15 * cafes_df["menu_match"]
            + 0.20 * interaction_normalized
        )
    
    return cafes_df


def _calculate_drink_scores(recommendations, pref_type, pref_roast, user_interactions=None, user_acidity_preference=None):
    """Calculate type match, roast match, acidity match, cosine score, interaction score, and final score for drinks."""
    recommendations = recommendations.copy()
    
    # Calculate binary matches (0 or 1)
    recommendations["type_match"] = (recommendations["type_encoded"] == pref_type).astype(float)
    recommendations["roast_match"] = (recommendations["roaster_encoded"] == pref_roast).astype(float)
    
    # Calculate acidity match score (0-1 based on how close drink acidity is to user preference)
    recommendations["acidity_match"] = 0.0
    if user_acidity_preference is not None:
        # Calculate similarity based on absolute difference (1-5 scale)
        # Perfect match (difference = 0) = 1.0, max difference (4) = 0.0
        acidity_diff = abs(recommendations["acidity"] - user_acidity_preference)
        # Normalize to 0-1: 1 - (diff / 4), where 4 is max possible difference
        recommendations["acidity_match"] = (1.0 - (acidity_diff / 4.0)).clip(0.0, 1.0)
    
    logger.debug(f"Scoring {len(recommendations)} drinks: type_match={recommendations['type_match'].sum()}, roast_match={recommendations['roast_match'].sum()}, acidity_match_avg={recommendations['acidity_match'].mean():.2f}")
    
    # Normalize cosine similarity to 0-1 range
    if len(recommendations) > 0:
        min_cos = recommendations["cosine_similarity"].min()
        max_cos = recommendations["cosine_similarity"].max()
        cos_range = max_cos - min_cos if max_cos > min_cos else 1
        
        if cos_range > 0:
            recommendations["cosine_score"] = (recommendations["cosine_similarity"] - min_cos) / cos_range
        else:
            # All drinks have same cosine similarity, use the actual value (clamped to 0-1)
            recommendations["cosine_score"] = min(max_cos, 1.0) if max_cos >= 0 else 0.0
    else:
        recommendations["cosine_score"] = 0.0
    
    # Calculate interaction score based on user behavior
    recommendations["interaction_score"] = 0.0
    if user_interactions:
        favorite_drinks = user_interactions.get('favorite_drinks', set())
        drink_ratings = user_interactions.get('drink_ratings', {})
        viewed_drinks = user_interactions.get('viewed_drinks', set())
        
        for idx, row in recommendations.iterrows():
            drink_id = str(row.get('id', ''))
            drink_name = str(row.get('name', ''))
            score = 0.0
            
            # Try both ID and name matching (in case ID is missing)
            entity_id = drink_id if drink_id and drink_id != 'nan' else drink_name
            
            # Boost for favorites (strong signal)
            if entity_id in favorite_drinks or drink_id in favorite_drinks or drink_name in favorite_drinks:
                score += 0.5
            
            # Boost for high ratings (user liked it)
            if entity_id in drink_ratings or drink_id in drink_ratings or drink_name in drink_ratings:
                rating = drink_ratings.get(entity_id) or drink_ratings.get(drink_id) or drink_ratings.get(drink_name, 0)
                score += (rating / 5.0) * 0.3  # Normalize to 0-0.3
            
            # Small boost for viewed (user showed interest)
            if entity_id in viewed_drinks or drink_id in viewed_drinks or drink_name in viewed_drinks:
                score += 0.1
            
            recommendations.at[idx, "interaction_score"] = min(score, 1.0)  # Cap at 1.0
    
    # Normalize interaction score
    max_interaction = recommendations["interaction_score"].max()
    if max_interaction > 0:
        interaction_normalized = recommendations["interaction_score"] / max_interaction
    else:
        # If no interactions, set all to 0 (no boost)
        interaction_normalized = recommendations["interaction_score"].copy()
    
    # Calculate final score using weighted combination
    recommendations["final_score"] = (
        DRINK_TYPE_WEIGHT * recommendations["type_match"] +
        DRINK_ROAST_WEIGHT * recommendations["roast_match"] +
        DRINK_ACIDITY_WEIGHT * recommendations["acidity_match"] +
        DRINK_COSINE_WEIGHT * recommendations["cosine_score"] +
        DRINK_INTERACTION_WEIGHT * interaction_normalized
    )
    
    # Log scoring summary for debugging
    if len(recommendations) > 0:
        logger.debug(
            f"Drink scoring summary: "
            f"final_score range=[{recommendations['final_score'].min():.3f}, {recommendations['final_score'].max():.3f}], "
            f"avg_type_match={recommendations['type_match'].mean():.2f}, "
            f"avg_roast_match={recommendations['roast_match'].mean():.2f}, "
            f"avg_cosine={recommendations['cosine_score'].mean():.3f}, "
            f"avg_interaction={interaction_normalized.mean():.3f}"
        )
    
    return recommendations


def is_cafe_open(working_time):
    """Check if cafe is currently open based on working time schedule."""
    if not working_time or not isinstance(working_time, list) or not working_time:
        return False
    now = datetime.now()
    current_time = now.hour * 60 + now.minute  # minutes since midnight
    for schedule in working_time:
        opens = schedule.get("opens", "")
        closes = schedule.get("closes", "")
        try:
            opens_hour, opens_min = map(int, opens.split(":"))
            closes_hour, closes_min = map(int, closes.split(":"))
            opens_minutes = opens_hour * 60 + opens_min
            closes_minutes = closes_hour * 60 + closes_min
            if closes_minutes < opens_minutes:  # wraps to next day
                if current_time >= opens_minutes or current_time < closes_minutes:
                    return True
            else:
                if opens_minutes <= current_time < closes_minutes:
                    return True
        except ValueError:
            continue
    return False


@app.route("/recommend/cafes", methods=["POST"])
def recommend_cafes():
    try:
        # Get request data (validation handled in Flutter app)
        request_data = request.json or {}
        user_id = request_data.get("user_id")
        user_lat = request_data.get("latitude")
        user_lng = request_data.get("longitude")

        # Check if dataframes are empty
        if data.users_df.empty or data.cafes_df.empty:
            logger.error("Dataframes are empty")
            return jsonify({"error": "No data available"}), 503

        # Get user safely
        user = _get_user_safely(user_id)
        if user is None:
            return jsonify([])

        # Fetch and process user interactions
        user_interactions = _process_user_interactions(user_id)
        logger.info(f"User {user_id} interactions: {len(user_interactions['favorite_cafes'])} favorite cafes, {len(user_interactions['cafe_ratings'])} cafe ratings")

        # User-Based: Find similar users using cosine similarity
        user_features = data.users_df[
            [
                "type_encoded",
                "roast_encoded",
                "acidity_scaled",
                "budget_scaled",
                "ambiance_encoded",
            ]
        ].values
        user_vector = np.array([[
            user["type_encoded"],
            user["roast_encoded"],
            user["acidity_scaled"],
            user["budget_scaled"],
            user["ambiance_encoded"],
        ]])
        
        # Calculate cosine similarity between current user and all users
        user_similarities = cosine_similarity(user_vector, user_features)[0]
        
        # Get top N most similar users (excluding the user themselves)
        user_indices = np.argsort(user_similarities)[::-1]  # Sort descending
        # Exclude the user themselves (they should be most similar to themselves)
        user_indices = [idx for idx in user_indices if data.users_df.iloc[idx]["userId"] != user["userId"]][:SIMILAR_USERS_COUNT]
        if not user_indices:
            logger.warning(f"No similar users found for user {user_id}")
            # Fallback to user's own preference
            avg_ambiance = user["ambiance_encoded"]
        else:
            similar_users = data.users_df.iloc[user_indices]
            
            # Weight similar users by cosine similarity (higher similarity = more weight)
            weights = user_similarities[user_indices]
            weights = weights / weights.sum() if weights.sum() > 0 else np.ones(len(weights)) / len(weights)  # Normalize weights
            
            # Weighted aggregation of ambiance preferences
            ambiance_values = similar_users["ambiance_encoded"].values
            weighted_ambiance = np.average(ambiance_values, weights=weights)
            # Round to nearest integer for encoding match
            avg_ambiance = int(np.round(weighted_ambiance))
            # Fallback to user's own preference if invalid
            if avg_ambiance not in data.cafes_df["ambiance_encoded"].values:
                avg_ambiance = user["ambiance_encoded"]

        # Item-Based: Use cosine similarity for cafe recommendations
        cafe_features = data.cafes_df[["ambiance_encoded", "avg_price", "latitude", "longitude"]].values
        user_cafe_vector = np.array([[
            user["ambiance_encoded"],
            user["budgetPerCup"],
            user_lat,
            user_lng
        ]])
        # Scale the vector using the same scaler used for cafes
        user_cafe_vector_scaled = data.scaler_cafe.transform(user_cafe_vector)
        cafe_features_scaled = data.scaler_cafe.transform(data.cafes_df[["ambiance_encoded", "avg_price", "latitude", "longitude"]])
        
        # Calculate cosine similarity between user cafe preferences and all cafes
        cafe_similarities = cosine_similarity(user_cafe_vector_scaled, cafe_features_scaled)[0]
        
        # Get top similar cafes
        cafe_indices = np.argsort(cafe_similarities)[::-1][:SIMILAR_CAFES_COUNT]
        similar_cafes = data.cafes_df.iloc[cafe_indices]

        # Combine user-based and item-based: Start with cafes matching user preferences
        filtered_cafes = data.cafes_df[
            (data.cafes_df["ambiance_encoded"] == avg_ambiance)
            & (data.cafes_df["avg_price"] <= user["budgetPerCup"])
        ].copy()
        
        # If not enough cafes, include item-based recommendations
        if len(filtered_cafes) < MIN_RECOMMENDATIONS:
            item_based_cafes = similar_cafes.copy()
            # Combine and remove duplicates
            filtered_cafes = pd.concat([filtered_cafes, item_based_cafes]).drop_duplicates(subset=['id'])
            # Re-filter by budget
            filtered_cafes = filtered_cafes[filtered_cafes["avg_price"] <= user["budgetPerCup"]]

        # Get user's favorite coffee type for menu matching
        user_favorite_coffee_type = user.get("favoriteCoffeeType")
        # Get user's preferred ambiance for ambiance matching
        user_preferred_ambiance = user.get("ambiance_encoded")
        
        # Calculate scores for filtered cafes (including interaction boost, ambiance match, and menu match)
        filtered_cafes = _calculate_cafe_scores(filtered_cafes, user_lat, user_lng, similar_cafes, user_interactions, user_favorite_coffee_type, user_preferred_ambiance)
        recommendations = filtered_cafes.sort_values("composite_score", ascending=False)

        # Ensure minimum recommendations
        if len(recommendations) < MIN_RECOMMENDATIONS:
            # Fallback: Use all cafes with simplified scoring (including interactions, ambiance match, and menu match)
            recommendations = _calculate_cafe_scores(data.cafes_df, user_lat, user_lng, None, user_interactions, user_favorite_coffee_type, user_preferred_ambiance)
            recommendations = recommendations.sort_values("composite_score", ascending=False).head(MIN_RECOMMENDATIONS)
        else:
            recommendations = recommendations.head(MAX_CAFE_RECOMMENDATIONS)

        # Ensure 'id' column exists and is not null - use index as fallback if missing
        if "id" not in recommendations.columns:
            logger.warning("'id' column missing, generating from index")
            recommendations["id"] = recommendations.index.astype(str)
        elif recommendations["id"].isna().any():
            logger.warning("Some cafes missing 'id', filling with index")
            recommendations["id"] = recommendations["id"].fillna(
                recommendations.index.astype(str)
            )
        # Ensure id is string type
        recommendations["id"] = recommendations["id"].astype(str)

        # Format priceRange as string
        recommendations["priceRange"] = recommendations["priceRange"].apply(
            lambda x: (
                f"{x[0]['min']}-{x[0]['max']}" if isinstance(x, list) and x else "20-40"
            )
        )
        recommendations["distance"] = recommendations["distance"].astype(str)
        recommendations["isOpen"] = recommendations["workingTime"].apply(is_cafe_open)
        recommendations["openingHours"] = recommendations["workingTime"].apply(
            lambda wt: (
                f"{wt[0]['opens']} - {wt[0]['closes']}"
                if wt and isinstance(wt, list) and wt
                else "7:00 AM - 10:00 PM"
            )
        )

        result = recommendations[
            [
                "id",
                "name",
                "location",
                "distance",
                "latitude",
                "longitude",
                "tags",
                "priceRange",
                "rating",
                "timeEstimate",
                "imageUrl",
                "isOpen",
                "openingHours",
            ]
        ].to_dict("records")
        logger.info(f"Generated {len(result)} cafe recommendations for user {user_id}")
        return jsonify(result)
    except KeyError as e:
        logger.error(f"KeyError in recommend_cafes: {str(e)}", exc_info=True)
        return jsonify({"error": "Invalid data structure"}), 500
    except ValueError as e:
        logger.error(f"ValueError in recommend_cafes: {str(e)}", exc_info=True)
        return jsonify({"error": "Invalid input data"}), 400
    except Exception as e:
        logger.error(f"Unexpected error in recommend_cafes: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/recommend/drinks", methods=["POST"])
def recommend_drinks():
    try:
        # Get request data (validation handled in Flutter app)
        request_data = request.json or {}
        user_id = request_data.get("user_id")

        logger.info(f"Received drink recommendation request for user: {user_id}")

        # Check if dataframes are empty
        if data.users_df.empty or data.drinks_df.empty:
            logger.error("Dataframes are empty")
            return jsonify({"error": "No data available"}), 503

        # Get user safely
        user = _get_user_safely(user_id)
        if user is None:
            return jsonify([])
        
        logger.info(f"Generating recommendations for user: {user_id}")

        # Fetch and process user interactions
        user_interactions = _process_user_interactions(user_id)
        logger.info(f"User {user_id} interactions: {len(user_interactions['favorite_drinks'])} favorite drinks, {len(user_interactions['drink_ratings'])} drink ratings")

        # Preferred type, roast, and acidity from the user
        pref_type = user["type_encoded"]
        pref_roast = user["roast_encoded"]
        user_acidity_preference = user.get("acidityPreference")

        # Item-Based: Find drinks similar to preferred type/roast
        # Properly scale user values to match drink feature space
        # The scaler was fit on drinks[["acidity", "price"]], so we need to scale
        # user's raw acidityPreference and budgetPerCup using the same scaler
        user_features_df = pd.DataFrame(
            [[user["acidityPreference"], user["budgetPerCup"]]],
            columns=["acidity", "price"]
        )
        user_features_scaled = data.scaler.transform(user_features_df)[0]
        user_acidity_scaled_for_drinks = user_features_scaled[0]
        user_budget_scaled_for_drinks = user_features_scaled[1]
        
        # Create user preference vector for cosine similarity
        user_vector = np.array([[
            pref_type,
            pref_roast,
            user_acidity_scaled_for_drinks,  # Properly scaled for drink feature space
            user_budget_scaled_for_drinks,  # Properly scaled for drink feature space
        ]])
        
        # FIRST: Get ALL drinks matching user's favorite type and roast (exact matches)
        # This ensures we prioritize drinks that match user preferences exactly
        exact_matches = data.drinks_df[
            (data.drinks_df["type_encoded"] == pref_type) &
            (data.drinks_df["roaster_encoded"] == pref_roast) &
            (data.drinks_df["price"] <= user["budgetPerCup"])
        ].copy()
        
        # Get drinks matching favorite type (any roast) - exclude exact matches
        excluded_indices = set(exact_matches.index)
        type_matches = data.drinks_df[
            (data.drinks_df["type_encoded"] == pref_type) &
            (data.drinks_df["price"] <= user["budgetPerCup"]) &
            (~data.drinks_df.index.isin(excluded_indices))
        ].copy()
        
        # Get drinks matching roast (any type) - exclude exact and type matches
        excluded_indices.update(type_matches.index)
        roast_matches = data.drinks_df[
            (data.drinks_df["roaster_encoded"] == pref_roast) &
            (data.drinks_df["price"] <= user["budgetPerCup"]) &
            (~data.drinks_df.index.isin(excluded_indices))
        ].copy()
        
        # Get all other drinks within budget - exclude all previous matches
        excluded_indices.update(roast_matches.index)
        all_drinks = data.drinks_df[
            (data.drinks_df["price"] <= user["budgetPerCup"]) &
            (~data.drinks_df.index.isin(excluded_indices))
        ].copy()
        
        # Calculate cosine similarity for all drinks
        # Prepare drink feature vectors
        drink_features = data.drinks_df[["type_encoded", "roaster_encoded", "acidity_scaled", "price_scaled"]].values
        
        # Calculate cosine similarity between user vector and all drinks
        cosine_similarities = cosine_similarity(user_vector, drink_features)[0]
        
        # Create a mapping from index to cosine similarity (avoid mutating global dataframe)
        cosine_sim_map = dict(zip(data.drinks_df.index, cosine_similarities))
        
        # Assign cosine similarity scores to all match groups
        for match_group in [exact_matches, type_matches, roast_matches]:
            match_group["cosine_similarity"] = match_group.index.map(
                lambda idx: cosine_sim_map.get(idx, 0.0)
            )
        
        # Combine matches in priority order
        total_matches = len(exact_matches) + len(type_matches) + len(roast_matches)
        if total_matches >= MAX_RECOMMENDATIONS:
            recommendations = pd.concat([exact_matches, type_matches, roast_matches]).drop_duplicates(
                subset=['id'] if 'id' in data.drinks_df.columns else ['name']
            )
        else:
            # Add candidates sorted by cosine similarity
            all_drinks["cosine_similarity"] = all_drinks.index.map(
                lambda idx: cosine_sim_map.get(idx, 0.0)
            )
            all_drinks = all_drinks.sort_values("cosine_similarity", ascending=False)
            recommendations = pd.concat([exact_matches, type_matches, roast_matches, all_drinks]).drop_duplicates(
                subset=['id'] if 'id' in data.drinks_df.columns else ['name']
            )
        
        # Calculate scores and sort (including interaction boost)
        recommendations = _calculate_drink_scores(recommendations, pref_type, pref_roast, user_interactions, user_acidity_preference)
        recommendations = recommendations.sort_values(
            ["final_score", "cosine_similarity"], ascending=[False, False]
        )

        # Take top N recommendations
        if len(recommendations) > MAX_RECOMMENDATIONS:
            recommendations = recommendations.head(MAX_RECOMMENDATIONS)
        elif len(recommendations) == 0:
            # Fallback: Use all drinks (relax budget constraint)
            all_drinks = data.drinks_df.copy()
            all_drinks["cosine_similarity"] = all_drinks.index.map(
                lambda idx: cosine_sim_map.get(idx, 0.0)
            )
            all_drinks = all_drinks.sort_values("cosine_similarity", ascending=False)
            recommendations = all_drinks.head(MAX_RECOMMENDATIONS).copy()
            recommendations = _calculate_drink_scores(recommendations, pref_type, pref_roast, user_interactions, user_acidity_preference)
            recommendations = recommendations.sort_values(
                ["final_score", "cosine_similarity"], ascending=[False, False]
            )

        # Calculate match percentage based on final_score (higher score = higher match)
        # Map final_score directly to percentage (0-100% range)
        # Score of 0.556 = 55.6% ≈ 56%
        if len(recommendations) > 0:
            max_score = recommendations["final_score"].max()
            min_score = recommendations["final_score"].min()
            
            # Map score directly to percentage: score * 100
            # Clamp to ensure it stays within 0-100% range
            recommendations["matchPercentage"] = recommendations["final_score"].apply(
                lambda score: f"{int(max(0, min(100, score * 100)))}%"
            )
            
            logger.info(
                f"Match percentages: min_score={min_score:.3f}, max_score={max_score:.3f}, "
                f"sample={recommendations['matchPercentage'].head(3).tolist()}"
            )
        else:
            # No recommendations, shouldn't happen but handle gracefully
            recommendations["matchPercentage"] = "0%"
        
        # Ensure 'id' column exists - use index as fallback if missing
        if "id" not in recommendations.columns:
            logger.warning("'id' column missing in recommendations, generating from index")
            recommendations["id"] = recommendations.index.astype(str)
        elif recommendations["id"].isna().any():
            logger.warning("Some drinks missing 'id', filling with index")
            recommendations["id"] = recommendations["id"].fillna(
                recommendations.index.astype(str)
            )
        # Ensure id is string type
        recommendations["id"] = recommendations["id"].astype(str)
        
        # Remove temporary columns before returning
        result = recommendations[
            [
                "id",
                "name",
                "description",
                "tags",
                "price",
                "rating",
                "preparationTime",
                "imageUrl",
                "isHot",
                "roaster",
                "matchPercentage",
            ]
        ].to_dict("records")
        logger.info(f"Generated {len(result)} recommendations for user {user_id}")
        return jsonify(result)
    except KeyError as e:
        logger.error(f"KeyError in recommend_drinks: {str(e)}", exc_info=True)
        return jsonify({"error": "Invalid data structure"}), 500
    except ValueError as e:
        logger.error(f"ValueError in recommend_drinks: {str(e)}", exc_info=True)
        return jsonify({"error": "Invalid input data"}), 400
    except Exception as e:
        logger.error(f"Unexpected error in recommend_drinks: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/refresh_data", methods=["POST"])
def refresh_data():
    """Refresh data from Firebase. Should be protected in production."""
    try:
        logger.info("Refreshing data from Firebase")
        load_data()
        logger.info("Data refreshed successfully")
        return jsonify({"message": "Data refreshed successfully"}), 200
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to refresh data"}), 500


if __name__ == "__main__":
    debug_mode = True  # Change to False in production
    app.run(host="0.0.0.0", debug=debug_mode, port=5000)
