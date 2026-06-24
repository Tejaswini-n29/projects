const API_URL = "http://127.0.0.1:8000";

let sessionId = Date.now().toString();
let mediaRecorder;
let audioChunks = [];
let videoStream;
let isRecording = false;
let currentQuestion = "";

// DOM Elements
const roleInput = document.getElementById("role-input");
const companyInput = document.getElementById("company-input");
const resumeUpload = document.getElementById("resume-upload");
const startBtn = document.getElementById("start-btn");
const setupLoading = document.getElementById("setup-loading");
const setupScreen = document.getElementById("setup-screen");
const interviewScreen = document.getElementById("interview-screen");
const resultsScreen = document.getElementById("results-screen");
const webcam = document.getElementById("webcam");
const chatBox = document.getElementById("chat-box");
const processingStatus = document.getElementById("processing-status");
const recordAnswerBtn = document.getElementById("record-answer-btn");
const stopAnswerBtn = document.getElementById("stop-answer-btn");
const finishBtn = document.getElementById("finish-btn");
const recordingIndicator = document.getElementById("recording-indicator");
const focusIndicator = document.getElementById("focus-indicator");

function addChatMessage(sender, text) {
    const div = document.createElement("div");
    div.className = `chat-msg ${sender === 'AI' ? 'chat-ai' : 'chat-user'}`;
    div.innerHTML = `<div class="msg-label">${sender}</div><div>${text}</div>`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function speak(text) {
    window.speechSynthesis.cancel();
    // Strip HTML tags if any for speech
    const cleanText = text.replace(/<[^>]*>?/gm, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
}

startBtn.addEventListener("click", async () => {
    if (!resumeUpload.files[0]) {
        alert("Please upload a resume (PDF) to continue.");
        return;
    }
    
    startBtn.disabled = true;
    setupLoading.classList.remove("hidden");
    
    const formData = new FormData();
    formData.append("resume", resumeUpload.files[0]);
    formData.append("role", roleInput.value);
    formData.append("company", companyInput.value);
    formData.append("session_id", sessionId);
    
    try {
        const res = await fetch(`${API_URL}/upload_resume`, { method: "POST", body: formData });
        const data = await res.json();
        
        setupScreen.classList.remove("active");
        setupScreen.classList.add("hidden");
        interviewScreen.classList.remove("hidden");
        interviewScreen.classList.add("active");
        
        startCamera();
        
        // Start interview loop
        if(data.questions && data.questions.length > 0) {
            currentQuestion = data.questions[0];
            addChatMessage("AI", currentQuestion);
            speak(currentQuestion);
        } else {
            currentQuestion = "Tell me about yourself.";
            addChatMessage("AI", currentQuestion);
            speak(currentQuestion);
        }
    } catch (err) {
        alert("Error connecting to backend. Is the FastAPI server running?");
        console.error(err);
        startBtn.disabled = false;
        setupLoading.classList.add("hidden");
    }
});

async function startCamera() {
    videoStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    webcam.srcObject = videoStream;
    
    mediaRecorder = new MediaRecorder(videoStream);
    mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
    };
    mediaRecorder.onstop = processAnswer;
}

recordAnswerBtn.addEventListener("click", () => {
    window.speechSynthesis.cancel();
    audioChunks = [];
    mediaRecorder.start();
    isRecording = true;
    
    recordAnswerBtn.classList.add("hidden");
    stopAnswerBtn.classList.remove("hidden");
    finishBtn.classList.add("hidden");
    recordingIndicator.classList.remove("hidden");
});

stopAnswerBtn.addEventListener("click", () => {
    mediaRecorder.stop();
    isRecording = false;
    
    stopAnswerBtn.classList.add("hidden");
    recordingIndicator.classList.add("hidden");
    processingStatus.classList.remove("hidden");
});

async function processAnswer() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    
    const canvas = document.createElement("canvas");
    canvas.width = webcam.videoWidth;
    canvas.height = webcam.videoHeight;
    canvas.getContext("2d").drawImage(webcam, 0, 0);
    
    canvas.toBlob(async (imageBlob) => {
        const formData = new FormData();
        formData.append("audio", audioBlob, "answer.webm");
        formData.append("frame", imageBlob, "frame.jpg");
        formData.append("question", currentQuestion);
        formData.append("session_id", sessionId);
        
        try {
            const res = await fetch(`${API_URL}/evaluate`, { method: "POST", body: formData });
            const data = await res.json();
            
            // Show User Answer
            addChatMessage("You", data.transcription || "...");
            
            // Show AI Feedback & Followup
            const aiReply = `<em>Feedback: ${data.feedback}</em><br><br><strong>${data.followup}</strong>`;
            addChatMessage("AI", aiReply);
            
            currentQuestion = data.followup;
            speak(data.followup);
            
            // Update focus indicator
            if(data.focused) {
                focusIndicator.textContent = "Focus: High";
                focusIndicator.className = "focus-good";
            } else {
                focusIndicator.textContent = "Focus: Distracted";
                focusIndicator.className = "focus-bad";
            }
            
        } catch (err) {
            addChatMessage("System", "Error processing answer.");
        } finally {
            processingStatus.classList.add("hidden");
            recordAnswerBtn.classList.remove("hidden");
            finishBtn.classList.remove("hidden");
        }
    }, "image/jpeg");
}

finishBtn.addEventListener("click", async () => {
    interviewScreen.classList.remove("active");
    interviewScreen.classList.add("hidden");
    resultsScreen.classList.remove("hidden");
    resultsScreen.classList.add("active");
    
    if (videoStream) {
        videoStream.getTracks().forEach(t => t.stop());
    }
    
    document.getElementById("improvement-plan").textContent = "Generating comprehensive report...";
    
    const fd = new FormData();
    fd.append("session_id", sessionId);
    
    try {
        const res = await fetch(`${API_URL}/finish`, { method: "POST", body: fd });
        const data = await res.json();
        
        document.getElementById("final-score").textContent = `${data.average_score}/10`;
        document.getElementById("improvement-plan").textContent = data.improvement_plan;
    } catch(err) {
        document.getElementById("improvement-plan").textContent = "Error generating report.";
    }
});

document.getElementById("restart-btn").addEventListener("click", () => {
    window.location.reload();
});
