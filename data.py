import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_ACIDITY = 3
DEFAULT_AVG_PRICE = 25
DEFAULT_AMBIANCE = "Quiet & Peaceful"
DEFAULT_RATING_COUNT = 0

# Initialize Firebase (assuming credentials are in the folder or env)
cred_path = os.getenv(
    "FIREBASE_CREDENTIALS", "brewsenseapp-7a2dc-firebase-adminsdk-fbsvc-73d1d00d89.json"
)

try:
    if not firebase_admin._apps:
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credentials file not found: {cred_path}")
            raise FileNotFoundError(f"Firebase credentials file not found: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase initialized successfully")
    else:
        logger.info("Firebase already initialized")
    db = firestore.client()
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}", exc_info=True)
    raise


def _fetch_collection(collection_name):
    
    ref = db.collection(collection_name)
    docs = ref.stream()
    data = []
    for doc in docs:
        doc_data = doc.to_dict()
        # Add document ID as 'id' field (important for drinks and cafes)
        doc_data["id"] = doc.id
        data.append(doc_data)
    logger.info(f"Fetched {len(data)} {collection_name} from Firebase")
    if len(data) == 0:
        logger.warning(f"No {collection_name} found in Firebase collection")
    return data


def fetch_data():
   
    try:
        logger.info("Fetching data from Firebase")
        cafes = _fetch_collection("Cafes")
        drinks = _fetch_collection("Drinks")
        user_preferences = _fetch_collection("preferences")
        return cafes, drinks, user_preferences
    except Exception as e:
        logger.error(f"Error fetching data from Firebase: {str(e)}", exc_info=True)
        raise


def fetch_user_interactions(user_id=None):
   
    try:
        ref = db.collection("user_interactions")
        if user_id:
            query = ref.where("userId", "==", user_id)
            docs = query.stream()
        else:
            docs = ref.stream()

        data = [doc.to_dict() for doc in docs]
        logger.info(
            f"Fetched {len(data)} user interactions"
            + (f" for user {user_id}" if user_id else "")
        )
        return data
    except Exception as e:
        logger.warning(f"Error fetching user interactions: {str(e)}", exc_info=True)
        return []  # Return empty list on error to not break recommendations


def _validate_required_columns(df, required_cols, data_name):
    """Validate that required columns exist in DataFrame."""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Required columns not found in {data_name} data: {missing}")


def _ensure_column_with_default(df, column, default_value, data_name):
    """Ensure column exists, create with default if missing."""
    if column in df.columns:
        df[column] = df[column].fillna(default_value)
    else:
        logger.warning(
            f"{column} column not found in {data_name}, creating with default value"
        )
        df[column] = default_value


def _fit_encoder(values, encoder_name):
    """Fit LabelEncoder with values, handling empty case."""
    unique_values = set(values) if values else set()
    if not unique_values:
        logger.warning(f"No {encoder_name} values found, using 'Unknown'")
        unique_values = {"Unknown"}
    encoder = LabelEncoder()
    encoder.fit(list(unique_values))
    return encoder


