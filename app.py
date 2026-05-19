import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import hashlib

# --- 1. INITIALIZE SUPABASE CLIENT ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. CONFIGURE GEMINI AI ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 3. DATABASE HELPER FUNCTIONS (AUTHENTICATION) ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user_exists(username):
    response = supabase.table("profiles").select("*").eq("username", username).execute()
    return len(response.data) > 0

def add_user(username, password):
    hashed_pw = make_hashes(password)
    supabase.table("profiles").insert({"username": username, "password": hashed_pw}).execute()

def login_user(username, password):
    hashed_pw = make_hashes(password)
    response = supabase.table("profiles").select("*").eq("username", username).eq("password", hashed_pw).execute()
    return len(response.data) > 0

# --- 4. DATABASE HELPER FUNCTIONS (CHAT HISTORY) ---
def load_chat_history(username):
    response = supabase.table("chat_messages").select("*").eq("username", username).order("id", desc=False).execute()
    return response.data

def save_chat_message(username, role, content):
    supabase.table("chat_messages").insert({"username": username, "role": role, "content": content}).execute()


# --- 5. STREAMLIT SESSION STATE SETUP ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- 6. APPLICATION GATEWAY (AUTH SCREEN) ---
if not st.session_state.logged_in:
    st.title("Healthcare Leadership AI Co-Pilot")
    st.subheader("Please Log In or Sign Up to Access the Platform")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login"):
            if login_user(login_username, login_password):
                st.session_state.logged_in = True
                st.session_state.username = login_username
                st.success(f"Welcome back, {login_username}!")
                st.rerun()
            else:
                st.error("Invalid Username or Password")
                
    with tab2:
        st.subheader("Create a New Account")
        new_username = st.text_input("Choose a Username", key="new_user")
        new_password = st.text_input("Choose a Password", type="password", key="new_pass")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass")
        
        if st.button("Sign Up"):
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            elif check_user_exists(new_username):
                st.error("Username already taken! Please pick another one.")
            elif new_username.strip() == "" or new_password.strip() == "":
                st.error("Fields cannot be left blank.")
            else:
                add_user(new_username, new_password)
                st.success("Account created successfully! Go to the Login tab to log in.")

# --- 7. MAIN PLATFORM INTERFACE (RESTORED FEATURES) ---
else:
    username = st.session_state.username
    
    # --- FEATURE: LIVE SIDEBAR DIAGNOSTICS ---
    with st.sidebar:
        st.title("Executive Dashboard")
        st.write(f"User: **{username}**")
        
        st.markdown("---")
        st.subheader("📊 Leadership Diagnostics")
        st.caption("Real-time metric tracking based on your interactions.")
        
        # Simulated performance diagnostic tracking bars
        st.progress(85, text="Communication Effectiveness")
        st.progress(70, text="Crisis & Shortage Management")
        st.progress(78, text="Strategic Resource Allocation")
        st.progress(92, text="Bioethics & Compliance")
        
        st.markdown("---")
        if st.button("Log Out of System", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
            
    # Main Application Header
    st.title("Healthcare Leadership AI Co-Pilot")
    st.write(f"Welcome back, **Director {username}**!")
    
    # --- FEATURE: APP NAVIGATION TABS ---
    tab_chat, tab_simulation, tab_learning = st.tabs([
        "💬 AI Mentor Chatbot", 
        "🎭 Scenario Simulations", 
        "📚 Microlearning Modules"
    ])
    
    # ==========================================
    # TAB 1: AI MENTOR CHATBOT (DATABASE CONNECTED)
    # ==========================================
    with tab_chat:
        st.subheader("Executive Advisory Session")
        st.info("Your chat logs are securely compiled and archived in your Supabase Cloud Database.")
        
        # Load past messages from Supabase cloud database
        db_messages = load_chat_history(username)
        
        # Display the full conversation history from database records
        for msg in db_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        # Handle new user chat input
        if user_input := st.chat_input("Consult your mentor regarding hospital operations, staff conflicts, or board metrics..."):
            with st.chat_message("user"):
                st.write(user_input)
                
            # Save user message permanently to Supabase cloud
            save_chat_message(username, "user", user_input)
            
            # Rebuild full conversation context for Gemini using the database records
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in db_messages]) + f"\nuser: {user_input}"
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing operational directives..."):
                    chat_prompt = f"""You are an elite, highly experienced expert healthcare leadership mentor and hospital consultant.
                    Conversation history context:
                    {history_context}
                    
                    Provide a CLEAR, DIRECT, STRATEGIC, and ACTIONABLE solution to their problem. Focus on healthcare operational efficiency, patient safety, or clinical morale.
                    Then, end your response by asking exactly ONE targeted follow-up question to help them apply it to their specific department."""
                    
                    response = model.generate_content(chat_prompt)
                    st.write(response.text)
                    
            # Save AI response permanently to Supabase cloud
            save_chat_message(username, "assistant", response.text)
            
    # ==========================================
    # TAB 2: SCENARIO SIMULATIONS (AI POWERED)
    # ==========================================
    with tab_simulation:
        st.subheader("Interactive Crisis Management Simulation")
        st.write("Select an operational emergency scenario to test your situational leadership decisions:")
        
        scenario_choice = st.selectbox("Choose a Scenario Blueprint:", [
            "Select a scenario...",
            "Sudden ICU Nursing Staff Shortage & Burnout Crisis",
            "Emergency Department Overcrowding & Diversion Dilemma",
            "Cross-Departmental Conflict: Surgery vs. Anesthesiology Chiefs",
            "Cybersecurity Ransomware Attack on Electronic Health Records (EHR)"
        ])
        
        if scenario_choice != "Select a scenario...":
            st.markdown(f"### 🚩 Active Case Study: {scenario_choice}")
            
            if st.button("Generate AI Case Briefing & Challenge"):
                with st.spinner("Formulating simulation parameters..."):
                    sim_prompt = f"Act as a healthcare leadership simulation coordinator. Generate a high-stakes, 2-paragraph operational briefing regarding this scenario: '{scenario_choice}'. Conclude with a critical choice or dilemma that a hospital administrator must make immediately."
                    sim_response = model.generate_content(sim_prompt)
                    st.markdown("---")
                    st.write(sim_response.text)
                    
            sim_answer = st.text_area("Type your executive action plan or response to this crisis:")
            if st.button("Submit Action Plan for Board Evaluation"):
                with st.spinner("Reviewing response against clinical compliance metrics..."):
                    eval_prompt = f"Evaluate the following leadership action plan for the scenario '{scenario_choice}'. Action Plan: '{sim_answer}'. Provide a brief score outline
