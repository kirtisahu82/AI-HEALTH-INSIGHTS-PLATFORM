async function sendMessage() {
    let input = document.getElementById("user-input");
    let text = input.value.trim();
    if (!text) return;

    let chatBox = document.getElementById("chat-box");
    chatBox.innerHTML += `<p><b>You:</b> ${text}</p>`;
    input.value = "";

    try {
        let response = await fetch("http://127.0.0.1:8000/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: text })
        });

        let data = await response.json();

        chatBox.innerHTML += `<p><b>AI:</b> ${data.reply}</p>`;
        chatBox.scrollTop = chatBox.scrollHeight;

    } catch (err) {
        chatBox.innerHTML += `<p><b>AI:</b> ❌ Error contacting server</p>`;
    }
}