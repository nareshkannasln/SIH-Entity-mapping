document.addEventListener("DOMContentLoaded", () => {
    const uploadButton = document.getElementById("uploadButton");
    const fileInput = document.getElementById("fileInput");
    const statusMessage = document.getElementById("statusMessage");
    const output = document.getElementById("output");

    uploadButton.addEventListener("click", () => {
        const file = fileInput.files[0];
        if (!file) {
            alert("Please select a file before uploading.");
            return;
        }

        // Open a WebSocket connection
        const websocket = new WebSocket("ws://localhost:8000/process");

        websocket.onopen = () => {
            statusMessage.textContent = "Connected to server. Uploading file...";
            sendFile(websocket, file); // Send the file once the connection is open
        };

        websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data); // Parse incoming JSON data
                if (data.status === "completed") {
                    statusMessage.textContent = "Processing completed.";
                    output.textContent = JSON.stringify(data.data, null, 2);
                } else if (data.status === "failed") {
                    statusMessage.textContent = `Error: ${data.message}`;
                } else {
                    statusMessage.textContent = data.message || "Processing...";
                }
            } catch (e) {
                console.error("Failed to parse message:", e);
                statusMessage.textContent = "Unexpected server response.";
            }
        };

        websocket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            statusMessage.textContent = "Error occurred. Check the console.";
        };

        websocket.onclose = (event) => {
            if (event.wasClean) {
                console.log("WebSocket connection closed cleanly.");
            } else {
                console.error("WebSocket connection terminated unexpectedly.");
            }
        };
    });

    function sendFile(websocket, file) {
        const reader = new FileReader();

        reader.onload = () => {
            if (websocket.readyState === WebSocket.OPEN) {
                websocket.send(reader.result); // Send file as binary
                statusMessage.textContent = "File uploaded. Waiting for processing...";
            } else {
                console.error("WebSocket is not open. File upload failed.");
            }
        };

        reader.onerror = (error) => {
            console.error("FileReader error:", error);
            statusMessage.textContent = "Error reading file. Please try again.";
        };

        reader.readAsArrayBuffer(file); // Read the file as an ArrayBuffer
    }
});
const historyContainer = document.getElementById("historyContainer");

function addToHistory(message) {
    const historyItem = document.createElement("div");
    historyItem.textContent = message;
    historyContainer.appendChild(historyItem);
}

websocket.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data); // Parse incoming JSON data
        if (data.status === "completed") {
            statusMessage.textContent = "Processing completed.";
            output.textContent = JSON.stringify(data.data, null, 2);
            addToHistory("Processing completed.");
        } else if (data.status === "failed") {
            statusMessage.textContent = `Error: ${data.message}`;
            addToHistory(`Error: ${data.message}`);
        } else {
            statusMessage.textContent = data.message || "Processing...";
            addToHistory(data.message || "Processing...");
        }
    } catch (e) {
        console.error("Failed to parse message:", e);
        statusMessage.textContent = "Unexpected server response.";
        addToHistory("Unexpected server response.");
    }
};