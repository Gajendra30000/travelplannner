import os
import streamlit as st
import requests
import datetime
import json

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def markdown_to_html(md_text: str) -> str:
    import re
    html = ""
    in_list = False
    
    # Split into lines
    lines = md_text.split("\n")
    for line in lines:
        stripped = line.strip()
        
        # Handle empty lines
        if not stripped:
            if in_list:
                html += "</ul>\n"
                in_list = False
            html += "<br>\n"
            continue
            
        # Handle lists
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html += "<ul>\n"
                in_list = True
            content = stripped[2:]
            content = parse_bold(content)
            html += f"<li>{content}</li>\n"
            continue
        else:
            if in_list:
                html += "</ul>\n"
                in_list = False
                
        # Handle headers
        if stripped.startswith("#### "):
            content = parse_bold(stripped[5:])
            html += f"<h4>{content}</h4>\n"
        elif stripped.startswith("### "):
            content = parse_bold(stripped[4:])
            html += f"<h3>{content}</h3>\n"
        elif stripped.startswith("## "):
            content = parse_bold(stripped[3:])
            html += f"<h2>{content}</h2>\n"
        elif stripped.startswith("# "):
            content = parse_bold(stripped[2:])
            html += f"<h1>{content}</h1>\n"
        else:
            content = parse_bold(stripped)
            html += f"<p>{content}</p>\n"
            
    if in_list:
        html += "</ul>\n"
        
    return html

def parse_bold(text: str) -> str:
    import re
    # Bold **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    return text


