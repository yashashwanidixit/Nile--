from fastapi import FastAPI
from graph import compiled_graph
from db import get_guest_profile
from pydantic import BaseModel
import time
import uuid
from task import run_agent_step
from celery.result import AsyncResult
from celery_app import celery_app

app = FastAPI()



class AgentStepRequest(BaseModel):
    tree_text: str
    total_steps: int
    action_history: list[str]
    valid_node_ids: list[str]
    thread_id: str | None = None  # reuse one id per booking to allow resume


@app.post("/agent/step")
def agent_step(data: AgentStepRequest):
    start_time = time.time()

    # One stable thread_id per booking lets the graph checkpointer resume
    # a crashed/Celery-retried run from the last completed node.
    thread_id = data.thread_id or str(uuid.uuid4())

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
        "plan": None,
    }

    task = run_agent_step.delay(initial_state, thread_id=thread_id)   # fires the task, returns immediately
    return {"task_id": task.id, "thread_id": thread_id}

@app.get("/agent/step/result/{task_id}")
def get_result(task_id: str):
    result = celery_app.AsyncResult(task_id)
    if result.ready():
        payload = result.result
        # Celery-level failure contract: task always returns a dict with
        # status "done" | "failed" — unless the worker itself was hard-killed,
        # in which case result.failed() is True and payload is an exception.
        if isinstance(payload, dict) and payload.get("status") == "failed":
            return {"status": "failed", "result": payload}
        if result.failed():
            return {"status": "failed", "result": {"status": "failed", "error": str(payload)}}
        return {"status": "done", "result": payload}
    return {"status": "pending"}
