import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

resp = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You write short, helpful customer support email replies."},
        {"role": "user", "content": "A customer asked: 'Need pricing and timeline for website + SEO'. Draft a reply."},
    ],
)

print(resp.choices[0].message.content)
