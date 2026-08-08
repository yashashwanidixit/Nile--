import ollama


def call_model(prompt: str, model: str = "qwen3:8b") ->str :
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        options={"num_predict": 60, "temperature": 0},
        
    )
    
    return response["message"]["content"].strip()