from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from groq import Groq
import os
from dotenv import load_dotenv
import re
import uvicorn
# Load environment variables from .env
load_dotenv()

app = FastAPI()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Generation Settings
MODEL_NAME = "llama-3.3-70b-versatile"
TEMPERATURE = 0.3
MAX_TOKENS = 2000
TOP_P = 0.9

# Data Models for API Requests/Responses
class CodeReviewRequest(BaseModel):
    code: str
    language: str
    focus_areas: list[str]

class CodeReviewResponse(BaseModel):
    review: str
    structured_review: dict
    rewritten_code: str

def parse_review_response(review_text: str) -> dict:
    """Extract and categorize feedback by priority levels"""
    # Regex patterns for priority sections
    patterns = {
        "critical": r'### Critical Issues.*?(?=###|\Z)',
        "high": r'### High Priority.*?(?=###|\Z)',
        "medium": r'### Medium Priority.*?(?=###|\Z)',
        "low": r'### Low Priority.*?(?=###|\Z)'
    }
    
    results = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, review_text, re.DOTALL)
        results[key] = match.group(0).strip() if match else ""
    
    return results

@app.get("/app", response_class=HTMLResponse)
async def serve_tool():
    """Serve the main tool interface (index.html)"""
    try:
        # Assumes frontend/index.html is one level up from backend/main.py
        with open("../frontend/index.html", "r", encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)

@app.post("/api/review", response_model=CodeReviewResponse)
async def review_code(request: CodeReviewRequest):
    """Analyze code and provide AI-driven suggestions"""
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    
    focus_str = ", ".join(request.focus_areas)
    
    # Prompt for the AI Reviewer
    prompt = (
        f"You are an expert code reviewer with 15+ years of experience. "
        f"Analyze this {request.language} code focusing on: {focus_str}.\n\n"
        f"Code:\n{request.code}\n\n"
        "Provide your review with sections: ### Critical Issues, ### High Priority, "
        "### Medium Priority, and ### Low Priority. Also provide the optimized 'REWRITTEN_CODE' at the end."
    )

    try:
        # Request inference from Groq
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=TOP_P
        )
        
        full_response = completion.choices[0].message.content
        
        # Split review from rewritten code
        parts = full_response.split("REWRITTEN_CODE")
        review_text = parts[0]
        rewritten_code = parts[1] if len(parts) > 1 else ""
        
        return {
            "review": review_text,
            "structured_review": parse_review_response(review_text),
            "rewritten_code": rewritten_code.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Start the server on localhost
    uvicorn.run(app, host="127.0.0.1", port=8000)
