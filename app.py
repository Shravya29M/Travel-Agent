import streamlit as st
import os
import json
import time
import requests
from datetime import datetime
import random

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

# System prompts based on planning phase
SYSTEM_PROMPTS = {
    "initial": """You are TravelBuddy, an intelligent travel planning assistant. You're starting a new conversation with a user. Welcome them and ask for basic trip details including destination, travel dates, budget, and interests. Extract any information they've already provided and ask about missing details.""",
    
    "refinement": """You are TravelBuddy, an intelligent travel planning assistant. You now have basic information about the user's trip, but need more specific preferences. Ask about accommodation preferences, dietary needs, activity interests, mobility considerations, and travel style. Be conversational and explain why these details help create a better itinerary.""",
    
    "suggestion": """You are TravelBuddy, an intelligent travel planning assistant. Based on the user's preferences, search for and suggest relevant attractions, activities, and experiences at their destination. Group suggestions by category (cultural, outdoor, food, etc.) and provide brief explanations of why each matches their interests. Ask if the suggestions seem appropriate before proceeding to itinerary creation.""",
    
    "generation": """You are TravelBuddy, an intelligent travel planning assistant. Create a detailed day-by-day itinerary based on the user's preferences and approved suggestions. Organize activities logically by location, include realistic timing, balance different interests, and add practical details like estimated costs and travel methods. Format with clear headings and structure."""
}

# Mock web search function (in a real implementation, this would connect to a search API)
def search_travel_information(query, user_profile):
    """
    Simulates retrieving travel information from the web.
    In a real implementation, this would use a search API.
    """
    # Simulate API delay
    time.sleep(1.5)
    
    # Mock data for popular destinations
    mock_data = {
        "japan": {
            "attractions": [
                {"name": "Tokyo Skytree", "description": "Tallest tower in Japan with observation decks", "type": "modern", "cost": "¥3,000"},
                {"name": "Fushimi Inari Shrine", "description": "Famous shrine with thousands of red torii gates", "type": "cultural", "cost": "Free"},
                {"name": "Arashiyama Bamboo Grove", "description": "Stunning path through bamboo forest", "type": "nature", "cost": "Free"},
                {"name": "TeamLab Borderless", "description": "Immersive digital art museum", "type": "modern", "cost": "¥3,200"},
                {"name": "Mount Fuji", "description": "Japan's highest mountain", "type": "nature", "cost": "Varies"}
            ],
            "restaurants": [
                {"name": "Ichiran Ramen", "description": "Famous chain for tonkotsu ramen", "type": "casual", "cost": "¥1,000-2,000"},
                {"name": "Sushi Dai", "description": "Popular sushi restaurant in Tsukiji", "type": "mid-range", "cost": "¥2,500-5,000"},
                {"name": "Tempura Kondo", "description": "Michelin-starred tempura", "type": "luxury", "cost": "¥8,000+"}
            ],
            "accommodations": [
                {"name": "Capsule Hotels", "description": "Unique Japanese budget option", "type": "budget", "cost": "¥2,000-4,000"},
                {"name": "Traditional Ryokan", "description": "Japanese inn with tatami rooms", "type": "mid-range/luxury", "cost": "¥15,000-50,000"},
                {"name": "Business Hotels", "description": "Compact, affordable rooms", "type": "budget/mid-range", "cost": "¥7,000-15,000"}
            ]
        },
        "italy": {
            "attractions": [
                {"name": "Colosseum", "description": "Ancient Roman amphitheater", "type": "historical", "cost": "€16"},
                {"name": "Vatican Museums", "description": "World-class art collection including the Sistine Chapel", "type": "cultural", "cost": "€17"},
                {"name": "Amalfi Coast", "description": "Stunning coastline with picturesque towns", "type": "nature", "cost": "Varies"},
                {"name": "Uffizi Gallery", "description": "Renaissance art museum in Florence", "type": "cultural", "cost": "€20"},
                {"name": "Venice Canals", "description": "Iconic waterways of Venice", "type": "scenic", "cost": "Varies"}
            ],
            "restaurants": [
                {"name": "Pizzeria da Michele", "description": "Famous traditional pizzeria in Naples", "type": "casual", "cost": "€10-15"},
                {"name": "Trattoria Zà Zà", "description": "Popular trattoria in Florence", "type": "mid-range", "cost": "€20-30"},
                {"name": "Osteria Francescana", "description": "Three-Michelin-star restaurant in Modena", "type": "luxury", "cost": "€250+"}
            ],
            "accommodations": [
                {"name": "Agriturismo", "description": "Farm stays in the countryside", "type": "mid-range", "cost": "€70-150"},
                {"name": "Pensione", "description": "Family-run budget hotels", "type": "budget", "cost": "€50-100"},
                {"name": "Luxury Hotels", "description": "High-end accommodations in historic buildings", "type": "luxury", "cost": "€200-500+"}
            ]
        },
        "france": {
            "attractions": [
                {"name": "Eiffel Tower", "description": "Iconic iron tower in Paris", "type": "landmark", "cost": "€17-26"},
                {"name": "Louvre Museum", "description": "World's largest art museum", "type": "cultural", "cost": "€15"},
                {"name": "Mont Saint-Michel", "description": "Medieval monastery on a tidal island", "type": "historical", "cost": "€11"},
                {"name": "Provence Lavender Fields", "description": "Beautiful purple landscapes in summer", "type": "nature", "cost": "Free/Varies"},
                {"name": "French Riviera", "description": "Glamorous Mediterranean coastline", "type": "scenic", "cost": "Varies"}
            ],
            "restaurants": [
                {"name": "Bistrot Paul Bert", "description": "Classic French bistro in Paris", "type": "mid-range", "cost": "€30-50"},
                {"name": "L'As du Fallafel", "description": "Famous falafel shop in Paris", "type": "casual", "cost": "€6-10"},
                {"name": "Le Louis XV", "description": "Alain Ducasse's restaurant in Monaco", "type": "luxury", "cost": "€200+"}
            ],
            "accommodations": [
                {"name": "Gîtes", "description": "Self-catering holiday homes", "type": "budget/mid-range", "cost": "€60-150"},
                {"name": "Boutique Hotels", "description": "Stylish smaller hotels", "type": "mid-range/luxury", "cost": "€120-300"},
                {"name": "Château Hotels", "description": "Historic castle accommodations", "type": "luxury", "cost": "€200-600+"}
            ]
        }
    }
    
    # Default to returning general information if destination not found
    destination = user_profile.get('destination', '').lower()
    if destination:
        for key in mock_data.keys():
            if key in destination:
                return mock_data[key]
    
    # If destination not found, return a generic response
    return {
        "attractions": [
            {"name": "Local Museum", "description": "Cultural heritage museum", "type": "cultural", "cost": "Varies"},
            {"name": "National Park", "description": "Natural beauty spot", "type": "nature", "cost": "Varies"},
            {"name": "Historic District", "description": "Old town with historic buildings", "type": "historical", "cost": "Free"}
        ],
        "restaurants": [
            {"name": "Local Cuisine Restaurant", "description": "Traditional local food", "type": "mid-range", "cost": "Varies"},
            {"name": "Street Food Market", "description": "Variety of affordable options", "type": "casual", "cost": "Varies"}
        ],
        "accommodations": [
            {"name": "City Center Hotels", "description": "Convenient location", "type": "mid-range", "cost": "Varies"},
            {"name": "Budget Hostels", "description": "Affordable option for travelers", "type": "budget", "cost": "Varies"}
        ]
    }

