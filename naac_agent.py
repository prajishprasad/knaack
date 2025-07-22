import os
from langchain.chat_models import init_chat_model
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.tools.retriever import create_retriever_tool
import streamlit as st
load_dotenv()
# st.write("GOOGLE_API_KEY", st.secrets["GOOGLE_API_KEY"])
# st.write("PINECONE_API_KEY", st.secrets["PINECONE_API_KEY"])

os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
response_model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0)

def load_vector_database():
    """Load the vector database from the Peer Team Report."""
    print("Loading vector database...")
    pinecone_api_key = st.secrets["PINECONE_API_KEY"]

    pc = Pinecone(
            api_key=pinecone_api_key
    )
    index_name = "naac-index"
    # Initialize index client
    index = pc.Index(name=index_name)
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = PineconeVectorStore(index=index, embedding=embeddings_model)
    print("Vector database loaded.")
    return vector_store

def create_retriever(vector_store):
    """Query the vector database with a question."""

    metadata_field_info = [
    AttributeInfo(
        name="college_name",
        description="The name of the college or institution. Need not be an exact name match",
        type="string",

        filter_match_type="contains"  # This makes the matching more flexible
    )
    ]
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        # other params...
    )
    retriever = SelfQueryRetriever.from_llm(
        llm,
        vector_store,
        "NAAC peer team report chunk",
        metadata_field_info=metadata_field_info,
        enable_limit=True,
    )
    retriever_tool = create_retriever_tool(
        retriever,
        "retrieve_naac_information_from_vector_db",
        "retrieve information from the NAAC vector database, which has information about the NAAC Peer Reports of various colleges.",
    )

    return retriever_tool

def create_sql_agent():
    db = SQLDatabase.from_uri("sqlite:///naac_accreditation.db")
    print(f"Dialect: {db.dialect}")
    print(f"Available tables: {db.get_usable_table_names()}")
    toolkit = SQLDatabaseToolkit(db=db, llm=response_model)
    tools = toolkit.get_tools()

    system_prompt = """
    You are an agent designed to interact with a SQL database.
    Given an input question, create a syntactically correct {dialect} query to run,
    then look at the results of the query and return the answer. Unless the user
    specifies a specific number of examples they wish to obtain, always limit your
    query to at most {top_k} results.

    You can order the results by a relevant column to return the most interesting
    examples in the database. Never query for all the columns from a specific table,
    only ask for the relevant columns given the question.

    You MUST double check your query before executing it. If you get an error while
    executing a query, rewrite the query and try again.

    DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
    database.

    To start you should ALWAYS look at the tables in the database to see what you
    can query. Do NOT skip this step.

    Then you should query the schema of the most relevant tables.
    """.format(
        dialect=db.dialect,
        top_k=5,
    )

    sql_agent = create_react_agent(
        response_model,
        tools,
        prompt=system_prompt,
        name="sql_agent",
        checkpointer=False
    )
    return sql_agent

def create_rag_agent():
    """Create a RAG agent that can answer questions about NAAC Peer Team Reports."""
    vector_store = load_vector_database()
    retriever_tool = create_retriever(vector_store)
    
    # Create the RAG agent
    rag_agent = create_react_agent(
        response_model,
        [retriever_tool],
        name="rag_agent",
        prompt="""
        You are an agent designed to answer questions about NAAC Peer Team Reports of different colleges.
        Use the provided tools to retrieve information.
        The name of the college may not always be accurate. 
        You can retrieve information from similar college names and filter the results.
        """,
        checkpointer=False
    )
    
    return rag_agent

def create_supervisor_agent(sql_agent, rag_agent):
    """Create a supervisor agent that can manage the RAG agent and SQL agent."""
    supervisor = create_supervisor(
    model=response_model,
    agents=[sql_agent, rag_agent],
    prompt=(
        """You are a supervisor managing two agents:
        (1) An SQL agent - Assign tasks to this agent only if you feel that the question needs to query a database 
        - e.g. questions related to 
        (a) the grade of an institution
        (b) Specific criteria grades,
        (c) Key indicator grades.
        and a combination of these queries.

        (2) a RAG agent - Assign tasks to this agent only if you feel that the question cannot be answered using queries to a database mentioned above.
        Assign work to one agent at a time, do not call agents in parallel.
        Do not do any work yourself."""
    ),
    add_handoff_back_messages=False,

    supervisor_name="supervisor_agent",
    include_agent_name=False,
    
    ).compile()
    return supervisor