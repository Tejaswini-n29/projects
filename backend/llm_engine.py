import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import google.generativeai as genai
import PyPDF2
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=api_key)
    # Using the standard latest pro model
    model = genai.GenerativeModel('gemini-1.5-pro')
else:
    print("WARNING: GEMINI_API_KEY not set or invalid. LLM features will run in Mock Mode.")
    model = None

def parse_resume(file_path: str) -> str:
    """Extracts text from a PDF resume."""
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"Error parsing resume: {e}")
    return text

def _get_company_context(company: str) -> str:
    if company == "Amazon":
        return "You must ask questions based on Amazon's 14 Leadership Principles and expect STAR (Situation, Task, Action, Result) method answers."
    elif company == "Google":
        return "You must ask questions focusing on Googliness, extreme scale, open-ended problem solving, and complex data structures."
    elif company == "Microsoft":
        return "You must ask questions focusing on enterprise scale, system design, collaboration, and customer obsession."
    elif company == "TCS":
        return "You must ask standard IT service industry questions, focusing on core programming concepts, agile methodologies, and client communication."
    return ""

def generate_initial_questions(resume_text: str, role: str, company: str = "Generic") -> list[str]:
    """Generates 3 personalized interview questions based on the resume and role."""
    if not model:
        return [
            f"Why are you interested in the {role} position at {company}?",
            "Can you tell me about a challenging project you've worked on recently?",
            "What is your greatest technical strength and how have you applied it?"
        ]
        
    company_context = _get_company_context(company)
        
    prompt = f"""
    You are an expert technical interviewer hiring for a '{role}' position at {company}.
    {company_context}
    
    Review the following candidate resume:
    ---
    {resume_text[:2500]} 
    ---
    Generate exactly 3 specific, probing interview questions based on their experience, projects, or skills listed in the resume.
    Make the questions sound natural and conversational.
    Return ONLY the questions, separated by newlines. Do not use numbering or bullet points.
    """
    
    try:
        response = model.generate_content(prompt)
        questions = [q.strip() for q in response.text.strip().split('\n') if q.strip() and not q.startswith('#')]
        # Filter out anything that looks like a markdown list element just in case
        clean_questions = [q.lstrip('*-1234567890. ') for q in questions]
        return clean_questions[:3]
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return [f"Tell me about your experience related to {role}."]

def evaluate_and_generate_followup(question: str, answer: str, company: str = "Generic") -> dict:
    """Evaluates an answer and generates a follow-up question."""
    if not model:
        return {
            "score": 7, 
            "feedback": "Good answer. (Running in mock mode due to missing API Key).", 
            "followup": "Can you elaborate more on how you handled that?"
        }
        
    company_context = _get_company_context(company)
        
    prompt = f"""
    You are an expert technical interviewer at {company}.
    {company_context}
    
    I asked the candidate: "{question}"
    The candidate answered: "{answer}"
    
    1. Evaluate their answer strictly out of 10 based on depth, correctness, and clarity.
    2. Provide 1-2 sentences of constructive feedback.
    3. Generate a challenging follow-up question based specifically on what they just said to test their depth of knowledge.
    
    Respond strictly in the following format:
    Score: <number>
    Feedback: <text>
    Followup: <text>
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        score = 5
        feedback = "Answer received."
        followup = "Let's move on to the next topic."
        
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith("Score:"):
                try:
                    score = int(line.replace("Score:", "").strip())
                except: pass
            elif line.startswith("Feedback:"):
                feedback = line.replace("Feedback:", "").strip()
            elif line.startswith("Followup:"):
                followup = line.replace("Followup:", "").strip()
                
        return {"score": score, "feedback": feedback, "followup": followup}
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {"score": 5, "feedback": "Error evaluating answer.", "followup": "Could you explain further?"}

def evaluate_code_submission(question: str, code: str) -> dict:
    """Evaluates a code snippet for correctness and time/space complexity."""
    if not model:
        return {
            "score": 8,
            "feedback": "Your code looks syntactically correct. (Mock Mode)",
            "followup": "Can you explain the Big-O Time Complexity of this approach?"
        }
        
    prompt = f"""
    You are a strict technical interviewer evaluating a coding challenge.
    The current context/question was: "{question}"
    
    The candidate submitted the following code:
    ```
    {code}
    ```
    
    1. Evaluate the code strictly out of 10 for correctness, edge-case handling, and efficiency.
    2. Provide 2-3 sentences of feedback, explicitly stating the Time (Big-O) and Space complexity of their approach.
    3. Ask a follow-up question regarding their code (e.g. asking to optimize it, or asking about a specific edge case).
    
    Respond strictly in the following format:
    Score: <number>
    Feedback: <text>
    Followup: <text>
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        score = 5
        feedback = "Code received."
        followup = "Can you optimize this?"
        
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith("Score:"):
                try:
                    score = int(line.replace("Score:", "").strip())
                except: pass
            elif line.startswith("Feedback:"):
                feedback = line.replace("Feedback:", "").strip()
            elif line.startswith("Followup:"):
                followup = line.replace("Followup:", "").strip()
                
        return {"score": score, "feedback": feedback, "followup": followup}
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {"score": 5, "feedback": "Error evaluating code.", "followup": "Let's move on."}

def generate_improvement_plan(history: list[dict]) -> str:
    if not model:
        return "Improvement plan mocked. Please practice more coding."
        
    history_text = ""
    for item in history:
        history_text += f"Q: {item['question']}\nA: {item['answer']}\nScore: {item['score']}\n\n"
        
    prompt = f"""
    Based on the following interview history, generate a short, personalized improvement plan for the candidate.
    Highlight their weak areas and suggest 2-3 specific topics to practice.
    
    History:
    {history_text}
    """
    try:
        return model.generate_content(prompt).text
    except:
        return "Error generating improvement plan."