def preprocess_data(cafes, drinks, user_preferences):

    try:
        # Create DataFrames
        cafes_df = pd.DataFrame(cafes if cafes else [])
        drinks_df = pd.DataFrame(drinks if drinks else [])
        users_df = pd.DataFrame(user_preferences if user_preferences else [])

        # Log warnings for empty data
        for name, df in [
            ("Cafes", cafes_df),
            ("Drinks", drinks_df),
            ("Users", users_df),
        ]:
            if df.empty:
                logger.warning(f"{name} DataFrame is empty")

        # Clean drinks data - ensure required columns with defaults
        _ensure_column_with_default(
            drinks_df, "ratingCount", DEFAULT_RATING_COUNT, "drinks"
        )
        _ensure_column_with_default(drinks_df, "acidity", DEFAULT_ACIDITY, "drinks")

        # Validate required columns for encoding
        _validate_required_columns(drinks_df, ["type", "roaster"], "drinks")
        _validate_required_columns(
            users_df, ["favoriteCoffeeType", "preferredRoastLevel"], "users"
        )

        # Encode categorical features - fit encoders on union of values
        type_values = set(drinks_df["type"].dropna().unique())
        type_values.update(users_df["favoriteCoffeeType"].dropna().unique())
        le_type = _fit_encoder(type_values, "type")

        roast_values = set(drinks_df["roaster"].dropna().unique())
        roast_values.update(users_df["preferredRoastLevel"].dropna().unique())
        le_roast = _fit_encoder(roast_values, "roast")

        # Transform with safe defaults
        drinks_df["type_encoded"] = le_type.transform(
            drinks_df["type"].fillna("Unknown")
        )
        drinks_df["roaster_encoded"] = le_roast.transform(
            drinks_df["roaster"].fillna("Unknown")
        )
        users_df["type_encoded"] = le_type.transform(
            users_df["favoriteCoffeeType"].fillna("Unknown")
        )
        users_df["roast_encoded"] = le_roast.transform(
            users_df["preferredRoastLevel"].fillna("Unknown")
        )

        # Encode ambiance - collect from users and cafes
        _validate_required_columns(users_df, ["preferredAmbiance"], "users")
        ambiance_values = set(users_df["preferredAmbiance"].dropna().unique())

        # Extract ambiance from cafe tags
        if "tags" in cafes_df.columns:
            ambiance_from_cafes = cafes_df["tags"].apply(
                lambda x: (
                    x[0]
                    if isinstance(x, list) and x and len(x) > 0
                    else DEFAULT_AMBIANCE
                )
            )
        else:
            logger.warning("tags column not found in cafes, using default ambiance")
            ambiance_from_cafes = pd.Series([DEFAULT_AMBIANCE] * len(cafes_df))

        ambiance_values.update(ambiance_from_cafes.unique())
        le_ambiance = _fit_encoder(ambiance_values, "ambiance")

        users_df["ambiance_encoded"] = le_ambiance.transform(
            users_df["preferredAmbiance"].fillna(DEFAULT_AMBIANCE)
        )
        cafes_df["ambiance_encoded"] = le_ambiance.transform(ambiance_from_cafes)

        # Scale numerical features for drinks
        _validate_required_columns(drinks_df, ["acidity", "price"], "drinks")
        scaler = StandardScaler()
        drinks_df[["acidity_scaled", "price_scaled"]] = scaler.fit_transform(
            drinks_df[["acidity", "price"]]
        )

        # Scale numerical features for users
        _validate_required_columns(
            users_df, ["acidityPreference", "budgetPerCup"], "users"
        )
        scaler_users = StandardScaler()
        users_df[["acidity_scaled", "budget_scaled"]] = scaler_users.fit_transform(
            users_df[["acidityPreference", "budgetPerCup"]]
        )

        # Prepare cafe features - calculate avg_price from priceRange
        if "priceRange" in cafes_df.columns:
            cafes_df["avg_price"] = cafes_df["priceRange"].apply(
                lambda x: (
                    (x[0]["min"] + x[0]["max"]) / 2
                    if isinstance(x, list)
                    and x
                    and isinstance(x[0], dict)
                    and "min" in x[0]
                    and "max" in x[0]
                    else DEFAULT_AVG_PRICE
                )
            )
        else:
            logger.warning("priceRange column not found, using default average price")
            cafes_df["avg_price"] = DEFAULT_AVG_PRICE

        # Validate and scale cafe features
        _validate_required_columns(
            cafes_df,
            ["ambiance_encoded", "avg_price", "latitude", "longitude"],
            "cafes",
        )
        cafe_features = cafes_df[
            ["ambiance_encoded", "avg_price", "latitude", "longitude"]
        ]
        scaler_cafe = StandardScaler()
        scaler_cafe.fit_transform(cafe_features)  # Fit scaler for use in app.py

        logger.info("Data preprocessing completed successfully")

        return (
            cafes_df,
            drinks_df,
            users_df,
            le_ambiance,
            scaler,  # For drink price scaling
            scaler_users,  # For user budget scaling
            scaler_cafe,  # For cafe features scaling
        )
    except KeyError as e:
        logger.error(f"Missing required column in data: {str(e)}", exc_info=True)
        raise ValueError(f"Missing required column: {str(e)}")
    except ValueError as e:
        logger.error(f"Data validation error: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in preprocess_data: {str(e)}", exc_info=True)
        raise


# Global variables for data
cafes_df = None
drinks_df = None
users_df = None
le_ambiance = None
scaler = None
scaler_users = None
scaler_cafe = None


def load_data():
   
    global cafes_df, drinks_df, users_df
    global le_ambiance, scaler, scaler_users, scaler_cafe

    try:
        logger.info("Loading data from Firebase...")
        cafes, drinks, user_preferences = fetch_data()
        (
            cafes_df,
            drinks_df,
            users_df,
            le_ambiance,
            scaler,
            scaler_users,
            scaler_cafe,
        ) = preprocess_data(cafes, drinks, user_preferences)
        logger.info(
            f"Data loaded successfully: {len(cafes_df)} cafes, {len(drinks_df)} drinks, {len(users_df)} users"
        )
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}", exc_info=True)
        raise


# Load data on startup
try:
    load_data()
except Exception as e:
    logger.critical(f"Failed to load data on startup: {str(e)}", exc_info=True)
    # Don't raise here - allow app to start but endpoints will handle empty data
