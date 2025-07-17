import os
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")


response_model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0)

def load_vector_database():
    """Load the vector database from the Peer Team Report."""
    print("Loading vector database...")
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    vector_store = Chroma(
        collection_name="naac_collection",
        embedding_function=embeddings_model,
        persist_directory="./chroma_langchain_db",  # Where to save data locally, remove if not necessary
    )
    print("Vector database loaded.")
    return vector_store

def create_retriever(vector_store):
    """Query the vector database with a question."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    import os
    from langchain.retrievers.self_query.base import SelfQueryRetriever
    from langchain.chains.query_constructor.base import AttributeInfo

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
    from langchain.tools.retriever import create_retriever_tool
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
        "You are a supervisor managing two agents:\n"
        "- an sql agent. Assign tasks to this agent only if you feel that the question needs to query a database\n"
        "- a RAG agent. Assign tasks to this agent only if you feel that the question cannot be answered using queries to a database\n"
        "Assign work to one agent at a time, do not call agents in parallel.\n"
        "Do not do any work yourself."
    ),
    add_handoff_back_messages=False,

    supervisor_name="supervisor_agent",
    include_agent_name=False,
    
    ).compile()
    return supervisor