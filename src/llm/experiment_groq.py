import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)

api_key = os.getenv("GROQ_API_KEY", "").strip()

if not api_key:
    raise ValueError(f"GROQ_API_KEY is missing or empty in .env")

client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
    messages=[
        {
            "role": "system",
            "content": "You are a concise Python programming tutor.",
        },
        {
            "role": "user",
            "content": "Explain what an API is in three sentences.",
        },
    ],
    temperature=0.3,
    max_completion_tokens=150,
)

print("\nResponse:")
print(response.choices[0].message.content)
