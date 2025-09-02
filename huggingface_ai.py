import os
import requests

HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = "google/flan-t5-small"  # same model you were using locally
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

def query_huggingface(prompt, max_length=512):
    payload = {
        "inputs": prompt,
        "parameters": {"max_length": max_length}
    }
    response = requests.post(HF_API_URL, headers=HEADERS, json=payload)
    
    if response.status_code != 200:
        return f"Error: {response.text}"
    
    return response.json()[0]["generated_text"]

def generate_flashcards(text):
    prompt = f"Create 5 study flashcards from this text. Each flashcard should be Q&A. Text: {text}"
    output = query_huggingface(prompt, max_length=256)
    
    flashcards = []
    for line in output.split("\n"):
        if "Q:" in line and "A:" in line:
            q, a = line.split("A:", 1)
            flashcards.append([q.replace("Q:", "").strip(), a.strip()])
    return flashcards if flashcards else [["No flashcards generated", output]]

def generate_quiz(text):
    prompt = f"Create a multiple-choice quiz (3 questions) from this text. Each should have 4 options and the correct answer marked. Text: {text}"
    output = query_huggingface(prompt, max_length=512)

    quiz = []
    for block in output.split("\n\n"):
        if "?" in block:
            parts = block.split("\n")
            q = parts[0].strip()
            options = [p.strip("- ").strip() for p in parts[1:-1] if p.strip()]
            answer = parts[-1].replace("Answer:", "").strip()
            quiz.append({"question": q, "options": options, "answer": answer})
    return quiz if quiz else [{"question": "No quiz generated", "options": [], "answer": output}]