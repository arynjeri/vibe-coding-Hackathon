async function generateContent(mode) {
  const text = document.getElementById("inputText").value.trim();
  if (!text) {
    alert("Please paste some text to generate " + mode);
    return;
  }

  try {
    const res = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, mode })   // ✅ send "mode" to match Flask
    });

    const data = await res.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    if (mode === "flashcards") {
      const container = document.getElementById("flashcards");
      container.innerHTML = "";
      data.flashcards.forEach(([q, a]) => {
        const card = document.createElement("div");
        card.className = "flashcard"; // ✅ match your CSS
        card.innerHTML = `<h3>Q: ${q}</h3><p>A: ${a}</p>`;
        container.appendChild(card);
      });
    }

    if (mode === "quiz") {
      const container = document.getElementById("quiz");
      container.innerHTML = "";
      data.quiz.forEach((q, i) => {
        const item = document.createElement("div");
        item.className = "quiz-question"; // ✅ match your CSS
        item.innerHTML = `
          <h3>Q${i + 1}: ${q.question}</h3>
          <div class="quiz-options">
            ${q.options
              .map(opt => `<button class="quiz-option">${opt}</button>`)
              .join("")}
          </div>
        `;
        container.appendChild(item);
      });
    }
  } catch (err) {
    console.error("Error:", err);
    alert("Something went wrong. Check server logs.");
  }
}

// Toggle forms
function showRegister() {
  document.getElementById("loginForm").style.display = "none";
  document.getElementById("registerForm").style.display = "block";
}

function showLogin() {
  document.getElementById("registerForm").style.display = "none";
  document.getElementById("loginForm").style.display = "block";
}