st.set_page_config(
    page_title="🌍 AI Travel Planner",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 20px 20px;
    }
    
    .travel-card {
        background: white;
        color: #111111;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        border-left: 5px solid #667eea;
    }
    
    .date-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border: 1px solid #e9ecef;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .travel-response {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-top: 2rem;
    }
    
    .response-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .feature-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    
    .sidebar-content {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .success-box {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    
    .info-box {
        background: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
    
    .error-box {
        background: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🌍 AI Travel Planner</h1>
    <p>Your intelligent companion for perfect travel planning</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_travel_details" not in st.session_state:
    st.session_state.last_travel_details = None

# Sidebar for additional features
with st.sidebar:
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    st.markdown("### 🎯 Features")
    st.markdown("✈️ **Smart Itinerary Planning**")
    st.markdown("🏨 **Hotel Recommendations**")
    st.markdown("🍽️ **Restaurant Suggestions**")
    st.markdown("📍 **Local Attractions**")
    st.markdown("💰 **Budget Planning**")
    st.markdown("🌤️ **Weather Insights**")
    st.markdown('</div>', unsafe_allow_html=True)
    

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="travel-card">', unsafe_allow_html=True)
    st.markdown("### 🗓️ Travel Dates")
    
    # Date picker section
    st.markdown('<div class="date-container">', unsafe_allow_html=True)
    
    date_col1, date_col2 = st.columns(2)
    
    with date_col1:
        start_date = st.date_input(
            "📅 Departure Date",
            datetime.date.today(),
            min_value=datetime.date.today(),
            max_value=datetime.date.today() + datetime.timedelta(days=365),
            key="start_date"
        )
    
    with date_col2:
        end_date = st.date_input(
            "📅 Return Date",
            datetime.date.today() + datetime.timedelta(days=7),
            min_value=start_date,
            max_value=datetime.date.today() + datetime.timedelta(days=365),
            key="end_date"
        )
    
  
    trip_duration = 0
    date_validation_message = ""
    
    if start_date and end_date:
        trip_duration = (end_date - start_date).days
        if trip_duration > 0:
            date_validation_message = f"✅ Trip Duration: {trip_duration} days"
            st.markdown(f'<div class="success-box">{date_validation_message}</div>', unsafe_allow_html=True)
        elif trip_duration == 0:
            date_validation_message = "ℹ️ Day trip selected"
            st.markdown(f'<div class="info-box">{date_validation_message}</div>', unsafe_allow_html=True)
        else:
            date_validation_message = "❌ Return date must be after departure date"
            st.markdown(f'<div class="error-box">{date_validation_message}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
  
    st.markdown("### 💬 Tell us about your dream trip")
    
    with st.form(key="travel_form", clear_on_submit=False):
        user_input = st.text_area(
            "Describe your travel plans:",
            placeholder="e.g., Plan a romantic trip to Paris for 2 people. We love art, fine dining, and historic sites. We're interested in museums, local markets, and cozy cafes.",
            height=100,
            key="user_input"
        )
        
        # Additional options
        col_budget, col_travelers = st.columns(2)
        
        with col_budget:
            budget_range = st.selectbox(
                "💰 Budget Range",
                ["Not specified", "Budget ($)", "Mid-range ($$)", "Luxury ($$$)", "Ultra-luxury ($$$$)"],
                key="budget_range"
            )
        
        with col_travelers:
            travel_style = st.selectbox(
                "🎭 Travel Style",
                ["Not specified", "Adventure", "Relaxation", "Cultural", "Romantic", "Family-friendly", "Business"],
                key="travel_style"
            )
        
        submit_button = st.form_submit_button("✨ Generate My Travel Plan")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="feature-box">', unsafe_allow_html=True)
    st.markdown("### 🎯 Quick Tips")
    st.markdown("**For better results:**")
    st.markdown("• Mention specific cities or regions")
    st.markdown("• Include your interests and hobbies")
    st.markdown("• Specify accommodation preferences")
    st.markdown("• Note any dietary restrictions")
    st.markdown("• Include group size and ages")
    st.markdown("• Mention special occasions")
    st.markdown('</div>', unsafe_allow_html=True)


if submit_button and user_input.strip():
  
    if trip_duration < 0:
        st.error("❌ Please select valid dates with return date after departure date.")
    else:
        try:
           
            payload = {
                "question": user_input,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "budget_range": budget_range if budget_range != "Not specified" else None,
                "travel_style": travel_style if travel_style != "Not specified" else None,
                "trip_duration": trip_duration if trip_duration > 0 else None
            }
            
        
            with st.expander("🔍 Debug: Request Details", expanded=False):
                st.json(payload)
            
         
            with st.spinner("🤖 AI is crafting your perfect travel plan..."):
                response = requests.post(
                    f"{BASE_URL}/query", 
                    json=payload,
                    timeout=120 
                )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", "No answer returned.")
                saved_file = result.get("saved_file", "")
                travel_details = result.get("travel_details", {})
                
                # Store travel details in session state
                st.session_state.last_travel_details = travel_details
                
                # Display response in styled container
                st.markdown(f"""<div class="travel-response">
<div class="response-header">
<h2>🎉 Your Personalized Travel Plan</h2>
<p><strong>Generated:</strong> {datetime.datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
<p><strong>Trip Duration:</strong> {trip_duration} days</p>
<p><strong>Budget Range:</strong> {budget_range}</p>
<p><strong>Travel Style:</strong> {travel_style}</p>
</div>
</div>""", unsafe_allow_html=True)
                
                # Display the actual travel plan
                answer_html = markdown_to_html(answer)
                st.markdown(f"""<div class="travel-card">
{answer_html}
<hr style="margin: 2rem 0;">
<p style="text-align: center; font-style: italic; color: #666;">
<strong>⚠️ Important:</strong> This travel plan was generated by AI. 
Please verify all information, especially prices, operating hours, and travel requirements before your trip.
</p>
</div>""", unsafe_allow_html=True)
                
                # Add download options
                col_download1, col_download2 = st.columns(2)
                
                with col_download1:
                    # Download as text
                    travel_plan_text = f"""
TRAVEL PLAN
===========

Trip Details:
- Dates: {start_date} to {end_date}
- Duration: {trip_duration} days
- Budget: {budget_range}
- Style: {travel_style}

Original Request:
{user_input}

Generated Plan:
{answer}

Generated on: {datetime.datetime.now().strftime('%B %d, %Y at %H:%M')}
                    """
                    
                    st.download_button(
                        label="📥 Download as Text",
                        data=travel_plan_text,
                        file_name=f"travel_plan_{start_date}_{end_date}.txt",
                        mime="text/plain"
                    )
                
                with col_download2:
                    if saved_file:
                        st.success(f"✅ Plan saved as: {saved_file}")
                    
                    # Download as JSON
                    travel_plan_json = {
                        "travel_details": travel_details,
                        "user_request": user_input,
                        "generated_plan": answer,
                        "generated_at": datetime.datetime.now().isoformat()
                    }
                    
                    st.download_button(
                        label="📥 Download as JSON",
                        data=json.dumps(travel_plan_json, indent=2),
                        file_name=f"travel_plan_{start_date}_{end_date}.json",
                        mime="application/json"
                    )
                
            else:
                st.error(f"❌ Failed to generate travel plan. Status code: {response.status_code}")
                st.error(f"Error details: {response.text}")
                
        except requests.exceptions.Timeout:
            st.error("❌ Request timed out. The AI is taking longer than expected. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to the backend. Please ensure the FastAPI server is running.")
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")

# Display last travel details if available
if st.session_state.last_travel_details:
    with st.expander("📊 Last Trip Details", expanded=False):
        st.json(st.session_state.last_travel_details)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🌍 <strong>AI Travel Planner</strong> | Making your travel dreams come true</p>
    <p>✈️ Safe travels and happy planning! ✈️</p>
</div>
""", unsafe_allow_html=True)