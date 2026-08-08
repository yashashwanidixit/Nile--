from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from llm import call_model
from prompts import build_decide_prompt

class AgentState(TypedDict):
    fake_screen: str
    guest_profile: dict
    valid_node_ids: list
    result: Optional[str]
    last_error: Optional[str]
    retry_count: int #this onyl determines what works within a call
    validation_outcome: Optional[str]
    total_steps: int # new — persists across the whole booking
    action_history: list #the model might confidently say "click node_101" every single turn,
    #even though clicking it isn't actually changing anything (maybe the tap isn't registering, 
    # or it's stuck on a popup). You need to catch "same action repeated with no progress," which 
    #requires comparing the current decision
    # against recent past decisions.
    plan : Optional[str]
    
def plan_node(state: AgentState) -> AgentState:
    prompt = f"""
    Here is a complex screen: {state['fake_screen']}
    Briefly outline the overall approach for this screen (not a specific action yet).
    """
    state["plan"] = call_model(prompt)   # new field, add to AgentState: plan: Optional[str]
    print(f"[PLAN] output: {state['plan']}")   
    return state    
    
def decide_node(state: AgentState) -> AgentState:
    prompt = build_decide_prompt(state["fake_screen"], state["guest_profile"], state["last_error"],state.get("plan"))
    state["result"] = call_model(prompt)
    print(f"result :{state["result"]}")
    print(f"[DECIDE] output: {state['result']}")
    return state    


def validate_node(state: AgentState) -> AgentState:
    result = state["result"]
    history = state["action_history"]
    print(f"\n[VALIDATE] checking: {result}")
    print(f"[VALIDATE] history so far: {history}")
     # Stuck check: is this exact action the same as the last 2?
    if len(history) >= 2 and history[-1] == result and history[-2] == result:
        state["validation_outcome"] = "stuck"
        print(f"[VALIDATE] outcome: stuck")
        return state

    if "PAY" in result.upper() or "CONFIRM AND PAY" in result.upper():
        state["last_error"] = f"You tried to click a Pay/Confirm button ('{result}'). This is FORBIDDEN. Choose a different, safe action instead — never touch a payment button."
        state["validation_outcome"] = "safety_violation"
        print(f"[VALIDATE] outcome: safety_violation")
        return state   # <-- add this

    if not any(node_id in result for node_id in state["valid_node_ids"]):
        state["last_error"] = "no valid node_id found"
        state["retry_count"] += 1
        state["validation_outcome"] = "invalid_node"        # new
        print(f"[VALIDATE] outcome: invalid_node, retry_count now {state['retry_count']}")
        return state

    state["last_error"] = None
    state["validation_outcome"] = "valid"                   # new
    return state

def fail_node(state: AgentState) -> AgentState:
    outcome = state["validation_outcome"]
    if outcome == "safety_violation":
        state["result"] = "FAILED: attempted forbidden action"
    elif outcome == "stuck":
        state["result"] = "FAILED: repeated same action 3 times without progress"
    elif state["total_steps"] >= MAX_TOTAL_STEPS:
        state["result"] = "FAILED: exceeded total step limit"
    elif outcome == "invalid_node":
        state["result"] = "FAILED: exceeded retries"
    print(f"[FAIL] final result set to: {state['result']}")
    return state
MAX_TOTAL_STEPS = 40
def route(state: AgentState) -> str:
    outcome = state["validation_outcome"]
    print(f"[ROUTE] deciding based on outcome: {outcome}")
    if outcome == "stuck":
        
        print(f"giving up coz the screen is stuck:route")
        return "give_up"
    if state["total_steps"] >= MAX_TOTAL_STEPS:
       
        print(f"total total steps limit is exceeded ")
        return "give_up"

    if outcome == "valid":
        print("opting out-route done ")
        return "end"

    if outcome == "safety_violation":
       
        print(f"safety viloation , giving up :route")
        return "give_up"        # new — stop immediately, don't retry a dangerous action

    if outcome == "invalid_node":
        if state["retry_count"] >= 5:
            print(f"invalid node found more than 5, givning up:route")
                      
            return "give_up"
        if state["retry_count"] == 2:
            return "replan"
        
        return "retry"

graph = StateGraph(AgentState)
graph.add_node("plan", plan_node)
graph.set_entry_point("plan")
graph.add_node("fail", fail_node)
        
graph.add_node("decide", decide_node)
graph.add_node("validate", validate_node)

graph.add_edge("plan", "decide")
graph.add_edge("decide", "validate")
graph.add_conditional_edges("validate", route, {"retry": "decide", "give_up": "fail","replan" :"plan", "end": END})
graph.add_edge("fail", END)
compiled_graph = graph.compile()