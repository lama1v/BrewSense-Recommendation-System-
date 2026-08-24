# BrewSense ☕

**AI-Powered Coffee Discovery App for Abha, Saudi Arabia**

BrewSense is a Flutter mobile application that helps users discover personalized coffee recommendations for cafes and drinks in Abha, Saudi Arabia. The app leverages AI-powered recommendation algorithms to provide tailored suggestions based on user preferences, location, and interaction history.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [AI Integration](#-ai-integration)
- [User Flow](#-user-flow)
- [Platform Support](#-platform-support)

---

## ✨ Features

### 🔐 Authentication & Security

- **Email/Password Authentication** via Firebase
- **Email Verification** - Required before accessing the main app
- **Password Management**:
  - Change password with current password verification
  - Forgot password with email reset link (validates email exists in database before sending)
- **Account Deletion** - Complete account removal with automatic data cleanup
- **Account Blocking** - Admin can block/unblock user accounts; blocked users cannot access the app
- **Secure Data Storage** - Firebase Firestore with security rules

### ☕ Coffee Preferences System

The app features a comprehensive preference system that allows users to customize their coffee experience:

- **Preference Setup** (Required onboarding for new users):
  - **Favorite Coffee Type**: Choose from available coffee types (Espresso, Cappuccino, Latte, Americano, etc.)
  - **Preferred Roast Level**: Select from all available roast levels in the dataset 
  - **Acidity Preference**: 1-5 scale slider 
  - **Budget per Cup**: 5-50 SAR range
  - **Preferred Ambiance**: Quiet & Peaceful, Lively & Social, Cozy & Intimate, Modern & Minimalist, or Traditional & Classic

- **Key Features**:
  - **Independent Selection**: Roast level and acidity preferences are independent and show all available options regardless of coffee type selection
  - **Preference Editing**: Update preferences anytime from the profile screen
  - **Preference Validation**: Ensures all preferences are complete before app access
  - **Auto-load**: Saved preferences automatically load when opening preference screens

### 🎯 AI-Powered Recommendations

#### Personalized Cafe Recommendations
- Location-based recommendations sorted by distance
- Match percentage display showing relevance score
- Interactive map view with Google Maps integration
- Quality scoring based on ratings and reviews
- Item-based collaborative filtering
- Real-time open/closed status
- Nearby filter (within 2.0 km radius)
- Filter options: All Cafes, Open Now, Nearby

#### Personalized Drink Recommendations
- "For You" tab with AI-generated recommendations
- Hot/Cold filter toggle
- "Saved" filter for favorited drinks
- Match percentage based on preferences
- Tiered matching system:
  1. Exact matches (type + roast)
  2. Type matches (coffee type)
  3. Roast matches (roast level)
  4. Cosine similarity scoring

### 💬 User Interactions & Analytics

#### Interaction Types
- **Views**: Automatically recorded when viewing cafe/drink details (deduplicated)
- **Favorites**: Save and manage favorite cafes and drinks
- **Ratings**: Rate cafes and drinks on a 1-5 scale (updates existing ratings)
- **Visits**: Record cafe visits (allows multiple visits)

#### Journey Statistics
Track your coffee journey with visual stat cards:
- Cups discovered
- Cafes visited
- Favorites saved
- Average rating given

### 🔒 Privacy & Data Management

- **Privacy Settings**: Granular control over data collection
  - Toggle preference data collection
  - Toggle activity tracking
- **Data Export**: Download all your data as JSON
- **Data Deletion**: Delete all interactions while keeping profile
- **Account Deletion**: Complete removal with full data cleanup

### 👤 User Profile & Settings

- **Profile Management**: View and edit profile information (name, phone)
- **Preference Management**: Edit coffee preferences from profile
- **Journey Statistics**: Visual stats cards with color-coded metrics
- **Theme Settings**: Toggle between light and dark mode
- **Language Settings**: Switch between English and Arabic with full RTL support
- **Change Password**: Secure password change with verification

### 🗺️ Location Features

- **Location-Based Recommendations**: Cafes sorted by proximity
- **Interactive Maps**: Google Maps integration showing cafe locations
- **Distance Display**: Real-time distance from user location
- **Geolocation Services**: Automatic location detection with permissions

### 🌍 Internationalization (i18n)

- **Multi-language Support**: English (en) and Arabic (ar)
- **RTL Support**: Full right-to-left layout for Arabic
- **Localized Content**: All UI text, messages, and error handling translated
- **Locale Management**: Easy language switching with persisted preferences

### 👨‍💼 Admin Features

- **Admin Dashboard**: Manage users and app content with real-time statistics
- **User Management**: 
  - View and manage user accounts
  - Block/unblock users
  - Delete user accounts with confirmation
  - Language switching in admin panel
- **Content Management**: Manage cafes and drinks data
- **Statistics**: View total users, active users, blocked users, and cafe counts

---

## 🏗️ Architecture

### MVVM Pattern with Provider

The app follows the **Model-View-ViewModel (MVVM)** architecture pattern with **Provider** for state management:

```
┌─────────────────────────────────────┐
│           View Layer                │
│    (StatelessWidget - UI Only)     │
└──────────────┬──────────────────────┘
               │ watches (Consumer)
               ▼
┌─────────────────────────────────────┐
│        ViewModel Layer              │
│   (ChangeNotifier - Business Logic) │
└──────────────┬──────────────────────┘
               │ uses
               ▼
┌─────────────────────────────────────┐
│         Service Layer               │
│  (Data Access - Firebase/API)       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│          Model Layer                │
│      (Data Classes/Entities)        │
└─────────────────────────────────────┘
```

### Architecture Principles

- **Separation of Concerns**: Clear boundaries between UI, business logic, and data access
- **Single Responsibility**: Each ViewModel handles one feature's logic
- **Reactive State Management**: Provider enables reactive UI updates
- **Dependency Injection**: Services injected via Provider
- **Testability**: ViewModels can be tested independently

---

## 💻 Technology Stack

### Frontend (Flutter/Dart)

- **Framework**: Flutter SDK 3.9.0+
- **Language**: Dart
- **State Management**: Provider (^6.1.5+1)
- **Localization**: easy_localization (^3.0.8)

### Backend & Services

- **Authentication**: Firebase Authentication
- **Database**: Cloud Firestore
- **AI Engine**: Python Flask REST API (see `AI/` directory)

### Key Dependencies

#### Core
- `firebase_core` ^4.0.0 - Firebase initialization
- `firebase_auth` ^6.0.1 - Authentication
- `cloud_firestore` ^6.0.0 - Database
- `provider` ^6.1.5+1 - State management

#### UI & Styling
- `google_fonts` ^6.2.1 - Custom typography (Poppins)
- `easy_localization` ^3.0.8 - Internationalization

#### Location & Maps
- `geolocator` ^13.0.1 - Location services
- `google_maps_flutter` ^2.5.0 - Map integration

#### Utilities
- `connectivity_plus` ^6.0.0 - Network connectivity checks
- `http` ^1.2.2 - HTTP requests to AI service
- `share_plus` ^10.0.0 - Data sharing
- `logger` ^2.0.0 - Logging utility

---

## 📁 Project Structure

```
brew_sense_app/
├── lib/
│   ├── core/
│   │   ├── constants/
│   │   │   ├── app_colors.dart
│   │   │   └── app_routes.dart
│   │   ├── dataset/
│   │   │   ├── cafes_dataset.dart
│   │   │   └── drinks_dataset.dart
│   │   ├── models/
│   │   │   ├── cafe_model.dart
│   │   │   ├── cafe_dataset_model.dart
│   │   │   ├── drink_model.dart
│   │   │   ├── drink_dataset_model.dart
│   │   │   ├── preference_model.dart
│   │   │   ├── recommendations_input.dart
│   │   │   ├── user_interaction_model.dart
│   │   │   └── user_model.dart
│   │   ├── services/
│   │   │   ├── auth_service.dart
│   │   │   ├── ai_recommendation_service.dart
│   │   │   ├── preference_service.dart
│   │   │   ├── user_interaction_service.dart
│   │   │   └── admin_service.dart
│   │   ├── theme/
│   │   │   └── app_theme.dart
│   │   ├── utils/
│   │   │   ├── error_handler.dart
│   │   │   └── font_utils.dart
│   │   └── widgets/
│   │       ├── bottom_navigation_bar_widget.dart
│   │       ├── custom_button.dart
│   │       ├── custom_elevated_button.dart
│   │       ├── custom_text_form_field.dart
│   │       ├── rating_dialog.dart
│   │       └── saudi_currency_symbol.dart
│   ├── features/
│   │   ├── admin/
│   │   │   ├── view/
│   │   │   │   ├── admin_view.dart
│   │   │   │   └── user_management_view.dart
│   │   │   └── viewmodel/
│   │   │       └── admin_viewmodel.dart
│   │   ├── auth/
│   │   │   ├── view/
│   │   │   │   ├── auth_view.dart
│   │   │   │   └── forgot_password_view.dart
│   │   │   └── viewmodel/
│   │   │       ├── auth_viewmodel.dart
│   │   │       └── forgot_password_viewmodel.dart
│   │   ├── drinks/
│   │   │   ├── view/
│   │   │   │   ├── drinks_view.dart
│   │   │   │   └── drink_detail_view.dart
│   │   │   └── viewmodel/
│   │   │       └── drinks_viewmodel.dart
│   │   ├── home/
│   │   │   ├── view/
│   │   │   │   ├── home_view.dart
│   │   │   │   └── cafe_detail_view.dart
│   │   │   └── viewmodel/
│   │   │       └── home_viewmodel.dart
│   │   ├── preference/
│   │   │   ├── view/
│   │   │   │   └── preference_view.dart
│   │   │   └── viewmodel/
│   │   │       └── preference_viewmodel.dart
│   │   ├── profile/
│   │   │   ├── view/
│   │   │   │   ├── profile_view.dart
│   │   │   │   ├── edit_profile_view.dart
│   │   │   │   └── privacy_view.dart
│   │   │   └── viewmodel/
│   │   │       ├── profile_viewmodel.dart
│   │   │       └── privacy_viewmodel.dart
│   │   └── splash/
│   │       ├── view/
│   │       │   └── splash_view.dart
│   │       └── viewmodel/
│   │           └── splash_viewmodel.dart
│   ├── firebase_options.dart
│   └── main.dart
├── AI/
│   ├── app.py                          # Flask API server
│   ├── data.py                         # Data processing & preprocessing
│   ├── requirements.txt                # Python dependencies
│   └── brewsenseapp-*.json            # Firebase Admin SDK credentials
├── assets/
│   └── translations/
│       ├── en.json                     # English translations
│       └── ar.json                     # Arabic translations
├── android/
├── ios/
└── README.md
```

### Key Components

#### Services Layer
- **AuthService**: Firebase Authentication, user management, email verification
- **AiRecommendationService**: HTTP client for AI recommendation API
- **PreferenceService**: CRUD operations for user preferences in Firestore
- **UserInteractionService**: Records and retrieves user interactions
- **AdminService**: Admin-specific operations

#### ViewModels
- **AuthViewModel**: Authentication state, login/signup flow
- **HomeViewModel**: Cafe recommendations, location management
- **DrinksViewModel**: Drink recommendations, filtering logic
- **PreferenceViewModel**: Preference setup/editing, validation
- **ProfileViewModel**: User profile, statistics aggregation
- **PrivacyViewModel**: Privacy settings, data operations

---



## 🤖 AI Integration

### Overview

The app integrates with a Python Flask-based AI recommendation engine located in the `AI/` directory. The AI service provides personalized recommendations using collaborative filtering, content-based filtering, and cosine similarity.

### API Endpoints

#### POST `/recommend/cafes`

Get personalized cafe recommendations based on user location and preferences.

**Request:**
```json
{
  "user_id": "firebase_user_id",
  "latitude": 18.2164,
  "longitude": 42.5043
}
```

**Response:**
```json
[
  {
    "id": "cafe_id",
    "name": "Cafe Name",
    "location": "Address",
    "distance": "2.5 km",
    "latitude": 18.2200,
    "longitude": 42.5100,
    "tags": ["cozy", "wifi"],
    "priceRange": "20-40",
    "rating": 4.5,
    "timeEstimate": "15 min",
    "imageUrl": "url",
    "isOpen": true,
    "openingHours": "7:00 AM - 10:00 PM"
  }
]
```

#### POST `/recommend/drinks`

Get personalized drink recommendations based on user preferences.

**Request:**
```json
{
  "user_id": "firebase_user_id"
}
```

**Response:**
```json
[
  {
    "id": "drink_id",
    "name": "Drink Name",
    "description": "Description",
    "tags": ["hot", "strong"],
    "price": 15.0,
    "rating": 4.7,
    "ratingCount": 150,
    "acidity": 3,
    "preparationTime": "2-3 min",
    "imageUrl": "url",
    "isHot": true,
    "roaster": "Medium",
    "type": "Espresso",
    "matchPercentage": 85
  }
]
```

#### POST `/refresh_data`

Refresh data from Firebase (used by admin or for data updates).

### Recommendation Algorithm

The AI service uses a hybrid recommendation approach:

1. **Content-Based Filtering**: Matches drinks based on user preferences (type, roast, acidity)
2. **Collaborative Filtering**: Finds similar users and recommends items they liked
3. **Interaction Scoring**: Boosts recommendations based on user interactions (favorites, ratings, views)
4. **Location Scoring**: For cafes, considers distance and quality metrics
5. **Cosine Similarity**: Calculates feature similarity between user preferences and items

---

## 🔄 User Flow

### New User Journey

1. **Splash Screen** → Check authentication status
2. **Authentication** → Sign up/Login with email
3. **Email Verification** → Verify email (required)
4. **Preference Setup** → Set coffee preferences (required)
5. **Home Screen** → View personalized cafe recommendations
6. **Drinks Screen** → Browse personalized drink recommendations
7. **Profile** → View/edit profile, statistics, settings

### Returning User Journey

1. **Splash Screen** → Check authentication and preferences
2. **Home Screen** → Direct access if authenticated with preferences

### Navigation Flow

```
Splash → [Not Authenticated] → Auth
       → [Not Verified] → Auth
       → [No Preferences] → Preference Setup
       → [Ready] → Home
       
Home → Drinks → Profile → Settings
     → Cafe Detail
     → Drink Detail
```

---

## 🎨 Theming

### Theme System

The app supports dynamic theming with light and dark modes:

- **Light Theme**: Default Material Design light theme
- **Dark Theme**: Material Design dark theme
- **Custom Colors**: Defined in `lib/core/constants/app_colors.dart`
- **Typography**: Poppins font family with system font fallback
- **Dialog Theme**: Consistent dialog styling across light and dark modes
- **Responsive Design**: Adaptive layouts for different screen sizes

### Theme Persistence

Theme preference is stored in user profile and persists across app restarts.

---

## 🌐 Localization

### Supported Languages

- **English (en)**: Default language
- **Arabic (ar)**: Full RTL support with right-to-left layout

### Translation Files

- `assets/translations/en.json` - English translations
- `assets/translations/ar.json` - Arabic translations

### Usage in Code

```dart
// Translate text
Text('g_appName'.tr())

// Translate with parameters
Text('pf_member_since'.tr(namedArgs: {'date': dateString}))
```

### Adding New Translations

1. Add key-value pair to both `en.json` and `ar.json`
2. Use the key in code with `.tr()` extension
3. Restart app to see changes (or use hot reload)

---

## 📱 Platform Support

- ✅ **Android** - Full support
- ✅ **iOS** - Full support
- ✅ **Web** - Partial support (basic functionality)

---

## 🔐 Security Features

### Authentication Security

- **Email Verification**: Required before accessing main app
- **Password Requirements**: Minimum 8 characters
- **Secure Password Reset**: 
  - Email-based reset links
  - Validates email exists in database before sending reset link
  - Prevents email enumeration attacks
- **Password Change**: Requires current password verification
- **Account Blocking**: Blocked accounts cannot access the app and are automatically signed out

### Data Security

- **Firestore Security Rules**: Configure appropriate rules for your collections
- **Secure Data Storage**: All sensitive data stored in Firestore
- **Error Handling**: Centralized error handling with user-friendly messages
- **Network Validation**: Connectivity checks before API calls

### Privacy Features

- **Privacy Settings**: User control over data collection
- **Data Export**: Users can download their data
- **Data Deletion**: Users can delete interactions or entire account
- **No Data Sharing**: User data not shared with third parties

---

## 📊 Data Models

### Preference Model

```dart
PreferenceModel {
  userId: String
  favoriteCoffeeType: String          // e.g., "Espresso"
  preferredRoastLevel: String         // e.g., "Medium"
  acidityPreference: int              // 1-5 scale
  budgetPerCup: double                // 5-50 SAR
  preferredAmbiance: String           // e.g., "Quiet & Peaceful"
  createdAt: Timestamp
}
```

### User Interaction Model

```dart
UserInteraction {
  userId: String
  entityId: String                    // Cafe or drink ID
  entityType: String                  // "cafe" or "drink"
  interactionType: String             // "view", "favorite", "rating", "visit"
  rating: int?                        // Optional (1-5)
  createdAt: Timestamp
}
```

### Interaction Deduplication Logic

- **Views**: Updates existing view timestamp (no duplicates per entity)
- **Favorites**: Prevents duplicates (unfavorite deletes favorite record)
- **Ratings**: Updates existing rating (no duplicates, replaces previous)
- **Visits**: Allows duplicates (multiple visits allowed)

---

## 🐛 Error Handling

### Centralized Error Handler

The app uses a centralized `ErrorHandler` utility class:

```dart
// Log error
ErrorHandler.logError('Operation failed', exception);

// Show user-friendly error
ErrorHandler.showErrorSnackBar(context, 'error_message_key'.tr());

// Show success message
ErrorHandler.showSuccessSnackBar(context, 'success_message_key'.tr());
```

### Error Types Handled

- **Network Errors**: Connectivity issues, timeout (30-second timeout for AI service)
- **Firebase Errors**: Authentication, Firestore, storage errors
- **Validation Errors**: Form validation, input errors
- **API Errors**: AI service errors, HTTP errors
- **Database Errors**: Firestore query errors, connection issues
- **Account Errors**: Blocked account detection, email verification status

### User-Friendly Messages

All errors are translated and displayed in user-friendly format using localization keys.

---

## 🔧 Development

### Code Style

- Follows [Flutter Style Guide](https://flutter.dev/docs/development/ui/widgets-intro)
- Uses `flutter_lints` for code quality
- Follows Dart linting rules from `analysis_options.yaml`
- Uses modern Flutter APIs (e.g., `withValues` instead of deprecated `withOpacity`)
- Implements proper BuildContext checks (`context.mounted`) before async operations

### Project Organization

- **Feature-based structure**: Each feature has its own directory
- **Separation of concerns**: View/ViewModel/Service separation
- **Reusable widgets**: Common widgets in `core/widgets/`
- **Constants**: App-wide constants in `core/constants/`
- **Responsive Design**: MediaQuery-based adaptive layouts for all screens
- **Keyboard Handling**: Proper viewInsets handling to prevent content overlap

### Adding New Features

1. Create feature directory in `lib/features/`
2. Add view and viewmodel subdirectories
3. Create route in `app_routes.dart`
4. Add route handler in `main.dart`
5. Create ViewModel provider in `main.dart`
6. Add translations if needed
7. Implement responsive design using `MediaQuery`
8. Add keyboard padding using `viewInsets.bottom`
9. Use theme colors for light/dark mode support


## 📞 Support & Contact

For issues, questions, or contributions:

- **Issues**: Open an issue in the repository
- **Email**: [brewsense11@gmail.com]

---

## 🙏 Acknowledgments

- **Flutter Team** - Amazing cross-platform framework
- **Firebase** - Robust backend services
- **Google Maps** - Location services
- **Coffee Community** - Inspiration for the app

---

**BrewSense** - Discover Your Perfect Cup ☕

*Made with ❤️ for coffee lovers in Abha, Saudi Arabia*
