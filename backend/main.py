import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class CodeRequest(BaseModel):
    code: str
    language: str
    focus_areas: list

# Serve static files
@app.get("/index.css")
async def get_css():
    return FileResponse("../frontend/index.css", media_type="text/css")

@app.get("/robot_icon.png")
async def get_robot_icon():
    return FileResponse("C:/Users/Raju/.gemini/antigravity/brain/db65b4aa-c089-4cd5-ac67-cddb7efa796a/robot_exact_background_1769840667579.png", media_type="image/png")

@app.get("/")
@app.get("/index.html")
@app.get("/app", response_class=HTMLResponse)
async def get_app():
    try:
        with open("../frontend/index.html", "r", encoding='utf-8') as f:
            content = f.read()
            content = content.replace('src="C:/Users/Raju/.gemini/antigravity/brain/db65b4aa-c089-4cd5-ac67-cddb7efa796a/robot_exact_background_1769840667579.png"', 'src="/robot_icon.png"')
            return content
    except FileNotFoundError:
        return "<h1>Error: index.html not found</h1>"

@app.get("/login", response_class=HTMLResponse)
async def get_login():
    try:
        with open("../frontend/login.html", "r", encoding='utf-8') as f:
            content = f.read()
            content = content.replace('src="C:/Users/Raju/.gemini/antigravity/brain/db65b4aa-c089-4cd5-ac67-cddb7efa796a/robot_exact_background_1769840667579.png"', 'src="/robot_icon.png"')
            return content
    except FileNotFoundError:
        return "<h1>Error: login.html not found</h1>"



@app.post("/api/review")
async def review_code(request: CodeRequest):
    try:
        focus_str = ', '.join(request.focus_areas)
        
        prompt = f"""You are an expert code reviewer. Analyze this {request.language} code focusing on: {focus_str}.

Code:
{request.code}

Provide your review with these sections:
### Critical Issues
(List any critical issues)

### High Priority  
(List high priority issues)

### Medium Priority
(List medium priority issues)

### Low Priority
(List low priority suggestions)

### REWRITTEN_CODE
IMPORTANT: Provide the complete, corrected {request.language} code below.
CRITICAL INSTRUCTION: specific to the user request, you MUST add detailed comments (inline or docstrings) within the code explaining WHY changes were made.
Do NOT include any external markdown text, notes, or explanations outside the code block.

```{request.language.lower()}
(corrected code with detailed explanation comments)
```"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        
        full_response = completion.choices[0].message.content
        
        # Split by REWRITTEN_CODE marker
        parts = full_response.split("REWRITTEN_CODE")
        review_text = parts[0].strip()
        
        # Extract rewritten code
        rewritten_code = ""
        if len(parts) > 1:
            code_section = parts[1]
            
            # Try to extract code from markdown code block
            import re
            code_block_match = re.search(r'```(?:\w+)?\n(.*?)```', code_section, re.DOTALL)
            if code_block_match:
                rewritten_code = code_block_match.group(1).strip()
                
                # Remove any explanatory text that might be in the code
                # Look for patterns like "Note:", "```java", comments at the start
                lines = rewritten_code.split('\n')
                cleaned_lines = []
                skip_next = False
                
                for line in lines:
                    stripped = line.strip()
                    # Skip lines that are clearly explanatory notes OUTSIDE of comments
                    # We allow comments (starting with #, //, /*, *)
                    if not (stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*')):
                        if any(marker in stripped.lower() for marker in ['note:', 'explanation:', 'here is the']):
                            continue

                    if skip_next and (stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('/*')):
                        continue
                    skip_next = False
                    cleaned_lines.append(line)
                
                rewritten_code = '\n'.join(cleaned_lines).strip()
            else:
                # If no code block found, just take the text after REWRITTEN_CODE
                rewritten_code = code_section.strip()
        
        return {
            "review": review_text,
            "rewritten_code": rewritten_code,
            "structured_review": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)