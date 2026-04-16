from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
print("API KEY =", GROQ_API_KEY )

client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class ChatInput(BaseModel):
    message: str

@app.post("/chat")
async def chat(input: ChatInput):

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": input.message}]
        )

        
        ai_text = response.choices[0].message.content

        return {"reply": ai_text}

    except Exception as e:
        return {"reply": f"Error: {str(e)}"}
    









    ###uvicorn chatbot_api:app --reload --port 8000
