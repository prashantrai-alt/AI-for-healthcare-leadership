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
    # CHANGED: Fixed syntax from 'ascending=True' to 'desc=False'
    response = supabase.table("chat_messages").select("*").eq("username", username).order("id", desc=False).execute()
    return response.data

def save_chat_message(username, role, content):
    supabase.table("chat_messages").insert({"username": username, "role": role, "content": content}).execute()


# --- 5. STREAMLIT SESSION STATE SETUP ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- 6. APPLICATION USER INTERFACE ---
st.title("Healthcare Leadership AI Co-Pilot")

if not st.session_state.logged_in:
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

else:
    username = st.session_state.username
    
    with st.sidebar:
        st.write(f"Logged in as: **{username}**")
        if st.button("Log Out"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
            
    st.write(f"### Welcome back, {username}!")
    st.info("Your conversation history is securely saved to the cloud database permanently.")
    
    # Load past messages from Supabase cloud database
    db_messages = load_chat_history(username)
    
    # Display the full conversation history chronologically
    for msg in db_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # Handle new user chat input
    if user_input := st.chat_input("Ask your mentor bot anything..."):
        with st.chat_message("user"):
            st.write(user_input)
            
        save_chat_message(username, "user", user_input)
        
        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in db_messages]) + f"\nuser: {user_input}"
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                chat_prompt = f"""You are an expert healthcare leadership mentor.
                Conversation history context:
                {history_context}
                
                Provide a CLEAR, DIRECT, ACTIONABLE solution to their problem.
                Then, end your response by asking ONE follow-up question to help them apply it."""
                
                response = model.generate_content(chat_prompt)
                st.write(response.text)
                
        save_chat_message(username, "assistant", response.text)
