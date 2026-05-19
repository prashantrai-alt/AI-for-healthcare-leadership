import streamlit as st
import google.generativeai as genai
import json
import re
import time
import hashlib
from supabase import create_client, Client

# Configure the look of your app
st.set_page_config(page_title="Continuous Learning AI", layout="wide")
st.title("Healthcare Leadership AI Co-Pilot")
st.write("An integrated platform for continuous competency development.")

# --- MEMORY SETUP ---
if "sim_history" not in st.session_state:
    st.session_state.sim_history = []
if "sim_active" not in st.session_state:
    st.session_state.sim_active = False

if "diagnostic_profile" not in st.session_state:
    st.session_state.diagnostic_profile = {
        "topic": "Pending...", 
        "emotion": "Pending...", 
        "core_skill_needed": "Pending..."
    }

if "microlearning_content" not in st.session_state:
    st.session_state.microlearning_content = ""

# --- LOGIN MEMORY SETUP ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- SECURE API CONNECTIVITY (Gemini & Supabase) ---
try:
    # Gemini Setup
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Supabase Setup
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except KeyError:
    st.error("⚠️ Configuration Keys not found! Please check your Streamlit Secrets setting.")
    st.stop()

# --- SECURITY HANDLERS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_userdata(username, password):
    supabase.table("profiles").insert({"username": username, "password": password}).execute()

def login_user(username, password):
    response = supabase.table("profiles").select("*").eq("username", username).eq("password", password).execute()
    return response.data

# --- DATABASE CHAT HISTORY HANDLERS ---
def load_chat_history(username):
    try:
        response = supabase.table("chat_messages").select("*").eq("username", username).order("id", desc=False).execute()
        return response.data
    except Exception:
        return []

def save_chat_message(username, role, content):
    try:
        supabase.table("chat_messages").insert({"username": username, "role": role, "content": content}).execute()
    except Exception:
        pass


# ==========================================
# --- SUPABASE LOGIN/SIGNUP GATEWAY ---
# ==========================================
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            user_log = st.text_input("Username")
            pass_log = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                hashed_pswd = make_hashes(pass_log)
                result = login_user(user_log, hashed_pswd)
                
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = user_log
                    st.success(f"Welcome back, {user_log}!")
                    st.rerun()
                else:
                    st.error("⚠️ Invalid username or password.")

    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_user = st.text_input("Choose a Username")
            new_pass = st.text_input("Choose a Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Sign Up"):
                if new_pass != confirm_pass:
                    st.error("⚠️ Passwords do not match!")
                elif len(new_pass) < 4:
                    st.error("⚠️ Password must be at least 4 characters.")
                elif not new_user.strip():
                    st.error("⚠️ Username cannot be blank.")
                else:
                    # Check if user already exists
                    existing = supabase.table("profiles").select("username").eq("username", new_user).execute()
                    if existing.data:
                        st.warning("⚠️ Username already exists.")
                    else:
                        add_userdata(new_user, make_hashes(new_pass))
                        st.success("🎉 Account created successfully! You can now log in.")

