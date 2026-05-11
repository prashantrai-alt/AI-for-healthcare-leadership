import streamlit as st
import google.generativeai as genai

# Configure the look of your app
st.set_page_config(page_title="AI Healthcare Leader", layout="wide")
st.title("Healthcare Leadership AI Co-Pilot")
st.write("An integrated platform for learning, simulations, and workload support.")

# --- MEMORY SETUP ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "sim_history" not in st.session_state:
    st.session_state.sim_history = []
if "sim_active" not in st.session_state:
    st.session_state.sim_active = False

# --- SECURE API KEY SETUP ---
# The app now silently looks into your hidden secrets.toml file!
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except KeyError:
    st.error("⚠️ API Key not found! Please check your .streamlit/secrets.toml file.")
    st.stop() # Stops the app from running further if the key is missing

# Create a menu on the left sidebar
st.sidebar.title("App Navigation")
menu = ["Chatbot Support", "Scenario Simulations", "Adaptive Microlearning", "Burnout Support"]
choice = st.sidebar.radio("Go to:", menu)

# --- 1. CHATBOT SUPPORT ---
if choice == "Chatbot Support":
    st.header("Leadership Coaching Chatbot")
    st.write("Get direct solutions and reflective support for your daily challenges.")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("What challenge are you facing?"):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history])
                
                prompt = f"""You are an expert healthcare leadership mentor. 
                Conversation history:
                {history_text}
                
                User's latest input: '{user_input}'. 
                INSTRUCTIONS:
                1. Provide a CLEAR, DIRECT, ACTIONABLE solution to their problem. Don't just ask them to reflect; tell them exactly what best practices suggest they should do.
                2. Only after providing the direct answer, ask ONE follow-up question to help them apply it to their specific ward."""
                
                response = model.generate_content(prompt)
                st.markdown(response.text)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

# --- 2. SCENARIO SIMULATIONS ---
elif choice == "Scenario Simulations":
    st.header("Crisis Management Simulation")
    st.write("**Scenario:** You are managing a ward that is suddenly understaffed during a busy shift. Patient wait times are tripling.")
    
    if not st.session_state.sim_active:
        decision = st.radio(
            "Choose your initial action:", 
            ["Reallocate staff from another ward", 
             "Call in off-duty nurses on overtime", 
             "Take on patient load yourself to help the team"]
        )
        if st.button("Submit Decision"):
            st.session_state.sim_active = True
            with st.spinner("Analyzing your decision..."):
                prompt = f"""You are a healthcare leadership mentor running a simulation. 
                Scenario: Understaffed ward, wait times tripling.
                User's choice: '{decision}'. 
                Provide clear feedback on why this is right or wrong. Then, escalate the crisis based on this choice, and ask what they will do next."""
                
                response = model.generate_content(prompt)
                st.session_state.sim_history.append({"role": "assistant", "content": response.text})
                st.rerun()
    
    else:
        for message in st.session_state.sim_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if follow_up_action := st.chat_input("What is your next move?"):
            with st.chat_message("user"):
                st.markdown(follow_up_action)
            st.session_state.sim_history.append({"role": "user", "content": follow_up_action})
            
            with st.chat_message("assistant"):
                with st.spinner("Evaluating your response..."):
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.sim_history])
                    
                    prompt = f"""You are a supportive healthcare leadership mentor running a dynamic simulation.
                    Conversation so far: {history_text}
                    User's latest input: '{follow_up_action}'.
                    
                    CRITICAL INSTRUCTIONS:
                    1. If the user asks for help, asks a question (like "What should I do?"), or seems stuck, DO NOT scold them. Step in as a mentor. Tell them the clear, direct answer on what the BEST practice is for this crisis, and give them 2-3 specific options they can choose from to move forward.
                    2. If they suggest a long-term action (like hiring staff) for a short-term emergency, gently explain why that won't work right this second, and tell them what they SHOULD focus on.
                    3. If they give a specific action, evaluate it clearly. Say if it is a GOOD (right) or BAD (wrong) move. Explain why, then continue the scenario."""
                    
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
            st.session_state.sim_history.append({"role": "assistant", "content": response.text})
            
        if st.button("Restart Simulation"):
            st.session_state.sim_active = False
            st.session_state.sim_history = []
            st.rerun()

# --- 3. ADAPTIVE MICROLEARNING ---
elif choice == "Adaptive Microlearning":
    st.header("Your Daily Microlearning")
    st.write("Based on your recent simulation, here is a 3-minute module tailored for you.")
    st.subheader("Module: Effective Delegation in Crisis")
    st.write("1. Assess your team's current bandwidth.")
    st.write("2. Clearly communicate the priority tasks.")
    st.write("3. Trust your team to execute.")
    if st.button("Mark Module Complete"):
        st.balloons()
        st.success("Great job! Your next module will adapt based on this progress.")

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