# Extract travel preferences from user messages
def extract_travel_preferences(message):
    """
    Extract travel preferences from user messages using basic keyword matching.
    In a real implementation, this would use NLP or an LLM.
    """
    preferences = {}
    
    # Extract destination
    destinations = {
        "japan": ["japan", "tokyo", "kyoto", "osaka", "hiroshima"],
        "italy": ["italy", "rome", "venice", "florence", "milan", "naples"],
        "france": ["france", "paris", "nice", "lyon", "marseille"]
    }
    
    for destination, keywords in destinations.items():
        if any(keyword in message.lower() for keyword in keywords):
            preferences["destination"] = destination
            break
    
    # Extract duration
    for i in range(1, 31):  # 1 to 30 days
        patterns = [f"{i} day", f"{i} days", f"{i}-day", f"{i} night", f"{i} nights", f"{i}-night"]
        if any(pattern in message.lower() for pattern in patterns):
            preferences["duration"] = i
            break
    
    # Extract budget
    budget_keywords = {
        "budget": ["cheap", "budget", "affordable", "inexpensive"],
        "mid-range": ["moderate", "mid-range", "average"],
        "luxury": ["luxury", "high-end", "expensive", "premium"]
    }
    
    for budget, keywords in budget_keywords.items():
        if any(keyword in message.lower() for keyword in keywords):
            preferences["budget"] = budget
            break
    
    # Extract interests
    interest_keywords = {
        "cultural": ["museum", "history", "art", "culture", "historical"],
        "nature": ["nature", "hiking", "outdoors", "landscape", "mountain", "beach"],
        "food": ["food", "culinary", "dining", "restaurant", "cuisine"],
        "shopping": ["shopping", "market", "shop", "mall"],
        "adventure": ["adventure", "extreme", "thrill", "adrenaline"],
        "relaxation": ["relax", "spa", "peaceful", "quiet"]
    }
    
    interests = []
    for interest, keywords in interest_keywords.items():
        if any(keyword in message.lower() for keyword in keywords):
            interests.append(interest)
    
    if interests:
        preferences["interests"] = interests
    
    return preferences