# ==========================================
# --- THE MAIN APP (Only runs if logged in) ---
# ==========================================
else:
    # --- SIDEBAR UI ---
    st.sidebar.success(f"👤 Welcome back, {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.diagnostic_profile = {"topic": "Pending...", "emotion": "Pending...", "core_skill_needed": "Pending..."}
        st.session_state.microlearning_content = ""
        st.rerun()
        
    st.sidebar.divider()
    
    st.sidebar.title("App Navigation")
    menu = ["Chatbot Support", "Scenario Simulations", "Adaptive Microlearning", "Burnout Support"]
    choice = st.sidebar.radio("Go to:", menu)

    st.sidebar.divider()

    st.sidebar.subheader("🧠 Live Diagnostic Profile")
    st.sidebar.info(
        f"**Topic:** {st.session_state.diagnostic_profile.get('topic', 'N/A')}\n\n"
        f"**Emotion:** {st.session_state.diagnostic_profile.get('emotion', 'N/A')}\n\n"
        f"**Target Skill:** {st.session_state.diagnostic_profile.get('core_skill_needed', 'N/A')}"
    )

    # --- 1. THE DIAGNOSTIC CHATBOT ---
    if choice == "Chatbot Support":
        st.header("Diagnostic Chatbot")
        st.write("Discuss a leadership challenge. The AI will coach you while silently building your learning profile.")
        
        # Pull past logs dynamically from the secure Supabase table
        db_messages = load_chat_history(st.session_state.username)
        
        for message in db_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_input := st.chat_input("What challenge are you facing today?"):
            
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Commit the user message to the database immediately
            save_chat_message(st.session_state.username, "user", user_input)
            
            # Context window array for the AI runtime engine
            current_history = db_messages + [{"role": "user", "content": user_input}]

            with st.chat_message("assistant"):
                with st.spinner("Analyzing your profile and generating advice..."):
                    
                    # PHASE A: THE SILENT DIAGNOSTIC
                    diagnostic_prompt = f"""
                    Analyze this healthcare leader's statement: '{user_input}'.
                    Identify the core issue, their emotional state, and the primary leadership skill they need to develop.
                    Return ONLY a valid JSON object with exactly these three keys: "topic", "emotion", "core_skill_needed".
                    Do not include any other text.
                    """
                    try:
                        raw_diagnosis = model.generate_content(diagnostic_prompt).text
                        clean_json = re.sub(r'```json\n|```', '', raw_diagnosis).strip()
                        profile_data = json.loads(clean_json)
                        st.session_state.diagnostic_profile = profile_data
                        
                        time.sleep(2) 
                    except Exception as e:
                        pass 

                    # PHASE B: THE ACTUAL CHATBOT REPLY
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in current_history])
                    chat_prompt = f"""You are an expert healthcare leadership mentor. 
                    Conversation history: {history_text}
                    INSTRUCTIONS:
                    Provide a CLEAR, DIRECT, ACTIONABLE solution to their problem.
                    Then, ask ONE follow-up question to help them apply it."""
                    
                    response = model.generate_content(chat_prompt)
                    st.markdown(response.text)
            
            # Archive the AI response to the database table
            save_chat_message(st.session_state.username, "assistant", response.text)
            st.rerun()
                
        if st.button("Clear Chat History"):
            supabase.table("chat_messages").delete().eq("username", st.session_state.username).execute()
            st.rerun()

    # --- 2. SCENARIO SIMULATIONS ---
    elif choice == "Scenario Simulations":
        st.header("Dynamic Scenario Simulation")
        profile = st.session_state.diagnostic_profile
        
        if profile["topic"] == "Pending...":
            st.warning("⚠️ Please chat with the Diagnostic Chatbot first! The AI needs to build your profile before it can generate a custom simulation.")
        else:
            st.success(f"**Scenario customized for you based on:** {profile['topic']} | **Testing your:** {profile['core_skill_needed']}")
            
            if not st.session_state.sim_active:
                if st.button("Generate My Custom Scenario"):
                    st.session_state.sim_active = True
                    with st.spinner("Building a realistic hospital environment..."):
                        setup_prompt = f"""
                        You are a healthcare simulation engine. Generate a brief, realistic hospital scenario tailored to this profile:
                        - Topic: {profile['topic']}
                        - User's Emotion to manage: {profile['emotion']}
                        - Leadership Skill to test: {profile['core_skill_needed']}
                        
                        Set the scene in 3 sentences. End by explicitly asking the user: "What is your immediate first action?" 
                        """
                        response = model.generate_content(setup_prompt)
                        st.session_state.sim_history.append({"role": "assistant", "content": response.text})
                        st.rerun()
            
            else:
                for message in st.session_state.sim_history:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                
                if user_action := st.chat_input("Enter your leadership decision..."):
                    with st.chat_message("user"):
                        st.markdown(user_action)
                    st.session_state.sim_history.append({"role": "user", "content": user_action})
                    
                    with st.chat_message("assistant"):
                        with st.spinner("Evaluating your decision..."):
                            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.sim_history])
                            eval_prompt = f"""
                            You are a healthcare leadership evaluator. 
                            Target Skill being evaluated: {profile['core_skill_needed']}.
                            Conversation history: {history_text}
                            
                            Evaluate the user's latest action. Provide brief feedback on what they did right or wrong specifically regarding the target skill. 
                            Then, escalate the scenario and ask for their next move.
                            """
                            response = model.generate_content(eval_prompt)
                            st.markdown(response.text)
                    st.session_state.sim_history.append({"role": "assistant", "content": response.text})
                
                if st.button("End Simulation & Reset"):
                    st.session_state.sim_active = False
                    st.session_state.sim_history = []
                    st.rerun()

    # --- 3. ADAPTIVE MICROLEARNING ---
    elif choice == "Adaptive Microlearning":
        st.header("Adaptive Microlearning Module")
        profile = st.session_state.diagnostic_profile
        
        if profile["topic"] == "Pending...":
            st.warning("⚠️ Please chat with the Diagnostic Chatbot first to identify your learning needs!")
        else:
            st.write("Based on your recent profile, we have curated a custom learning module for you.")
            st.info(f"**Focus Area:** {profile['core_skill_needed']} in the context of {profile['topic']}")
            
            if st.button("Generate My Personalized Lesson"):
                with st.spinner("Curating evidence-based management practices..."):
                    lesson_prompt = f"""
                    You are a healthcare education expert. The user needs to improve their '{profile['core_skill_needed']}' 
                    regarding the topic of '{profile['topic']}'. 
                    
                    Create a highly engaging, 3-minute microlearning module. 
                    It must include:
                    1. A brief theoretical framework or clinical model (e.g., DESC, SBAR, LEAN) applicable to this exact skill.
                    2. 3 actionable bullet points on how a hospital leader can apply it immediately.
                    3. A quick, thought-provoking reflection question at the end.
                    
                    Use bolding and beautiful Markdown formatting. Keep it concise.
                    """
                    response = model.generate_content(lesson_prompt)
                    st.session_state.microlearning_content = response.text
            
            if st.session_state.microlearning_content != "":
                st.divider()
                st.markdown(st.session_state.microlearning_content)
                st.divider()
                
                if st.button("Mark Module Complete"):
                    st.balloons()
                    st.success("🎉 Incredible! You have completed a full Continuous Learning Loop.")

    # --- 4. BURNOUT SUPPORT ---
    elif choice == "Burnout Support":
        st.header("Wellbeing & Workload Management")
        st.write("Log your shift stress or take a quick mindfulness break to reduce burnout.")
        stress_level = st.slider("How stressful was your shift today? (1 = Very Calm, 10 = Overwhelming)", 1, 10, 5)
        if st.button("Log Stress Level"):
            if stress_level > 7:
                st.warning("It sounds like a tough day. Please take 5 minutes to unplug, and consider reaching out to a peer for support.")
            else:
                st.success("Your stress level has been logged. Keep up the great work!")
