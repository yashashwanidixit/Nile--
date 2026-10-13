from celery.exceptions import MaxRetriesExceededError
from celery_app import celery_app
from graph import compiled_graph
from llm import ModelTimeoutError
import time
import uuid


@celery_app.task(
    bind=True,
    time_limit=600,       # hard kill after 10 minutes
    soft_time_limit=540,  # warning at 9 minutes
    max_retries=3,
)
def run_agent_step(self, initial_state: dict, thread_id: str | None = None):
    """Run one agent step through the LangGraph.

    Celery-level retry: a TimeoutError/ModelTimeoutError from a hung LLM
    call retries the WHOLE task with exponential backoff. The graph's
    checkpointer (keyed by the same thread_id) means the retry resumes
    from the last completed node instead of redoing finished work.
    Once retries run out, return a clean failure dict (status="failed")
    so the /result polling endpoint never hangs or leaks a traceback.
    """
    start_time = time.time()
    # Keep the same thread_id across Celery retries so the checkpointer
    # can resume. A brand-new uuid is minted only for a brand-new step.
    thread_id = thread_id or initial_state.pop("thread_id", None) or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_state = compiled_graph.invoke(initial_state, config=config)
    except (TimeoutError, ModelTimeoutError) as exc:
        # Exponential backoff: 5s, 10s, 20s ... (request.retries = 0,1,2)
        countdown = 5 * (2 ** self.request.retries)
        try:
            raise self.retry(exc=exc, countdown=countdown, max_retries=3)
        except MaxRetriesExceededError:
            return {
                "status": "failed",
                "error": f"LLM timed out after retries: {exc}",
                "thread_id": thread_id,
            }
    except Exception as exc:  # non-retryable crash -> clean failure, no worker traceback leak
        return {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "thread_id": thread_id,
        }

    final_state["total_steps"] += 1
    updated_history = final_state["action_history"] + [final_state["result"]]
    elapsed = time.time() - start_time
    print(f"[TIMING] Task took {elapsed:.2f} seconds")
    return {
        "status": "done",
        "final_result": final_state["result"],
        "retries_needed": final_state["total_steps"],
        "history": updated_history,
        "thread_id": thread_id,
    }
