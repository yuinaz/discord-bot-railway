import os
import openai
import aiohttp
import logging
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

async def call_chatgpt(prompt, model="gpt-3.5-turbo", temperature=0.7):
    try:
        async with aiohttp.ClientSession() as session:
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            reply = response.choices[0].message["content"]
            return reply.strip()
    except Exception as e:
        logging.error(f"❌ Gagal memanggil ChatGPT: {e}")
        return "❌ Terjadi kesalahan saat memanggil ChatGPT."