# Generate AI response
def generate_ai_response(input_text, user_profile, planning_phase):
    """
    Generate AI response based on user input and current planning phase.
    In a real implementation, this would use an AI model API.
    """
    # Get system prompt for current phase
    system_prompt = SYSTEM_PROMPTS[planning_phase]
    
    # Simulate API delay
    time.sleep(2)
    
    # Simulate AI responses based on phase
    if planning_phase == "initial":
        # Extract any provided information
        preferences = extract_travel_preferences(input_text)
        
        # Update user profile
        for key, value in preferences.items():
            user_profile[key] = value
        
        # Generate response based on what we know
        if user_profile.get('destination'):
            return f"Great! I see you're interested in visiting {user_profile['destination'].title()}. " + \
                  (f"And you're planning a {user_profile['duration']}-day trip. " if user_profile.get('duration') else "How long are you planning to stay? ") + \
                  (f"You're looking for a {user_profile['budget']} experience. " if user_profile.get('budget') else "What's your approximate budget for this trip? ") + \
                  (f"You're interested in {', '.join(user_profile['interests'])}. " if user_profile.get('interests') else "What kinds of activities are you interested in? ") + \
                  "When are you planning to travel? This helps me recommend seasonal activities and events."
        else:
            return "Hi there! I'm your AI travel planner. To help create the perfect itinerary, I'll need some basic information. Where are you thinking of traveling to? And for how long? What's your approximate budget level (budget, mid-range, or luxury)? What kinds of activities interest you most?"
    
    elif planning_phase == "refinement":
        # Extract any provided information
        preferences = extract_travel_preferences(input_text)
        
        # Update user profile
        for key, value in preferences.items():
            user_profile[key] = value
            
        return "Thanks for sharing more details! A few more questions to perfect your itinerary:\n\n" + \
               "1. What type of accommodation do you prefer? (hotels, hostels, vacation rentals, etc.)\n" + \
               "2. Do you have any dietary preferences or restrictions I should keep in mind?\n" + \
               "3. Any mobility issues to consider when planning activities?\n" + \
               "4. Do you prefer a relaxed pace with free time, or a packed itinerary?\n" + \
               "5. Are you traveling solo, as a couple, with family, or in a group?"
    
    elif planning_phase == "suggestion":
        # Get destination information
        destination_info = search_travel_information("", user_profile)
        
        # Filter based on user interests
        user_interests = user_profile.get('interests', [])
        
        suggestions = "Based on your preferences, here are some suggestions for your trip:\n\n"
        
        # Add attractions
        suggestions += "**Attractions:**\n"
        for attraction in destination_info.get('attractions', [])[:3]:
            suggestions += f"- **{attraction['name']}**: {attraction['description']} ({attraction['cost']})\n"
        
        # Add restaurants
        suggestions += "\n**Dining:**\n"
        for restaurant in destination_info.get('restaurants', [])[:3]:
            suggestions += f"- **{restaurant['name']}**: {restaurant['description']} ({restaurant['cost']})\n"
        
        # Add accommodations
        suggestions += "\n**Accommodations:**\n"
        for accommodation in destination_info.get('accommodations', [])[:3]:
            suggestions += f"- **{accommodation['name']}**: {accommodation['description']} ({accommodation['cost']})\n"
        
        suggestions += "\nDo these suggestions match your interests? Would you like to see more options or proceed with creating your itinerary?"
        return suggestions
    
    elif planning_phase == "generation":
        # Generate itinerary based on user profile and approved suggestions
        destination = user_profile.get('destination', 'your destination')
        duration = user_profile.get('duration', 3)
        
        itinerary = f"# Your {duration}-Day {destination.title()} Itinerary\n\n"
        
        # Get destination information
        destination_info = search_travel_information("", user_profile)
        
        # Generate day-by-day itinerary
        attractions = destination_info.get('attractions', [])
        restaurants = destination_info.get('restaurants', [])
        
        for day in range(1, duration + 1):
            itinerary += f"## Day {day}\n\n"
            
            # Morning activity
            morning_attraction = attractions[day % len(attractions)]
            itinerary += f"**Morning**: Visit {morning_attraction['name']} - {morning_attraction['description']}. " + \
                        f"(Estimated cost: {morning_attraction['cost']})\n\n"
            
            # Lunch
            lunch = restaurants[day % len(restaurants)]
            itinerary += f"**Lunch**: Enjoy a meal at {lunch['name']} - {lunch['description']}. " + \
                        f"(Estimated cost: {lunch['cost']})\n\n"
            
            # Afternoon activity
            afternoon_attraction = attractions[(day + 1) % len(attractions)]
            itinerary += f"**Afternoon**: Explore {afternoon_attraction['name']} - {afternoon_attraction['description']}. " + \
                        f"(Estimated cost: {afternoon_attraction['cost']})\n\n"
            
            # Dinner
            dinner = restaurants[(day + 1) % len(restaurants)]
            itinerary += f"**Dinner**: Dine at {dinner['name']} - {dinner['description']}. " + \
                        f"(Estimated cost: {dinner['cost']})\n\n"
        
        # Travel tips
        itinerary += "## Travel Tips\n\n"
        itinerary += "- Always carry a map or use a maps app on your phone\n"
        itinerary += "- Check opening hours before visiting attractions\n"
        itinerary += "- Consider purchasing a city pass for discounts on attractions\n"
        itinerary += f"- Learn a few basic phrases in the local language of {destination.title()}\n"
        
        return itinerary

