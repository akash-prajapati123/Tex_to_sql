from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import generate_query, execute_query, evaluate_result, generate_answer

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Adding nodes
    workflow.add_node("generate_query", generate_query)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("generate_answer", generate_answer)
    
    # Setting entry point
    workflow.set_entry_point("generate_query")
    
    # Edges
    workflow.add_edge("generate_query", "execute_query")
    
    workflow.add_conditional_edges(
        "execute_query",
        evaluate_result,
        {
            "generate_query": "generate_query",
            "generate_answer": "generate_answer"
        }
    )
    
    workflow.add_edge("generate_answer", END)
    
    return workflow.compile()

graph = build_graph()
