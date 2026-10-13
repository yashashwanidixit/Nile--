import concurrent.futures

import ollama


class ModelTimeoutError(TimeoutError):
    """Raised when an LLM call hangs longer than the explicit timeout."""
    pass


def call_model(prompt: str, model: str = "qwen3:8b", timeout: float = 60.0) -> str:
    """Call the LLM with an explicit timeout.

    A hung Ollama request used to block a Celery worker forever.
    Now the call runs in a helper thread and raises ModelTimeoutError
    (a TimeoutError subclass) if it takes longer than `timeout` seconds,
    so callers (node retry policy / Celery retry) can back off and retry.
    """

    def _do_call() -> str:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            think=False,
            options={"num_predict": 60, "temperature": 0},

        )
        return response["message"]["content"].strip()

    # NOTE: we deliberately avoid `with ThreadPoolExecutor(...)` here:
    # its __exit__ calls shutdown(wait=True), which would block until the
    # hung Ollama thread finishes — defeating the timeout. Instead we shut
    # down with wait=False so the caller fails fast; the orphan thread is
    # left to die on its own (threads can't be killed in Python).
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_do_call)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise ModelTimeoutError(
            f"LLM call timed out after {timeout}s"
        ) from exc
    else:
        executor.shutdown(wait=True)