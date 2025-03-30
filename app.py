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
                {"name": "Trattoria Zà Zà", "description": "Popular trattoria in Florence", "type": "mid-range
