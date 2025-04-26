import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
from dateutil import parser

# Amadeus API credentials
AMADEUS_API_KEY = "5YWlF018OsxWXu9kMAHRIfBEATNd4irF"
AMADEUS_API_SECRET = "YS1jZZ088P6h5xLk"

# Streamlit app configuration
st.set_page_config(
    page_title="Flight Search App",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .header {
        background: linear-gradient(135deg, #4a8cff 0%, #2a56d6 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .flight-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .flight-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .price-tag {
        background-color: #4a8cff;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
    }
    .airline-logo {
        height: 40px;
        margin-right: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Airport codes (IATA)
AIRPORT_CODES = {
    "DEL": "Delhi", "BOM": "Mumbai", "MCT": "Muscat",
    "DOH": "Doha", "LHR": "London", "DXB": "Dubai",
    "JFK": "New York", "SIN": "Singapore", "BKK": "Bangkok"
}

# Airline logos
AIRLINE_LOGOS = {
    "AI": "https://www.airindia.com/content/dam/air-india/airindia-revamp/logos/AI_Logo_Red_New.svg",
    "EK": "https://logos-world.net/wp-content/uploads/2021/08/Emirates-Logo.png",
    "QR": "https://logos-world.net/wp-content/uploads/2020/11/Qatar-Airways-Logo.png",
    "6E": "https://www.goindigo.in/content/dam/s6web/in/en/assets/logo/IndiGo_logo_2x.png",
    "default": "https://cdn-icons-png.flaticon.com/512/1169/1169168.png"
}

# Function to get Amadeus access token
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_API_KEY,
        'client_secret': AMADEUS_API_SECRET
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            st.error("Failed to get Amadeus token")
            return None
    except Exception as e:
        st.error(f"Token error: {str(e)}")
        return None

# Function to search flights
def search_flights(origin, destination, departure_date, return_date=None, travelers=1, flight_class="ECONOMY"):
    token = get_amadeus_token()
    if not token:
        return None
    
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": travelers,
        "max": 10,
        "currencyCode": "OMR",
        "travelClass": flight_class.upper()
    }
    
    if return_date:
        params["returnDate"] = return_date
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Flight search failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return None

# Function to process flight data
def process_flight_data(flight_data):
    processed_flights = []
    
    if not flight_data or 'data' not in flight_data:
        return None
    
    for offer in flight_data['data']:
        # Basic flight info
        airline_code = offer['itineraries'][0]['segments'][0]['carrierCode']
        airline_logo = AIRLINE_LOGOS.get(airline_code, AIRLINE_LOGOS['default'])
        
        # Flight segments
        segments = offer['itineraries'][0]['segments']
        first_segment = segments[0]
        last_segment = segments[-1]
        
        # Calculate duration
        departure_time = parser.parse(first_segment['departure']['at'])
        arrival_time = parser.parse(last_segment['arrival']['at'])
        duration = arrival_time - departure_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes = remainder // 60
        duration_str = f"{hours}h {minutes}m"
        
        # Fare details
        price = float(offer['price']['grandTotal'])
        
        # Baggage info
        baggage_allowance = "7 kg cabin"
        if 'travelerPricings' in offer and len(offer['travelerPricings']) > 0:
            if 'fareDetailsBySegment' in offer['travelerPricings'][0] and len(offer['travelerPricings'][0]['fareDetailsBySegment']) > 0:
                baggage = offer['travelerPricings'][0]['fareDetailsBySegment'][0].get('includedCheckedBags', {})
                if 'weight' in baggage and 'weightUnit' in baggage:
                    baggage_allowance = f"7 kg cabin, {baggage['weight']} {baggage['weightUnit']} checked"
        
        # Flexibility info
        flexibility = "Standard"
        if 'nonHomogeneous' in offer and offer['nonHomogeneous']:
            flexibility = "Flexible"
        
        # Cancellation policy
        cancellation = "Refundable with fees"
        if 'nonRefundable' in offer and offer['nonRefundable']:
            cancellation = "Non-refundable"
        
        processed_flight = {
            "Airline": airline_code,
            "Airline Logo": airline_logo,
            "Source": first_segment['departure']['iataCode'],
            "Departure": departure_time.strftime("%a, %d-%b-%y %H:%M:%S"),
            "Destination": last_segment['arrival']['iataCode'],
            "Duration": duration_str,
            "Arrival": arrival_time.strftime("%a, %d-%b-%y %H:%M:%S"),
            "Baggage": baggage_allowance,
            "Flexibility": flexibility,
            "Class": offer['class'][0].upper() + offer['class'][1:].lower(),
            "Price (OMR)": price,
            "Cancellation Policy": cancellation,
            "raw_data": offer
        }
        processed_flights.append(processed_flight)
    
    return processed_flights

# Main app
st.title("✈️ Flight Search App")
st.markdown("<div class='header'>Find the best flights for your trip</div>", unsafe_allow_html=True)

# Search form
with st.form("flight_search_form"):
    col1, col2 = st.columns(2)
    with col1:
        origin = st.selectbox("From", options=list(AIRPORT_CODES.keys()), format_func=lambda x: f"{x} - {AIRPORT_CODES[x]}")
        departure_date = st.date_input("Departure Date", min_value=datetime.today())
        flight_class = st.selectbox("Class", ["Economy", "Premium Economy", "Business", "First"])
    with col2:
        destination = st.selectbox("To", options=list(AIRPORT_CODES.keys()), format_func=lambda x: f"{x} - {AIRPORT_CODES[x]}")
        return_date = st.date_input("Return Date (optional)", min_value=datetime.today() + timedelta(days=1))
        travelers = st.number_input("Travelers", min_value=1, max_value=10, value=1)
    
    submitted = st.form_submit_button("Search Flights")

# Display results
if submitted:
    if origin == destination:
        st.error("Origin and destination cannot be the same")
    else:
        with st.spinner("Searching for flights..."):
            flight_data = search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date.strftime("%Y-%m-%d"),
                return_date=return_date.strftime("%Y-%m-%d") if return_date else None,
                travelers=travelers,
                flight_class=flight_class
            )
            
            if flight_data:
                processed_flights = process_flight_data(flight_data)
                
                if processed_flights:
                    st.success(f"Found {len(processed_flights)} flight options")
                    
                    # Sort by price
                    processed_flights.sort(key=lambda x: x['Price (OMR)'])
                    
                    for flight in processed_flights:
                        with st.container():
                            st.markdown("<div class='flight-card'>", unsafe_allow_html=True)
                            
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.image(flight['Airline Logo'], width=80)
                                st.markdown(f"<span class='price-tag'>{flight['Price (OMR)']:.2f} OMR</span>", unsafe_allow_html=True)
                                st.write(f"Class: {flight['Class']}")
                            
                            with col2:
                                st.write(f"**{flight['Source']} → {flight['Destination']}**")
                                st.write(f"**Departure:** {flight['Departure']}")
                                st.write(f"**Arrival:** {flight['Arrival']}")
                                st.write(f"**Duration:** {flight['Duration']}")
                                
                                # Flight details expander
                                with st.expander("View Fare Details"):
                                    details_col1, details_col2 = st.columns(2)
                                    with details_col1:
                                        st.write("**Baggage Allowance:**")
                                        st.write(flight['Baggage'])
                                        st.write("**Flexibility:**")
                                        st.write(flight['Flexibility'])
                                    with details_col2:
                                        st.write("**Cancellation Policy:**")
                                        st.write(flight['Cancellation Policy'])
                                        st.write("**Airline:**")
                                        st.write(flight['Airline'])
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.warning("No flights found for your search criteria")
            else:
                st.error("Failed to retrieve flight data. Please try again later.")

# Add some information about the app
st.markdown("---")
st.markdown("""
### About This App
- Searches flights using Amadeus Flight Offers API
- Displays comprehensive fare details including baggage allowance and cancellation policies
- Prices shown in Omani Rial (OMR)
- Shows direct and connecting flight options
""")
