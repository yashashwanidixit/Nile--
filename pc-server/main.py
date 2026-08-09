from fastapi import FastAPI
from graph import compiled_graph
from db import get_guest_profile
app = FastAPI()

@app.post("/agent/step")
def agent_step(data: dict):
   
    initial_state = {
        "screen": data.get("tree_text",""),
        "guest_profile": get_guest_profile(),
        "valid_node_ids": ["node_101", "node_102", "node_103", "node_104"],
        "result": None,
        "last_error": None,
        "retry_count": 0,
        "validation_outcome": None,
        "total_steps":  data.get("total_steps", 0) ,
        "action_history": data.get("action_history", []),   # comes IN from phone
    }
    

    final_state = compiled_graph.invoke(initial_state)
    final_state["total_steps"] += 1 
    updated_history = final_state["action_history"] + [final_state["result"]]

    return {"final_result": final_state["result"], "retries_needed": final_state["total_steps"], "history" :updated_history}





