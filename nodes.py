import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_community.utilities import SQLDatabase
from state import AgentState

# Setup the LLM, model choice can be updated via env or passed in. NVIDIA's meta/llama-3.1-70b-instruct is excellent.
# We expect NVIDIA_API_KEY to be set in the environment.
def get_llm():
    return ChatNVIDIA(model="meta/llama-3.1-70b-instruct", temperature=0.1)

# Using SQLAlchemy wrapper from langchain
def get_db():
    return SQLDatabase.from_uri("sqlite:///ecommerce.db")

def generate_query(state: AgentState) -> dict:
    llm = get_llm()
    db = get_db()
    
    question = state["question"]
    sql_error = state.get("sql_error")
    
    schema = db.get_table_info()
    
    prompt = f"""
You are an expert SQL developer. Given the following SQLite database schema, write a valid SQLite SQL query that answers the user's question.
Only return the SQL query, nothing else. Do not format it in markdown blocks (no ```sql). Do not add explanations.

Schema:
{schema}

Question: {question}
"""
    
    if sql_error:
        prompt += f"\n\nContext: The previous SQL query you tried failed with this error: {sql_error}. Please carefully fix the query and try again."

    response = llm.invoke(prompt)
    
    # Clean up just in case the LLM still returns markdown
    query = response.content.strip()
    if query.startswith("```sql"):
        query = query[6:]
    if query.startswith("```"):
        query = query[3:]
    if query.endswith("```"):
        query = query[:-3]
    query = query.strip()
    
    retries = state.get("retries", 0) + 1
    
    return {"sql_query": query, "retries": retries}


def execute_query(state: AgentState) -> dict:
    db = get_db()
    query = state.get("sql_query", "")
    
    if not query:
        return {"sql_error": "No SQL query was provided by the generation step.", "db_results": None}
        
    try:
        # Run query
        results = db.run(query)
        return {"db_results": results, "sql_error": None}
    except Exception as e:
        return {"sql_error": str(e), "db_results": None}


def evaluate_result(state: AgentState) -> str:
    # If there's an error and we haven't retried too many times, go back to generate_query
    if state.get("sql_error") and state.get("retries", 0) < 3:
        return "generate_query"
    
    # Also catch unrecoverable errors (e.g. over retries), we'll let the final answer node apologize
    return "generate_answer"


def generate_answer(state: AgentState) -> dict:
    llm = get_llm()
    question = state["question"]
    sql_query = state.get("sql_query")
    db_results = state.get("db_results")
    sql_error = state.get("sql_error")
    
    if sql_error and state.get("retries", 0) >= 3:
        prompt = f"The user asked: '{question}'. However, the system encountered a SQL error and could not retrieve data after several retries: {sql_error}. Politely apologize and explain the situation to the user."
    else:
        prompt = f"""
The user asked: '{question}'.
The SQL query used: '{sql_query}'.
The database returned: '{db_results}'.

Write a concise, natural language response answering the question based on the database results. Ensure it is easily readable by an end-user.
"""
        
    response = llm.invoke(prompt)
    return {"final_answer": response.content}
