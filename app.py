import streamlit as st
import os
import json
import time
import requests
from datetime import datetime
import random
import openai

# Configure OpenAI API (you'll need to set up your own API key)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure page
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add CSS for better styling
st.markdown("""
<style>
.chat-message {
    padding: 1.5rem; 
    border-radius: 0.5rem; 
    margin-bottom: 1rem; 
    display: flex;
    flex-direction: column;
}
.chat-message.user {
    background-color: #f0f2f6;
}
.chat-message.assistant {
    background-color: #e6f7ff;
}
.chat-message .message-content {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
}
.chat-message .avatar {
    min-width: 40px;
    margin-right: 1rem;
}
.chat-header {
    text-align: center;
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    margin-bottom: 1rem;
}
.itinerary-day {
    margin-top: 1rem;
    margin-bottom: 1.5rem;
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f8f9fa;
    border-left: 4px solid #4CAF50;
}
.stButton button {
    width: 100%;
    border-radius: 2rem;
    background-color: #4CAF50;
    color: white;
}
.export-button {
    background-color: #007bff !important;
}
.new-button {
    background-color: #6c757d !important;
}
.searching-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    color: #666;
}
.search-result {
    background-color: #f5f5f5;
    border-left: 3px solid #007bff;
    padding: 0.8rem;
    margin-bottom: 0.8rem;
    border-radius: 0.3rem;
    font-size: 0.9rem;
}
.info-card {
    background-color: #f8f9fa;
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1rem;
    border-left: 4px solid #17a2b8;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'destination': None,
        'duration': None,
        'budget': None,
        'starting_location': None,
        'interests': [],
        'travel_dates': None,
        'accommodation_prefs': None,
        'dietary_prefs': None,
        'mobility_issues': None,
        'pace_preference': None,
        'group_size': None
    }

if 'planning_phase' not in st.session_state:
    st.session_state.planning_phase = "initial"  # initial, refinement, suggestion, generation

if 'approved_suggestions' not in st.session_state:
    st.session_state.approved_suggestions = []

if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None

if 'full_history' not in st.session_state:
    st.session_state.full_history = []

if 'search_history' not in st.session_state:
    st.session_state.search_history = []

if 'cached_searches' not in st.session_state:
    st.session_state.cached_searches = {}

# System prompts based on planning phase
SYSTEM_PROMPTS = {
    "initial": """You are TravelBuddy, an intelligent travel planning assistant. You're starting a new conversation with a user. 
    
Welcome them warmly and ask for basic trip details including destination, travel dates, budget, and interests. 
Extract any information they've already provided and ask about missing details.

Be proactive, helpful, and conversational. When you identify travel preferences, acknowledge them clearly.
""",
    
    "refinement": """You are TravelBuddy, an intelligent travel planning assistant. You now have basic information about the user's trip, but need more specific preferences.

The user profile so far includes:
{user_profile_str}

Ask about any missing details, including:
1. Accommodation preferences (hotels, hostels, vacation rentals, etc.)
2. Dietary preferences or restrictions
3. Mobility issues to consider when planning activities
4. Activity pace preference (relaxed with free time or packed itinerary)
5. Travel composition (solo, couple, family, group)

Be conversational and explain why these details help create a better itinerary.
""",
    
    "suggestion": """You are TravelBuddy, an intelligent travel planning assistant. Based on the user's preferences, suggest relevant attractions, activities, and experiences at their destination.

The user profile includes:
{user_profile_str}

Using this destination data:
{destination_data}

Group suggestions by category (cultural, outdoor, food, etc.) and provide brief explanations of why each matches their interests. 
Be thoughtful in your recommendations, considering their specific preferences like budget level, interests, and any mobility issues.

Ask if the suggestions seem appropriate before proceeding to itinerary creation.
""",
    
    "generation": """You are TravelBuddy, an intelligent travel planning assistant. Create a detailed day-by-day itinerary based on the user's preferences.

The user profile includes:
{user_profile_str}

Using this destination data:
{destination_data}

Additional real-time data from web searches:
{search_results}

Create a comprehensive itinerary with:
1. A day-by-day breakdown of activities
2. Realistic timing that considers travel between locations
3. A mix of activities that match their interests
4. Restaurant recommendations suitable for their dietary preferences
5. Estimated costs for activities and meals
6. Transportation suggestions between locations
7. Free time blocks if they prefer a relaxed pace
8. Accommodation recommendations

Format this as a well-structured markdown document with clear headings, bullet points where appropriate, and a professional travel itinerary layout.
Include practical travel tips specific to the destination at the end.
""",

    "modification": """You are TravelBuddy, an intelligent travel planning assistant. The user wants to modify their itinerary.

Original itinerary:
{current_itinerary}

User profile:
{user_profile_str}

Using this destination data:
{destination_data}

Additional real-time data from web searches:
{search_results}

Modify the itinerary based on the user's feedback. Be thoughtful and maintain the overall structure while incorporating their changes.
Format the revised itinerary as a well-structured markdown document with clear headings, bullet points where appropriate.
"""
}

# Real web search function using SerpAPI (you need to set up your own API key)
def search_web(query, num_results=3):
    """
    Search the web for real-time information using SerpAPI or similar service.
    """
    # Check cache first
    cache_key = query.lower().strip()
    if cache_key in st.session_state.cached_searches:
        return st.session_state.cached_searches[cache_key]
    
    try:
        # In production, replace with actual API call
        # Example using SerpAPI:
        # api_key = os.getenv("SERPAPI_KEY")
        # params = {
        #     "engine": "google",
        #     "q": query,
        #     "api_key": api_key,
        #     "num": num_results
        # }
        # response = requests.get("https://serpapi.com/search", params=params)
        # results = response.json().get("organic_results", [])
        
        # Simulate API call and delay for demo
        time.sleep(1.5)
        
        # Generate mock search results based on query keywords
        results = []
        
        if "weather" in query.lower():
            results.append({
                "title": f"Current Weather for {query.replace('weather', '').strip()}",
                "snippet": f"Generally favorable conditions with temperatures ranging from 18°C to 25°C. Occasional light showers possible in the afternoon. Best to pack layers and a light rain jacket.",
                "link": "https://weather.example.com"
            })
        
        if any(x in query.lower() for x in ["flight", "airplane", "airport"]):
            results.append({
                "title": f"Flight Information for {query.replace('flights', '').strip()}",
                "snippet": "Multiple daily flights available. Average flight time is 8.5 hours direct. Consider booking at least 3 months in advance for the best rates. Major carriers include Lufthansa, British Airways, and Delta.",
                "link": "https://flights.example.com"
            })
            
        if any(x in query.lower() for x in ["hotel", "accommodation", "stay", "resort"]):
            results.append({
                "title": f"Top Rated Accommodations in {query.replace('hotels', '').strip()}",
                "snippet": "Wide range of options from budget hostels (€30-50/night) to luxury hotels (€200+/night). Most central accommodations book quickly during high season (June-August). Consider boutique hotels in residential areas for better value.",
                "link": "https://hotels.example.com"
            })
            
        if any(x in query.lower() for x in ["restaurant", "food", "eat", "dining"]):
            results.append({
                "title": f"Best Dining Options in {query.replace('restaurants', '').strip()}",
                "snippet": "Local specialties include seafood paella and tapas. Most restaurants open for dinner around 8pm. Reservations recommended for popular establishments. Many places offer fixed price lunch menus ('menu del día') for €10-15.",
                "link": "https://restaurants.example.com"
            })
            
        if any(x in query.lower() for x in ["attraction", "sight", "museum", "visit"]):
            results.append({
                "title": f"Top Tourist Attractions in {query.replace('attractions', '').strip()}",
                "snippet": "Major attractions include the historic cathedral (€10 entry), the national museum (free on Sundays), and the botanical gardens (€5 entry). Purchase city passes for discounts on multiple attractions. Many sites closed on Mondays.",
                "link": "https://attractions.example.com"
            })
            
        if any(x in query.lower() for x in ["transport", "bus", "train", "subway", "metro"]):
            results.append({
                "title": f"Transportation Guide for {query.replace('transportation', '').strip()}",
                "snippet": "Public transportation includes extensive metro and bus networks. Tourist travel cards available for 1-7 days (€8-40). Taxis readily available but expect to pay premium rates during night hours. Ride-sharing services operate in most urban areas.",
                "link": "https://transport.example.com"
            })
        
        if any(x in query.lower() for x in ["event", "festival", "concert", "show"]):
            results.append({
                "title": f"Upcoming Events in {query.replace('events', '').strip()}",
                "snippet": "Annual film festival takes place in May. Summer months feature weekly outdoor concerts in the central park (often free). Traditional harvest festival celebrated in September with local food and music.",
                "link": "https://events.example.com"
            })
        
        # If no specific matches, return generic travel information
        if not results:
            results = [
                {
                    "title": f"Travel Guide for {query}",
                    "snippet": "Popular destination with tourists year-round. Peak season is June to August with higher prices and crowds. Spring and fall offer pleasant weather with fewer tourists. Some attractions have seasonal opening hours.",
                    "link": "https://travel.example.com"
                },
                {
                    "title": f"Travel Tips for {query}",
                    "snippet": "Local currency is Euro. Credit cards widely accepted but carry some cash for small vendors. Tipping customary at 5-10% in restaurants. Basic phrases in the local language appreciated by residents.",
                    "link": "https://tips.example.com"
                }
            ]
        
        # Store in cache
        st.session_state.cached_searches[cache_key] = results
        
        # Add to search history
        st.session_state.search_history.append({
            "query": query,
            "results": results,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return results
        
    except Exception as e:
        print(f"Search error: {e}")
        return [{
            "title": "Search Error",
            "snippet": "Unable to retrieve information at this time. Using cached destination data instead.",
            "link": "#"
        }]

# Real-time travel data function (currency exchange, weather, events)
def get_real_time_data(destination):
    """
    Get real-time travel data like currency exchange rates, weather forecast, and current events.
    """
    try:
        # In production, replace with actual API calls to currency, weather, and events APIs
        # Simulate API call and delay for demo
        time.sleep(1)
        
        # Mock data based on destination
        now = datetime.now()
        
        data = {
            "currency_exchange": {
                "japan": {"rate": 160.5, "currency": "Japanese Yen (JPY)", "trend": "stable"},
                "italy": {"rate": 0.92, "currency": "Euro (EUR)", "trend": "rising"},
                "france": {"rate": 0.92, "currency": "Euro (EUR)", "trend": "rising"},
                "default": {"rate": 1.0, "currency": "varies", "trend": "unknown"}
            },
            "weather_forecast": {
                "japan": [
                    {"date": (now.strftime("%b %d")), "condition": "Partly Cloudy", "temp_high": 22, "temp_low": 16, "precipitation": "20%"},
                    {"date": ((now.day + 1) % 28), "condition": "Sunny", "temp_high": 24, "temp_low": 17, "precipitation": "10%"},
                    {"date": ((now.day + 2) % 28), "condition": "Sunny", "temp_high": 25, "temp_low": 18, "precipitation": "5%"},
                    {"date": ((now.day + 3) % 28), "condition": "Rain", "temp_high": 20, "temp_low": 16, "precipitation": "80%"},
                    {"date": ((now.day + 4) % 28), "condition": "Cloudy", "temp_high": 21, "temp_low": 15, "precipitation": "30%"}
                ],
                "italy": [
                    {"date": (now.strftime("%b %d")), "condition": "Sunny", "temp_high": 26, "temp_low": 18, "precipitation": "5%"},
                    {"date": ((now.day + 1) % 28), "condition": "Sunny", "temp_high": 27, "temp_low": 19, "precipitation": "0%"},
                    {"date": ((now.day + 2) % 28), "condition": "Partly Cloudy", "temp_high": 25, "temp_low": 18, "precipitation": "20%"},
                    {"date": ((now.day + 3) % 28), "condition": "Partly Cloudy", "temp_high": 24, "temp_low": 17, "precipitation": "30%"},
                    {"date": ((now.day + 4) % 28), "condition": "Sunny", "temp_high": 26, "temp_low": 18, "precipitation": "10%"}
                ],
                "france": [
                    {"date": (now.strftime("%b %d")), "condition": "Cloudy", "temp_high": 18, "temp_low": 12, "precipitation": "40%"},
                    {"date": ((now.day + 1) % 28), "condition": "Rain", "temp_high": 16, "temp_low": 11, "precipitation": "70%"},
                    {"date": ((now.day + 2) % 28), "condition": "Partly Cloudy", "temp_high": 19, "temp_low": 13, "precipitation": "30%"},
                    {"date": ((now.day + 3) % 28), "condition": "Sunny", "temp_high": 21, "temp_low": 14, "precipitation": "10%"},
                    {"date": ((now.day + 4) % 28), "condition": "Sunny", "temp_high": 22, "temp_low": 15, "precipitation": "5%"}
                ],
                "default": [
                    {"date": (now.strftime("%b %d")), "condition": "Varies", "temp_high": 22, "temp_low": 15, "precipitation": "30%"},
                    {"date": ((now.day + 1) % 28), "condition": "Varies", "temp_high": 23, "temp_low": 16, "precipitation": "20%"},
                    {"date": ((now.day + 2) % 28), "condition": "Varies", "temp_high": 22, "temp_low": 15, "precipitation": "25%"},
                    {"date": ((now.day + 3) % 28), "condition": "Varies", "temp_high": 21, "temp_low": 14, "precipitation": "30%"},
                    {"date": ((now.day + 4) % 28), "condition": "Varies", "temp_high": 22, "temp_low": 15, "precipitation": "20%"}
                ]
            },
            "current_events": {
                "japan": [
                    {"name": "Cherry Blossom Festival", "dates": "Mar 20 - Apr 15", "location": "Various parks", "description": "Annual celebration of cherry blossoms with special illuminations and events"},
                    {"name": "Sumo Tournament", "dates": "May 10 - May 24", "location": "Ryogoku Kokugikan, Tokyo", "description": "Major sumo wrestling tournament held three times a year in Tokyo"}
                ],
                "italy": [
                    {"name": "Venice Film Festival", "dates": "Aug 28 - Sep 7", "location": "Venice", "description": "One of the world's oldest and most prestigious film festivals"},
                    {"name": "Palio di Siena", "dates": "Jul 2 & Aug 16", "location": "Siena", "description": "Historic horse race held twice each summer in the main square"}
                ],
                "france": [
                    {"name": "Cannes Film Festival", "dates": "May 14 - May 25", "location": "Cannes", "description": "World-renowned film festival showcasing new films from around the world"},
                    {"name": "Tour de France", "dates": "Jun 29 - Jul 21", "location": "Various routes", "description": "Famous annual multiple stage bicycle race"}
                ],
                "default": [
                    {"name": "Local Festival", "dates": "Varies", "location": "Main city center", "description": "Traditional local celebration with food, music, and cultural activities"},
                    {"name": "Art Exhibition", "dates": "Ongoing", "location": "National Museum", "description": "Collection of works by local and international artists"}
                ]
            }
        }
        
        # Get data for destination or default
        destination_key = destination.lower() if destination.lower() in data["currency_exchange"] else "default"
        
        return {
            "currency": data["currency_exchange"][destination_key],
            "weather": data["weather_forecast"][destination_key],
            "events": data["current_events"][destination_key]
        }
        
    except Exception as e:
        print(f"Real-time data error: {e}")
        return {
            "currency": {"rate": 1.0, "currency": "Unknown", "trend": "unavailable"},
            "weather": [{"date": "Today", "condition": "Unknown", "temp_high": 0, "temp_low": 0, "precipitation": "0%"}],
            "events": [{"name": "Information unavailable", "dates": "N/A", "location": "N/A", "description": "Could not retrieve current events"}]
        }

# Mock travel information database
def search_travel_information(query, user_profile):
    """
    Search for travel information in our mock database.
    In a production app, this would query a real database or API.
    """
    destination = user_profile.get('destination', '').lower()
    budget_level = user_profile.get('budget', 'mid-range').lower()
    interests = [interest.lower() for interest in user_profile.get('interests', [])]
    
    # Mock destination database (simplified from earlier code for brevity)
    destinations = {
        "japan": {
            "description": "Japan is a fascinating blend of traditional culture and cutting-edge technology.",
            "visa_requirements": "Tourists from many countries can visit Japan for up to 90 days without a visa.",
            "language": "Japanese is the official language. English is taught in schools but not widely spoken outside major tourist areas.",
            "currency": "Japanese Yen (JPY)",
            "time_zone": "Japan Standard Time (UTC+9)",
            "attractions": [
                {"name": "Tokyo Skytree", "type": "urban", "description": "One of the tallest towers in the world offering panoramic views of Tokyo", "location": "Tokyo", "cost": "¥3,000 ($20)", "suitable_for": ["sightseeing", "photography"]},
                {"name": "Fushimi Inari Shrine", "type": "cultural", "description": "Famous shrine with thousands of vermilion torii gates", "location": "Kyoto", "cost": "Free", "suitable_for": ["cultural", "hiking", "photography"]},
                {"name": "Mount Fuji", "type": "natural", "description": "Japan's highest mountain and iconic symbol", "location": "Shizuoka/Yamanashi", "cost": "Free to view, ¥5,000+ ($35+) to climb", "suitable_for": ["nature", "hiking", "adventure"]}
            ],
            "restaurants": [
                {"name": "Sukiyabashi Jiro", "type": "sushi", "location": "Tokyo", "cost": "Luxury", "dietary_options": ["pescatarian"]},
                {"name": "Ichiran Ramen", "type": "ramen", "location": "Multiple locations", "cost": "Budget", "dietary_options": ["non-vegetarian"]}
            ]
        },
        "italy": {
            "description": "Italy offers a perfect blend of history, art, cuisine, and stunning landscapes.",
            "visa_requirements": "EU citizens can enter freely. Many non-EU citizens can stay up to 90 days without a visa.",
            "language": "Italian is the official language. English is commonly spoken in tourist areas.",
            "currency": "Euro (EUR)",
            "time_zone": "Central European Time (UTC+1), Central European Summer Time (UTC+2)",
            "attractions": [
                {"name": "Colosseum", "type": "historical", "description": "Ancient Roman amphitheater", "location": "Rome", "cost": "€16 ($17)", "suitable_for": ["history buffs", "photography"]},
                {"name": "Vatican Museums", "type": "cultural", "description": "World-class art collection including Sistine Chapel", "location": "Vatican City", "cost": "€17 ($18)", "suitable_for": ["art lovers", "history buffs"]}
            ],
            "restaurants": [
                {"name": "Da Enzo al 29", "type": "Roman cuisine", "location": "Rome", "cost": "Mid-range", "dietary_options": ["vegetarian options"]},
                {"name": "50 Kalò", "type": "Pizza", "location": "Naples", "cost": "Budget", "dietary_options": ["vegetarian options"]}
            ]
        },
        "france": {
            "description": "France enchants visitors with its elegance, rich history, and world-class cuisine.",
            "visa_requirements": "EU citizens can enter freely. Many non-EU citizens need a Schengen visa.",
            "language": "French is the official language. English is widely spoken in tourist areas.",
            "currency": "Euro (EUR)",
            "time_zone": "Central European Time (UTC+1), Central European Summer Time (UTC+2)",
            "attractions": [
                {"name": "Eiffel Tower", "type": "landmark", "description": "Iconic iron tower in central Paris", "location": "Paris", "cost": "€26 ($28) to summit", "suitable_for": ["sightseeing", "romance", "photography"]},
                {"name": "Louvre Museum", "type": "cultural", "description": "World's largest art museum housing Mona Lisa", "location": "Paris", "cost": "€17 ($18)", "suitable_for": ["art lovers", "history buffs", "culture"]}
            ],
            "restaurants": [
                {"name": "L'Ambroisie", "type": "Fine dining", "location": "Paris", "cost": "Luxury", "dietary_options": ["customized menu"]},
                {"name": "Chez Janou", "type": "Bistro", "location": "Paris", "cost": "Mid-range", "dietary_options": ["vegetarian options"]}
            ]
        }
    }
    
    # Add more destinations as needed...
    
    # Default data if destination not in database
    if destination.lower() not in destinations:
        return {
            "description": "Destination information not available.",
            "attractions": [],
            "restaurants": [],
            "transportation": []
        }
    
    return destinations[destination.lower()]

# Function to extract user profile information from conversation
def extract_user_profile(messages):
    """
    Extract structured user profile data from conversation history.
    In a production app, this would use more sophisticated NLP.
    """
    # Placeholder for a more sophisticated extraction system
    # For demo purposes, we'll use simple keyword matching
    
    user_text = " ".join([msg["content"] for msg in messages if msg["role"] == "user"])
    profile = st.session_state.user_profile.copy()
    
    # Look for destination
    destinations = ["japan", "tokyo", "kyoto", "italy", "rome", "venice", "florence", "france", "paris", "nice"]
    for destination in destinations:
        if destination.lower() in user_text.lower():
            if destination.lower() in ["tokyo", "kyoto"]:
                profile["destination"] = "Japan"
            elif destination.lower() in ["rome", "venice", "florence"]:
                profile["destination"] = "Italy"
            elif destination.lower() in ["paris", "nice"]:
                profile["destination"] = "France"
            else:
                profile["destination"] = destination.title()
            break
    
    # Look for duration
    duration_patterns = [
        r"(\d+)\s*days?",
        r"(\d+)\s*weeks?",
        r"for\s+(\d+)\s+nights"
    ]
    for pattern in duration_patterns:
        import re
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            duration = match.group(1)
            if "week" in match.group(0).lower():
                duration = str(int(duration) * 7) + " days"
            else:
                duration = duration + " days"
            profile["duration"] = duration
            break
    
    # Look for budget
    budget_keywords = {
        "budget": ["budget", "cheap", "affordable", "inexpensive", "economical", "low cost"],
        "mid-range": ["mid-range", "moderate", "average", "middle"],
        "luxury": ["luxury", "high-end", "expensive", "five-star", "premium", "deluxe"]
    }
    
    for budget_level, keywords in budget_keywords.items():
        for keyword in keywords:
            if keyword in user_text.lower():
                profile["budget"] = budget_level
                break
        if profile["budget"]:
            break
    
    # Look for interests
    interest_keywords = {
        "culture": ["culture", "museum", "history", "art", "architecture"],
        "nature": ["nature", "hiking", "outdoors", "landscape", "mountain", "beach", "wildlife"],
        "food": ["food", "dining", "cuisine", "restaurant", "gastronomy", "culinary"],
        "adventure": ["adventure", "thrill", "action", "adrenaline", "extreme"],
        "relaxation": ["relax", "spa", "peaceful", "quiet", "retreat", "tranquil"],
        "shopping": ["shopping", "shop", "market", "souvenir", "mall"],
        "nightlife": ["nightlife", "bar", "club", "entertainment", "party"],
        "photography": ["photo", "photography", "camera", "instagram"]
    }
    
    interests = []
    for interest, keywords in interest_keywords.items():
        for keyword in keywords:
            if keyword in user_text.lower() and interest not in interests:
                interests.append(interest)
                break
    
    if interests:
        profile["interests"] = interests
    
    # Look for travel dates
    date_patterns = [
        r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})",  # MM/DD/YYYY or DD/MM/YYYY
        r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*-\s*|\s+to\s+)([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?",  # March 15th to April 2nd
        r"([A-Za-z]+)\s+(\d{4})"  # March 2023
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            profile["travel_dates"] = match.group(0)
            break
    
    # Look for group size
    group_patterns = [
        r"(\d+)\s*people",
        r"(\d+)\s*of us",
        r"(\d+)\s*travelers",
        r"with my (\w+)",  # family, partner, etc.
        r"(solo|alone|myself)"
    ]
    
    for pattern in group_patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            if match.group(1).lower() in ["solo", "alone", "myself"]:
                profile["group_size"] = "Solo traveler"
            elif match.group(1).lower() == "family":
                profile["group_size"] = "Family"
            elif match.group(1).lower() in ["partner", "wife", "husband", "spouse", "girlfriend", "boyfriend"]:
                profile["group_size"] = "Couple"
            else:
                try:
                    num_people = int(match.group(1))
                    profile["group_size"] = f"Group of {num_people}"
                except ValueError:
                    profile["group_size"] = match.group(0)
            break
    
    # Accommodation preferences
    accom_keywords = {
        "hotel": ["hotel", "resort", "5-star", "4-star", "3-star"],
        "hostel": ["hostel", "dormitory"],
        "airbnb": ["airbnb", "vacation rental", "apartment", "flat"],
        "guesthouse": ["guesthouse", "bed and breakfast", "b&b", "inn"],
        "camping": ["camping", "campsite", "tent", "rv", "campervan"]
    }
    
    for accom_type, keywords in accom_keywords.items():
        for keyword in keywords:
            if keyword in user_text.lower():
                profile["accommodation_prefs"] = accom_type
                break
        if profile.get("accommodation_prefs"):
            break
    
    # Look for dietary preferences
    diet_keywords = {
        "vegetarian": ["vegetarian", "no meat"],
        "vegan": ["vegan", "plant-based", "no animal products"],
        "halal": ["halal"],
        "kosher": ["kosher"],
        "gluten-free": ["gluten-free", "celiac", "coeliac"],
        "dairy-free": ["dairy-free", "lactose intolerant"],
        "no restrictions": ["anything", "everything", "no restrictions", "not picky"]
    }
    
    for diet_type, keywords in diet_keywords.items():
        for keyword in keywords:
            if keyword in user_text.lower():
                profile["dietary_prefs"] = diet_type
                break
        if profile.get("dietary_prefs"):
            break
    
    # Look for mobility issues
    mobility_phrases = [
        "wheelchair", "limited mobility", "walking difficulty", "mobility issues", 
        "can't walk far", "can't walk long", "accessible", "disability"
    ]
    
    for phrase in mobility_phrases:
        if phrase in user_text.lower():
            profile["mobility_issues"] = True
            break
    
    # Look for pace preference
    pace_keywords = {
        "relaxed": ["relaxed", "slow pace", "leisurely", "not rushed", "plenty of free time", "downtime"],
        "balanced": ["balanced", "moderate pace", "mix of activities", "some free time"],
        "intensive": ["intensive", "fast pace", "packed", "busy", "full schedule", "see everything"]
    }
    
    for pace_type, keywords in pace_keywords.items():
        for keyword in keywords:
            if keyword in user_text.lower():
                profile["pace_preference"] = pace_type
                break
        if profile.get("pace_preference"):
            break
    
    return profile

def determine_planning_phase(messages, user_profile):
    """
    Determine which planning phase we're in based on conversation history.
    """
    if not messages:
        return "initial"
    
    # Count how many fields are filled in the user profile
    filled_fields = sum(1 for value in user_profile.values() if value)
    total_fields = len(user_profile)
    
    # If we have enough basic info, move to refinement
    if filled_fields >= 3 and user_profile.get("destination") and user_profile.get("duration"):
        if filled_fields >= 6:
            return "suggestion"
        else:
            return "refinement"
    
    return "initial"

# Function to generate response from OpenAI API
def generate_ai_response(messages, planning_phase, user_profile, itinerary=None):
    """
    Generate AI response using the OpenAI API.
    """
    # Format the prompt based on planning phase
    user_profile_str = "\n".join([f"{key}: {value}" for key, value in user_profile.items() if value])
    
    # Get destination information if available
    destination_data = {}
    if user_profile.get("destination"):
        destination_data = search_travel_information("", user_profile)
    destination_data_str = json.dumps(destination_data, indent=2)
    
    # Get search results for generation phase
    search_results = []
    if planning_phase == "generation" or planning_phase == "modification":
        # Perform targeted searches based on user profile
        destination = user_profile.get("destination", "")
        if destination:
            search_results.extend(search_web(f"top attractions in {destination}"))
            search_results.extend(search_web(f"best restaurants in {destination}"))
            search_results.extend(search_web(f"transportation in {destination}"))
            search_results.extend(search_web(f"weather in {destination}"))
            
            # Add interest-specific searches
            for interest in user_profile.get("interests", []):
                search_results.extend(search_web(f"{interest} activities in {destination}"))
    
    search_results_str = json.dumps(search_results, indent=2)
    
    # Create system prompt based on phase
    system_prompt = SYSTEM_PROMPTS[planning_phase].format(
        user_profile_str=user_profile_str,
        destination_data=destination_data_str,
        search_results=search_results_str,
        current_itinerary=itinerary or ""
    )
    
    formatted_messages = [{"role": "system", "content": system_prompt}]
    formatted_messages.extend(messages)
    
    try:
        # In a production app, use the actual OpenAI API call:
        # response = openai.ChatCompletion.create(
        #    model="gpt-4",
        #    messages=formatted_messages,
        #    temperature=0.7,
        #    max_tokens=1000
        # )
        # return response['choices'][0]['message']['content']
        
        # For demo purposes, simulate API response
        time.sleep(2)  # Simulate API delay
        
        # Mock responses based on planning phase
        if planning_phase == "initial":
            return """Welcome to TravelBuddy! 👋 I'm here to help you plan an amazing trip.

Based on what you've shared, I see you're interested in visiting **{destination}**. That's a wonderful choice!

To create a personalized itinerary, I need a few more details:
- How long are you planning to stay?
- When are you thinking of traveling?
- What's your approximate budget level (budget, mid-range, luxury)?
- What are your main interests for this trip (culture, food, nature, adventure, relaxation)?

The more you can tell me, the better I can tailor recommendations to your preferences!""".format(destination=user_profile.get("destination", "your destination"))
        
        elif planning_phase == "refinement":
            return """Thanks for sharing those details! I'm getting a better picture of your trip to **{destination}** for **{duration}**.

To fine-tune your itinerary, could you help me understand:
- What type of accommodation do you prefer (hotels, hostels, vacation rentals)?
- Do you have any dietary preferences or restrictions I should consider for restaurant recommendations?
- Are there any mobility issues I should be aware of when suggesting activities?
- Do you prefer a relaxed pace with free time, or a packed itinerary to see as much as possible?
- Will you be traveling solo, as a couple, or in a group?

These details will help me create a truly personalized experience for you!""".format(destination=user_profile.get("destination", "your destination"), duration=user_profile.get("duration", "your stay"))
        
        elif planning_phase == "suggestion":
            return """Based on your preferences for **{destination}**, here are some suggestions that match your interests:

**Cultural Experiences:**
- Visit the historic city center (UNESCO World Heritage site)
- Explore the National Museum (budget-friendly on Sundays)
- Take a guided walking tour of the old quarter

**Outdoor Activities:**
- Hike in the nearby mountains for spectacular views
- Relax at the public gardens near the city center
- Take a day trip to the nearby coastal area

**Food & Dining:**
- Try local specialties at the central market
- Book a food tour to sample regional cuisine
- Visit the wine region for tastings

**Shopping & Entertainment:**
- Browse the artisan shops in the historic district
- Catch a traditional performance at the city theater
- Visit the night market for unique souvenirs

Do these suggestions align with your interests? Would you like me to focus more on certain categories or add different types of activities? Once you're happy with the general direction, I'll craft a detailed daily itinerary.
""".format(destination=user_profile.get("destination", "your destination"))
        
        elif planning_phase == "generation" or planning_phase == "modification":
            return """# Your Personalized {duration} Itinerary for {destination}

## Overview
I've created a custom itinerary based on your preferences for {budget} travel with interests in {interests}. This plan includes a {pace} pace with plenty of {main_interest} experiences.

## Day 1: Arrival and Orientation
* **Morning**: Arrival at {destination} Airport/Station
* **Afternoon**: Check-in at {accommodation} ({accommodation_area})
  * Recommended: {hotel_name} (${hotel_price}/night)
* **Evening**: Welcome dinner at {restaurant} - local cuisine with {view_type} views (${dinner_price}/person)
  * Dietary options available: {dietary_options}

## Day 2: City Exploration
* **Morning**: Guided walking tour of {historic_area} (${tour_price})
  * Highlights: {highlight1}, {highlight2}, {highlight3}
* **Afternoon**: Visit to {museum} (${museum_price})
* **Evening**: Dinner at {dinner_place} followed by {evening_activity}

## Day 3: Cultural Immersion
* **Morning**: {morning_activity}
* **Afternoon**: {afternoon_activity}
* **Evening**: {evening_activity}

## Practical Information
* **Weather**: Expect temperatures between {temp_low}°C and {temp_high}°C with {weather_condition}
* **Transportation**: {transport_tip}
* **Local Customs**: {custom_tip}
* **Emergency Contacts**: {emergency_info}

## Estimated Budget
Total estimated cost: ${total_cost} ({budget} category)
* Accommodation: ${accommodation_cost}
* Meals: ${meal_cost}
* Activities: ${activities_cost}
* Transportation: ${transportation_cost}

I hope you enjoy your personalized itinerary! Would you like me to adjust any aspects of this plan?
""".format(
                destination=user_profile.get("destination", "your destination"),
                duration=user_profile.get("duration", "7-day"),
                budget=user_profile.get("budget", "mid-range"),
                interests=", ".join(user_profile.get("interests", ["culture", "food"])),
                pace=user_profile.get("pace_preference", "balanced"),
                main_interest=user_profile.get("interests", ["cultural"])[0] if user_profile.get("interests") else "cultural",
                accommodation=user_profile.get("accommodation_prefs", "hotel"),
                accommodation_area="city center",
                hotel_name="Central Plaza Hotel",
                hotel_price=random.randint(100, 300),
                restaurant="Seaside Terrace",
                view_type="ocean",
                dinner_price=random.randint(30, 80),
                dietary_options=user_profile.get("dietary_prefs", "various options"),
                historic_area="Old Town",
                tour_price=random.randint(15, 50),
                highlight1="Historic Cathedral",
                highlight2="Main Square",
                highlight3="Ancient Walls",
                museum="National Gallery",
                museum_price=random.randint(10, 25),
                dinner_place="Local Bistro",
                evening_activity="sunset walk along the promenade",
                morning_activity="Workshop on local crafts",
                afternoon_activity="Visit to the historic castle",
                evening_activity="Traditional music performance",
                temp_low=random.randint(15, 20),
                temp_high=random.randint(21, 30),
                weather_condition="occasional showers",
                transport_tip="Public transportation is efficient, consider getting a 3-day pass",
                custom_tip="Tipping is customary at 10-15% in restaurants",
                emergency_info="Local emergency number: 112",
                total_cost=random.randint(800, 2500),
                accommodation_cost=random.randint(300, 1000),
                meal_cost=random.randint(200, 600),
                activities_cost=random.randint(100, 500),
                transportation_cost=random.randint(50, 200)
            )
        
        else:
            return "I'm processing your request. Let me know if you have any specific questions about your trip planning."
            
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm having trouble processing your request. Please try again or rephrase your question."

# Main app layout and functionality
def main():
    # Header
    st.markdown('<div class="chat-header"><h1>✈️ AI Travel Planner</h1></div>', unsafe_allow_html=True)
    
    # Create columns for layout
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Sidebar for user profile and controls
        st.subheader("Your Trip Details")
        
        # Trip summary card
        profile_summary = ""
        if st.session_state.user_profile.get('destination'):
            profile_summary += f"**Destination:** {st.session_state.user_profile['destination']}\n\n"
        if st.session_state.user_profile.get('duration'):
            profile_summary += f"**Duration:** {st.session_state.user_profile['duration']}\n\n"
        if st.session_state.user_profile.get('travel_dates'):
            profile_summary += f"**Dates:** {st.session_state.user_profile['travel_dates']}\n\n"
        if st.session_state.user_profile.get('budget'):
            profile_summary += f"**Budget:** {st.session_state.user_profile['budget']}\n\n"
        if st.session_state.user_profile.get('interests'):
            profile_summary += f"**Interests:** {', '.join(st.session_state.user_profile['interests'])}\n\n"
        
        if profile_summary:
            st.markdown(profile_summary)
        else:
            st.write("Start chatting to build your travel profile")
        
        # Planning phase indicator
        planning_phases = {
            "initial": "🔍 Gathering Basic Information",
            "refinement": "🔎 Refining Preferences",
            "suggestion": "💡 Suggesting Activities",
            "generation": "📝 Creating Itinerary"
        }
        
        current_phase = planning_phases.get(st.session_state.planning_phase, "🔍 Planning Phase")
        st.markdown(f"**Current Stage:** {current_phase}")
        
        # Real-time travel data
        if st.session_state.user_profile.get('destination'):
            st.subheader("Destination Insights")
            
            # Get real-time data
            with st.spinner("Loading destination insights..."):
                travel_data = get_real_time_data(st.session_state.user_profile['destination'])
            
            # Display weather
            st.markdown("**Weather Forecast**")
            weather_html = "<div style='font-size:0.9em'>"
            for day in travel_data["weather"][:3]:  # Show only next 3 days
                weather_html += f"<div style='margin-bottom:8px;'><strong>{day['date']}</strong>: {day['condition']}, {day['temp_low']}°C to {day['temp_high']}°C</div>"
            weather_html += "</div>"
            st.markdown(weather_html, unsafe_allow_html=True)
            
            # Display currency
            st.markdown("**Currency**")
            currency_html = f"<div style='font-size:0.9em'><strong>{travel_data['currency']['currency']}</strong><br>1 USD = {travel_data['currency']['rate']} {travel_data['currency']['currency'].split()[0]}<br>Trend: {travel_data['currency']['trend']}</div>"
            st.markdown(currency_html, unsafe_allow_html=True)
            
            # Display events
            if travel_data["events"]:
                st.markdown("**Upcoming Events**")
                events_html = "<div style='font-size:0.9em'>"
                for event in travel_data["events"][:2]:  # Show only top 2 events
                    events_html += f"<div style='margin-bottom:8px;'><strong>{event['name']}</strong><br>{event['dates']}<br>{event['location']}</div>"
                events_html += "</div>"
                st.markdown(events_html, unsafe_allow_html=True)
        
        # Search box for travel information
        st.subheader("Research Your Trip")
        search_query = st.text_input("Search for travel information:", placeholder="E.g., Best time to visit Paris")
        
        if search_query:
            with st.spinner("Searching for information..."):
                results = search_web(search_query)
                
            if results:
                for result in results:
                    st.markdown(f"""<div class="search-result">
                        <div style="font-weight:bold;">{result['title']}</div>
                        <div>{result['snippet']}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.write("No results found. Try a different search term.")
        
        # Button to start a new trip
        if st.button("Start New Trip", key="new_trip", help="Clear current plan and start over"):
            st.session_state.messages = []
            st.session_state.user_profile = {key: None for key in st.session_state.user_profile}
            st.session_state.planning_phase = "initial"
            st.session_state.approved_suggestions = []
            st.session_state.itinerary = None
            st.session_state.full_history = []
            st.session_state.search_history = []
            st.experimental_rerun()
        
        # Export options
        if st.session_state.itinerary:
            # Button to export itinerary as PDF (in a real app, this would generate a PDF)
            if st.button("Export as PDF", key="export_pdf", help="Download your itinerary as PDF"):
                st.balloons()
                st.success("Itinerary exported! (Simulated in this demo)")
            
            # Button to share itinerary (in a real app, this would generate a shareable link)
            if st.button("Share Itinerary", key="share_itinerary", help="Get a shareable link"):
                st.success("Shareable link created! (Simulated in this demo)")
                st.code("https://travel-planner.example.com/shared/trip123456")
    
    # Main chat area
    with col1:
        # Chat interface
        st.subheader("Chat with Your Travel Assistant")
        
        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # React to user input
        if prompt := st.chat_input("Ask about your trip or share your travel preferences..."):
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Extract user profile from messages
            st.session_state.user_profile = extract_user_profile(st.session_state.messages)
            
            # Determine planning phase
            st.session_state.planning_phase = determine_planning_phase(
                st.session_state.messages, 
                st.session_state.user_profile
            )
            
            # Generate assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = generate_ai_response(
                        st.session_state.messages, 
                        st.session_state.planning_phase,
                        st.session_state.user_profile,
                        st.session_state.itinerary
                    )
                    
                    # Check if this is an itinerary (for generation/modification phases)
                    if (st.session_state.planning_phase == "generation" or 
                        st.session_state.planning_phase == "modification") and "# Your Personalized" in response:
                        st.session_state.itinerary = response
                    
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Add to full history
            st.session_state.full_history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_message": prompt,
                "assistant_response": response,
                "planning_phase": st.session_state.planning_phase,
                "user_profile": st.session_state.user_profile.copy()
            })

# Run the app
if __name__ == "__main__":
    main()
