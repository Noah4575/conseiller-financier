import streamlit as st

from langchain_core.messages import HumanMessage, AIMessage

from llm.llm import initialize_model

# --- 1. Core Setup and Initialization ---
st.set_page_config(page_title="Conseiller Financier IA", layout="wide")
st.title("👨‍💼 Conseiller Financier IA (Crédit)")

# Initialize the LangGraph application
app = initialize_model()

# --- 2. Chat History Management (State) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content="Bonjour! Je suis votre conseiller financier expert."
                  " Comment puis-je vous aider avec vos projets de crédit "
                  "ce soir ?")
    ]
if "thread_id" not in st.session_state:
    # Use a fixed thread ID for persistent memory across the session
    st.session_state.thread_id = "stream_session_123"

for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)


if user_input := st.chat_input("Votre demande..."):
    # 1. Display User Message
    st.chat_message("user").write(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))

    # 2. Run the AI (Synchronously)
    with st.chat_message("assistant"):
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {"messages": [HumanMessage(content=user_input)],
                  "language": "Français"}

        # Container for the text stream
        message_placeholder = st.empty()
        full_response = ""

        # SIMPLE FOR LOOP - No async, no await, no event loops!
        # app.stream is the synchronous version of app.astream
        for event in app.stream(inputs, config, stream_mode="values"):
            if "messages" in event:
                msg = event["messages"][-1]

                # Check if it's a final response (not a tool call)
                if (isinstance(msg, AIMessage) and msg.content
                   and not msg.tool_calls):
                    full_response = msg.content
                    message_placeholder.markdown(full_response)

        # Save final response to history
        st.session_state.messages.append(AIMessage(content=full_response))
