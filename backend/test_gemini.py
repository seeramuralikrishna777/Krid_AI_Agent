import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_gemini_2_5():
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("Testing LangChain with gemini-2.5-flash...")
        llm = ChatGoogleGenerativeAI(google_api_key=api_key, model="gemini-2.5-flash")
        response = await llm.ainvoke("Hi, reply with one word 'Success'")
        print("Success! Gemini response:", response.content)
    except Exception as e:
        print("Gemini 2.5 Flash failed with:", e)

if __name__ == "__main__":
    asyncio.run(test_gemini_2_5())
