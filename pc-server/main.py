from fastapi import FastAPI
from graph import compiled_graph
from db import get_guest_profile
from pydantic import BaseModel
import time
from task import run_agent_step
from celery.result import AsyncResult
from celery_app import celery_app

app = FastAPI()



class AgentStepRequest(BaseModel):
    tree_text: str
    total_steps: int
    action_history: list[str]
    valid_node_ids: list[str]
    

@app.post("/agent/step")
def agent_step(data: AgentStepRequest):
    start_time = time.time()
   
    initial_state = {
        "fake_screen": data.tree_text,
        "guest_profile": get_guest_profile(),
        "valid_node_ids": data.valid_node_ids,
        "result": None,
        "last_error": None,
        "retry_count": 0,
        "validation_outcome": None,
        "total_steps":  data.total_steps,
        "action_history": data.action_history,   # comes IN from phone
    }
    
    task = run_agent_step.delay(initial_state)   # fires the task, returns immediately
    return {"task_id": task.id}  

@app.get("/agent/step/result/{task_id}")
def get_result(task_id: str):
    result = celery_app.AsyncResult(task_id)
    if result.ready():
        return {"status": "done", "result": result.result}
    return {"status": "pending"}

    




