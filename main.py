import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# 1. Load API Key from .env file
load_dotenv()

app = FastAPI()

# 2. Initialize Groq Client
# Ensure your .env file has: GROQ_API_KEY=your_key_here
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class CodeRequest(BaseModel):
    code: str
    language: str
    focus_areas: list

# --- ROUTES ---

@app.get("/login", response_class=HTMLResponse)
async def get_login():
    """Serves the login page."""
    try:
        with open("../frontend/login.html", "r", encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: login.html not found in frontend folder</h1>"

@app.get("/app", response_class=HTMLResponse)
async def get_app():
    """Serves the main reviewer app page."""
    try:
        with open("../frontend/index.html", "r", encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: index.html not found in frontend folder</h1>"

@app.post("/api/review")
async def review_code(request: CodeRequest):
    """Handles the AI code review logic."""
    try:
        prompt = f"Review this {request.language} code focusing on {', '.join(request.focus_areas)}:\n\n{request.code}"
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return {"review": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- STARTUP ---

if __name__ == "__main__":
    import uvicorn
    # This line starts the server. All @app routes must be defined ABOVE this.
    uvicorn.run(app, host="127.0.0.1", port=8000)