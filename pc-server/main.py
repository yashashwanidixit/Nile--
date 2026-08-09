from fastapi import FastAPI
from graph import compiled_graph
from db import get_guest_profile
from pydantic import BaseModel
app = FastAPI()



class AgentStepRequest(BaseModel):
    tree_text: str
    total_steps: int
    action_history: list[str]
    valid_node_ids: list[str]
    

@app.post("/agent/step")
def agent_step(data: AgentStepRequest):
   
    initial_state = {
        "screen": data.tree_text,
        "guest_profile": get_guest_profile(),
        "valid_node_ids": data.valid_node_ids,
        "result": None,
        "last_error": None,
        "retry_count": 0,
        "validation_outcome": None,
        "total_steps":  data.total_steps,
        "action_history": data.action_history,   # comes IN from phone
    }
    

    final_state = compiled_graph.invoke(initial_state)
    final_state["total_steps"] += 1 
    updated_history = final_state["action_history"] + [final_state["result"]]

    return {"final_result": final_state["result"], "retries_needed": final_state["total_steps"], "history" :updated_history}





