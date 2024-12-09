from langchain_ollama import OllamaLLM  # Updated import for Ollama
import asyncio

def load_model():
    return OllamaLLM(model="gemma2:9b", temperature=0)