def build_decide_prompt(fake_screen: str, guest_profile: dict, last_error: str | None, plan: str | None = None) -> str:
    error_note = f"\n\n⚠️ IMPORTANT — your last attempt was rejected: {last_error}\nDo NOT repeat that mistake. Choose differently this time.\n" if last_error else ""
    plan_note = (
        f"\nYou already outlined this approach for the screen: {plan}\n"
        f"Follow that approach — decide the next single action that moves it forward."
        if plan else ""
    )

    return f"""
    You are booking a hotel room. Here is the current screen:
    {fake_screen}
    {plan_note}
    Rules:
    - If any guest detail fields on screen are still empty, fill the next 
    empty one — do NOT click Proceed/Continue/Next until all relevant 
    fields are filled.
    - Only click Proceed/Continue/Next once every field you can fill with 
    the guest details above has been filled.

    Guest name: {guest_profile['name']}, email: {guest_profile['email']}, phone: {guest_profile['phone']}.

    Decide ONLY the single next action.

    Respond with ONLY one line, in this EXACT format, with no extra spaces:
    ACTION:<click|set_text> NODE_ID:<the bracketed id, e.g. node_104> NODE_LABEL:<the element's text label> VALUE:<text to type, or none>

    Example — if the screen shows [node_101] TextField "Full Name" (empty), and you want to fill it, respond exactly like this:
    ACTION:set_text NODE_ID:node_101 NODE_LABEL:Full Name VALUE:Priya Sharma

    Example — if the screen shows [node_104] Button "Proceed" and you want to click it, respond exactly like this:
    ACTION:click NODE_ID:node_104 NODE_LABEL:Proceed VALUE:none
    {error_note}
    """