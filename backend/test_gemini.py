import os
from dotenv import load_dotenv

load_dotenv()

def test_gemini_3_5():
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("Testing LangChain with gemini-3.5-flash using REST transport...")
        llm = ChatGoogleGenerativeAI(google_api_key=api_key, model="gemini-3.5-flash", transport="rest")
        response = llm.invoke("Hi, reply with one word 'Success'")
        print("Success! Gemini response:", response.content)
    except Exception as e:
        print("Gemini 3.5 Flash failed with:", e)

if __name__ == "__main__":
    test_gemini_3_5()
