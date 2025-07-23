import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
import streamlit as st
st.set_page_config(layout="wide")
from naac_agent import create_rag_agent, create_sql_agent, create_supervisor_agent  # Import your agent
from langchain_core.messages import AIMessage

# Load the agents
rag_agent = create_rag_agent()
sql_agent = create_sql_agent()
supervisor_agent = create_supervisor_agent(sql_agent, rag_agent)

# Streamlit UI
st.title("KNAACK: Know about NAAC Accredited Institutes and Universities")

question = ""
with st.form("my_form"):
    question = st.text_input("Enter your question related to NAAC accreditation or NAAC accredited universities:")
    submitted = st.form_submit_button("Submit")
    st.write(":grey[Example 1: What are some of the green campus initiatives at FLAME UNIVERSITY?]")
    st.write(":grey[Example 2: What does the FLAME Centre for Entrepreneurship do?]")
    st.write(":grey[Example 3: Which institutes have got the highest grade for Criteria 2?]")
    if submitted:    
        # st.write("Example 3: Show me the NAAC grade details of  Shri Shankaracharya Institute of Professional Management and Technology?")
        result = ""
        with st.spinner("Fetching answer..."):
            # Call the supervisor agent with the user's question, using stream
            result = supervisor_agent.invoke({"messages": [{"role": "user", "content": question}]})

        st.write("Answer:")
        response_parts = []
        for message in result["messages"]:
            # We look for AIMessages that have content and are not tool calls.
            if isinstance(message, AIMessage) and message.content:
                if not getattr(message, "tool_calls", None) and "function_call" not in message.additional_kwargs:
                    response_parts.append(message.content)

        response_text = "\n".join(response_parts)
        st.write(response_text)