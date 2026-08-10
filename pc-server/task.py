from celery_app import celery_app
from graph import compiled_graph
import time
@celery_app.task(
    bind=True,
    time_limit=600,       # hard kill after 10 minutes
    soft_time_limit=540,  # warning at 9 minutes
)
def run_agent_step(self, initial_state: dict):  
    start_time = time.time()
    
    final_state = compiled_graph.invoke(initial_state)
    final_state["total_steps"] += 1
    updated_history = final_state["action_history"] + [final_state["result"]]
    elapsed = time.time() - start_time
    print(f"[TIMING] Task took {elapsed:.2f} seconds")
    return {
        "final_result": final_state["result"],
        "retries_needed": final_state["total_steps"],
        "history": updated_history
    }