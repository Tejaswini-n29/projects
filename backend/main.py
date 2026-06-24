import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import cv2
import numpy as np
from faster_whisper import WhisperModel
from deepface import DeepFace

from llm_engine import parse_resume, generate_initial_questions, evaluate_and_generate_followup, evaluate_code_submission, generate_improvement_plan
from cv_engine import analyze_stress_and_focus

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading Whisper Model...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Whisper Model Loaded.")

# In-memory store for session (in production use Redis/DB)
sessions = {}

@app.get("/")
def read_root():
    return {"message": "SmartHire AI V3 is running"}

@app.post("/upload_resume")
async def upload_resume(
    resume: UploadFile = File(...), 
    role: str = Form(...), 
    company: str = Form(...),
    session_id: str = Form(...)
):
    temp_path = f"temp_{session_id}_{resume.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)
        
    try:
        text = parse_resume(temp_path)
        questions = generate_initial_questions(text, role, company)
        
        sessions[session_id] = {
            "questions": questions,
            "current_q_idx": 0,
            "history": [],
            "company": company
        }
        
        return {"questions": questions}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/evaluate")
async def evaluate_answer(
    audio: UploadFile = File(...), 
    frame: UploadFile = File(...), 
    question: str = Form(...),
    session_id: str = Form(...)
):
    # Retrieve company context
    company = "Generic"
    if session_id in sessions:
        company = sessions[session_id].get("company", "Generic")
        
    # 1. Transcribe Audio
    temp_audio_path = f"temp_audio_{session_id}.webm"
    with open(temp_audio_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
        
    try:
        segments, _ = whisper_model.transcribe(temp_audio_path, beam_size=5)
        answer_text = " ".join([segment.text for segment in segments]).strip()
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            
    # 2. Analyze Frame (Emotion + Focus)
    contents = await frame.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    emotion = "neutral"
    try:
        result = DeepFace.analyze(img, actions=['emotion'], enforce_detection=False)
        if isinstance(result, list): result = result[0]
        emotion = result['dominant_emotion']
    except: pass
    
    focus_data = analyze_stress_and_focus(img)
    
    # 3. LLM Evaluation & Follow-up
    eval_result = evaluate_and_generate_followup(question, answer_text, company)
    
    # Update History
    if session_id in sessions:
        sessions[session_id]["history"].append({
            "question": question,
            "answer": answer_text,
            "score": eval_result["score"],
            "emotion": emotion,
            "focused": focus_data["focused"],
            "type": "verbal"
        })
    
    return {
        "transcription": answer_text,
        "emotion": emotion,
        "focused": focus_data["focused"],
        "score": eval_result["score"],
        "feedback": eval_result["feedback"],
        "followup": eval_result["followup"]
    }

@app.post("/evaluate_code")
async def evaluate_code(
    question: str = Form(...),
    code: str = Form(...),
    session_id: str = Form(...)
):
    eval_result = evaluate_code_submission(question, code)
    
    if session_id in sessions:
        sessions[session_id]["history"].append({
            "question": question,
            "answer": code,
            "score": eval_result["score"],
            "emotion": "focused",
            "focused": True,
            "type": "code"
        })
        
    return {
        "score": eval_result["score"],
        "feedback": eval_result["feedback"],
        "followup": eval_result["followup"]
    }

@app.post("/finish")
async def finish_interview(session_id: str = Form(...)):
    if session_id not in sessions:
        return {"error": "Session not found"}
        
    history = sessions[session_id]["history"]
    plan = generate_improvement_plan(history)
    
    # Calculate average score
    avg_score = sum(h["score"] for h in history) / len(history) if history else 0
    
    return {
        "average_score": round(avg_score, 1),
        "improvement_plan": plan,
        "history": history
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
