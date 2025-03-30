import streamlit as st
import openai
import requests
import json

def get_activity_suggestions(destination, preferences):
    """Fetch travel activity suggestions using a web search API."""
    search_url = f"https://api.duckduckgo.com/?q={destination} {preferences} travel activities&format=json"
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()
        return [item['Text'] for item in data.get('RelatedTopics', [])][:5]
    except requests.exceptions.RequestException:
        return ["Could not fetch activity suggestions. Please try again later."]

def generate_itinerary(user_input):
    """Generate a structured travel itinerary using OpenAI GPT."""
    prompt = f"""
    You are an AI-powered travel assistant. Create a highly personalized, detailed, and structured day-by-day itinerary for a traveler with the following details:
    
    Budget: {user_input['budget']}
    Duration: {user_input['duration']} days
    Destination: {user_input['destination']}
    Preferences: {', '.join(user_input['preferences'])}
    
    The itinerary should include:
    - Suggested activities based on preferences
    - Recommended dining options
    - Travel tips and estimated costs
    - Suitable timings for each activity
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4", messages=[{"role": "system", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generating itinerary: {str(e)}"

def fetch_travel_info(destination):
    """Get live travel-related information from the web (e.g., weather, local events)."""
    weather_api_key = "your_weather_api_key"
    event_api_key = "your_event_api_key"
    
    weather_url = f"https://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={destination}"
    events_url = f"https://api.eventapi.com/events?location={destination}&key={event_api_key}"
    
    try:
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        weather_info = weather_data.get("current", {}).get("condition", {}).get("text", "Weather data unavailable")
    except requests.exceptions.RequestException:
        weather_info = "Weather data unavailable"
    
    try:
        events_response = requests.get(events_url)
        events_response.raise_for_status()
        events_data = events_response.json()
        events = [event['name'] for event in events_data.get("events", [])][:3]
    except requests.exceptions.RequestException:
        events = ["Could not fetch event data."]
    
    return weather_info, events

# Streamlit UI
st.title("AI-Powered Travel Planner")
st.write("Plan your trip with a personalized AI itinerary!")

# User Input Section
with st.form("travel_form"):
    budget = st.selectbox("Budget", ["Low", "Moderate", "High"])
    duration = st.number_input("Trip Duration (days)", min_value=1, max_value=30, value=5)
    destination = st.text_input("Destination")
    preferences = st.multiselect("Select Preferences", ["Nature", "Adventure", "Food", "Cultural Sites", "Relaxation", "Nightlife"])
    submit = st.form_submit_button("Generate Itinerary")

if submit:
    if not destination:
        st.error("Please enter a destination.")
    else:
        user_data = {"budget": budget, "duration": duration, "destination": destination, "preferences": preferences}
        suggestions = get_activity_suggestions(destination, preferences)
        itinerary = generate_itinerary(user_data)
        weather, events = fetch_travel_info(destination)
        
        st.subheader("Live Travel Info")
        st.write(f"Weather: {weather}")
        st.write("Upcoming Events:")
        for event in events:
            st.write(f"- {event}")
        
        st.subheader("Suggested Activities")
        for s in suggestions:
            st.write(f"- {s}")
        
        st.subheader("Your Personalized Itinerary")
        st.write(itinerary)

st.write("Hosted on Streamlit - Enjoy your trip planning!")
