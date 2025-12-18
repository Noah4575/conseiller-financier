import asyncio
import streamlit as st

from langchain_core.messages import HumanMessage, AIMessage

from llm.llm import initialize_model


# --- 1. Core Setup and Initialization ---
# Streamlit App Configuration
st.set_page_config(page_title="Conseiller Financier IA", layout="wide")
st.title("👨‍💼 Conseiller Financier IA (Crédit)")

# Initialize the LangGraph application
app = initialize_model()

# --- 2. Chat History Management (State) ---

# Initialize chat history in Streamlit session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content="Bonjour! Je suis votre conseiller financier expert."
                  " Comment puis-je vous aider avec vos projets de crédit "
                  "ce soir ?")
    ]
if "thread_id" not in st.session_state:
    # Use a fixed thread ID for persistent memory across the session
    st.session_state.thread_id = "stream_session_123"
# Updated stream_response for streamlit_app.py


def stream_response(prompt_text):
    """Generates and streams the response, handling
        multi-step tool execution."""

    # 1. Prepare inputs
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    input_messages = [HumanMessage(content=prompt_text)]
    inputs = {"messages": input_messages, "language": "Français"}

    # 2. Get the async generator
    async_generator = app.astream(inputs, config, stream_mode="values")

    def response_generator():
        # Create a clean event loop for this interaction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def get_next_chunk():
            try:
                return await async_generator.__anext__()
            except StopAsyncIteration:
                return None

        try:
            while True:
                # Fetch the next step from the graph
                event = loop.run_until_complete(get_next_chunk())

                if event is None:
                    break

                if "messages" in event:
                    message = event["messages"][-1]

                    # CASE 1: The model is responding to the user
                    if (isinstance(message, AIMessage) and
                            message.content and not message.tool_calls):
                        yield message.content

                    # CASE 2: The model requested a tool (Intermediate Step)
                    # We do NOT yield here, we just let the loop continue.
                    # LangGraph will automatically execute the tool and cycle
                    # to the model in the NEXT iteration of this 'while' loop.
                    elif isinstance(message, AIMessage) and message.tool_calls:
                        # Optional: Yield a status update to the user
                        # yield "\n*Analysing data...*\n"
                        pass

        except Exception as e:
            st.error(f"Error streaming response: {e}")
        finally:
            loop.close()

    return response_generator


# --- 4. Streamlit UI Loop ---
# Display existing messages
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

# Handle user input
if prompt := st.chat_input("Posez votre question sur le crédit..."):
    # 1. Add user message to history and display
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Display assistant response
    with st.chat_message("assistant"):
        # Use st.write_stream to display the response chunks as they arrive
        full_response = st.write_stream(stream_response(prompt))

    # 3. Save the full final AIMessage to history
    # NOTE: LangGraph's checkpointer handles saving the full history to memory
    # We only save the final displayed message for the history display
    st.session_state.messages.append(AIMessage(content=full_response))
