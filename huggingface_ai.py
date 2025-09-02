from transformers import pipeline

# Force PyTorch backend (avoids TensorFlow/Keras issues)
qa_pipeline = pipeline(
    "text2text-generation",
    model="google/flan-t5-small",
    framework="pt"
)

def generate_flashcards(text):
    # This is a stub – adjust for your prompt
    prompt = f"Create 5 study flashcards from this text. Each flashcard should be Q&A. Text: {text}"
    output = qa_pipeline(prompt, max_length=256, num_return_sequences=1)[0]["generated_text"]
    
    # TODO: parse into list of [question, answer]
    flashcards = []
    for line in output.split("\n"):
        if "Q:" in line and "A:" in line:
            q, a = line.split("A:", 1)
            flashcards.append([q.replace("Q:", "").strip(), a.strip()])
    return flashcards

def generate_quiz(text):
    prompt = f"Create a multiple-choice quiz (3 questions) from this text. Each should have 4 options and the correct answer marked. Text: {text}"
    output = qa_pipeline(prompt, max_length=512, num_return_sequences=1)[0]["generated_text"]

    # TODO: parse string into {question, options, answer}
    quiz = []
    # Example placeholder parsing
    for block in output.split("\n\n"):
        if "?" in block:
            parts = block.split("\n")
            q = parts[0].strip()
            options = [p.strip("- ").strip() for p in parts[1:-1] if p.strip()]
            answer = parts[-1].replace("Answer:", "").strip()
            quiz.append({"question": q, "options": options, "answer": answer})
    return quiz