# Update planning phase
def update_planning_phase(messages):
    """
    Update the planning phase based on conversation progress.
    """
    user_profile = st.session_state.user_profile
    planning_phase = st.session_state.planning_phase
    
    # Initial → Refinement transition
    if planning_phase == "initial" and user_profile.get('destination') and user_profile.get('duration'):
        if len(messages) >= 4:  # At least 2 exchanges
            return "refinement"
    
    # Refinement → Suggestion transition
    if planning_phase == "refinement":
        # Count how many preferences are filled
        filled_prefs = sum(1 for v in user_profile.values() if v)
        if filled_prefs >= 6 and len(messages) >= 6:  # More than half fields filled and 3+ exchanges
            return "suggestion"
    
    # Suggestion → Generation transition
    if planning_phase == "suggestion":
        # Look for approval in the last user message
        if len(messages) >= 2:
            last_msg = messages[-1].get('content', '').lower()
            approval_keywords = ['yes', 'good', 'great', 'proceed', 'continue', 'looks good', 'perfect']
            if any(keyword in last_msg for keyword in approval_keywords):
                return "generation"
    
    return planning_phase

# UI Components
def display_chat_message(role, content, avatar="🧑‍💻"):
    """Display a chat message with proper styling"""
    if role == "assistant":
        avatar = "🤖"
    
    with st.container():
        st.markdown(f"""
        <div class="chat-message {role}">
            <div class="message-content">
                <div class="avatar">{avatar}</div>
                <div>{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def display_itinerary(itinerary):
    """Display the generated itinerary with proper formatting"""
    st.markdown(itinerary, unsafe_allow_html=True)

def export_itinerary():
    """Export itinerary as text file"""
    if st.session_state.itinerary:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = st.session_state.user_profile.get('destination', 'trip')
        filename = f"{destination}_itinerary_{now}.txt"
        
        st.download_button(
            label="Export Itinerary as Text",
            data=st.session_state.itinerary,
            file_name=filename,
            mime="text/plain",
            key="download_button",
            help="Download your itinerary as a text file"
        )

def new_itinerary():
    """Reset the app for a new itinerary"""
    st.session_state.messages = []
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
    st.session_state.planning_phase = "initial"
    st.session_state.approved_suggestions = []
    st.session_state.itinerary = None

# Main application
def main():
    st.title("✈️ AI Travel Planner")
    
    # Sidebar
    with st.sidebar:
        st.header("Trip Details")
        if st.session_state.user_profile.get('destination'):
            st.write(f"**Destination:** {st.session_state.user_profile['destination'].title()}")
        if st.session_state.user_profile.get('duration'):
            st.write(f"**Duration:** {st.session_state.user_profile['duration']} days")
        if st.session_state.user_profile.get('budget'):
            st.write(f"**Budget:** {st.session_state.user_profile['budget']}")
        if st.session_state.user_profile.get('interests'):
            st.write(f"**Interests:** {', '.join(st.session_state.user_profile['interests'])}")
        
        st.divider()
        
        if st.session_state.itinerary:
            st.button("Create New Itinerary", on_click=new_itinerary, key="new_button", type="primary")
            export_itinerary()
    
    # Display chat history
    for message in st.session_state.messages:
        display_chat_message(message["role"], message["content"])
    
    # User input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})
        display_chat_message("user", user_input)
        
        # Update planning phase
        current_phase = st.session_state.planning_phase
        new_phase = update_planning_phase(st.session_state.messages)
        
        if new_phase != current_phase:
            st.session_state.planning_phase = new_phase
            
        # Generate AI response
        response = generate_ai_response(
            user_input, 
            st.session_state.user_profile, 
            st.session_state.planning_phase
        )
        
        # Save response
        st.session_state.messages.append({"role": "assistant", "content": response})
        display_chat_message("assistant", response)
        
        # If in generation phase, save itinerary
        if st.session_state.planning_phase == "generation" and len(st.session_state.messages) >= 2:
            st.session_state.itinerary = response
            st.rerun()  # Refresh to show export button

if __name__ == "__main__":
    main()
