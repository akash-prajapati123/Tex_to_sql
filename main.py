from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import sqlite3
from graph import graph
from langchain_nvidia_ai_endpoints import ChatNVIDIA

app = FastAPI(title="Text-to-SQL LLM Agent API")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    final_answer: str
    sql_query: str | None = None
    db_results: str | None = None
    sql_error: str | None = None
    retries: int


# Schema Builder Models
class ColumnDef(BaseModel):
    name: str
    type: str # TEXT, INTEGER, REAL, DATE
    is_primary: bool = False
    is_foreign_key: bool = False
    references_table: Optional[str] = None
    references_column: Optional[str] = None

class TableDef(BaseModel):
    name: str
    columns: List[ColumnDef]

class SchemaRequest(BaseModel):
    tables: List[TableDef]


def recreate_database_from_schema(schema: SchemaRequest):
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()
    
    # Drop all existing tables (for simplicity)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        if table[0] != "sqlite_sequence": # Keep auto-increment tracker
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
    
    # Create new tables
    for table in schema.tables:
        cols_sql = []
        foreign_keys = []
        
        for col in table.columns:
            col_def = f"{col.name} {col.type}"
            if col.is_primary:
                col_def += " PRIMARY KEY"
                if col.type.upper() == "INTEGER":
                    col_def += " AUTOINCREMENT"
            cols_sql.append(col_def)
            
            if col.is_foreign_key and col.references_table and col.references_column:
                foreign_keys.append(f"FOREIGN KEY({col.name}) REFERENCES {col.references_table}({col.references_column})")
        
        all_defs = cols_sql + foreign_keys
        create_sql = f"CREATE TABLE {table.name} ({', '.join(all_defs)})"
        cursor.execute(create_sql)
        
    conn.commit()
    conn.close()

def seed_mock_data(schema: SchemaRequest):
    # Use LLM to generate insert statements
    llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct", temperature=0.7)
    
    schema_desc = []
    for t in schema.tables:
        cols = [f"{c.name} ({c.type})" for c in t.columns]
        schema_desc.append(f"Table '{t.name}' with columns: {', '.join(cols)}")
    
    prompt = f"""
Given the following SQLite database schema:
{chr(10).join(schema_desc)}

Write 5-10 INSERT statements for each table to populate it with highly realistic mock data.
Make sure to respect foreign key constraints (e.g., if Order references User, make sure User exists first).
Return ONLY the raw SQL queries separated by semicolons. Do NOT wrap them in ```sql blocks. Do NOT include explanations.
"""
    response = llm.invoke(prompt)
    sql_inserts = response.content.strip()
    
    # Clean up markdown if llm ignored instructions
    if sql_inserts.startswith("```sql"): sql_inserts = sql_inserts[6:]
    if sql_inserts.startswith("```"): sql_inserts = sql_inserts[3:]
    if sql_inserts.endswith("```"): sql_inserts = sql_inserts[:-3]
    
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()
    try:
        # Execute script handles multiple statements separated by semicolons
        cursor.executescript(sql_inserts)
        conn.commit()
    except Exception as e:
        print(f"Data seeding warning: {e}")
        conn.rollback()
    finally:
        conn.close()


@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/api/schema")
def build_schema_endpoint(req: SchemaRequest):
    try:
        recreate_database_from_schema(req)
        # Attempt to auto-seed realistic mock data so chat works out-of-the-box
        seed_mock_data(req)
        return {"status": "success", "message": "Schema deployed and seeded with mock data successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=QueryResponse)
def chat_endpoint(req: QueryRequest):
    if not os.environ.get("NVIDIA_API_KEY"):
        raise HTTPException(status_code=500, detail="NVIDIA_API_KEY environment variable not set. Please set it securely.")
        
    initial_state = {"question": req.question, "retries": 0}
    
    try:
        # Pass state through LangGraph
        final_state = graph.invoke(initial_state)
        
        return QueryResponse(
            final_answer=final_state.get("final_answer", "Sorry, I could not generate an answer."),
            sql_query=final_state.get("sql_query"),
            db_results=str(final_state.get("db_results")) if final_state.get("db_results") else None,
            sql_error=final_state.get("sql_error"),
            retries=final_state.get("retries", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Execution Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
