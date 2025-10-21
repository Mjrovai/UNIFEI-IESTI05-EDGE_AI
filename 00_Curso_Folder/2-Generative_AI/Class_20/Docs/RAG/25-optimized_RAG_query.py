#!/usr/bin/env python
# coding: utf-8

# Optimized RAG Query System
# - Edge AI Engineering with Raspberry Pi

import time
import warnings
import os
import requests
import concurrent.futures
from functools import lru_cache
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser

# Suppress warnings
warnings.filterwarnings("ignore", 
                        message="API key must be provided when using hosted LangSmith API",
                        category=UserWarning)

# models
MODEL = "llama3.2:3b"
EMBED = "nomic-embed-text"

# Define persistent directory for Chroma
PERSIST_DIRECTORY = "chroma_db"

# Direct Ollama API functions for better performance
def direct_ollama_embed(text):
    """Get embeddings directly from Ollama API"""
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": EMBED, "prompt": text}
    )
    if response.status_code == 200:
        return response.json()["embedding"]
    else:
        raise Exception(f"Error from Ollama API: {response.status_code}")

# Cache embeddings to avoid recalculating
@lru_cache(maxsize=100)
def cached_embed_query(text):
    """Cache embeddings for repeated queries"""
    return direct_ollama_embed(text)

# Custom embedding class that uses Ollama directly and implements caching
class OptimizedOllamaEmbeddings:
    def embed_query(self, text):
        """Get embeddings for a query with caching"""
        return cached_embed_query(text)
    
    def embed_documents(self, documents):
        """Get embeddings for documents - not cached as this is mainly used during DB creation"""
        results = []
        # Process in batches of 4 for efficiency
        batch_size = 4
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                batch_results = list(executor.map(direct_ollama_embed, batch))
            results.extend(batch_results)
        return results

def generate_llm_response(prompt):
    """Generate response directly from Ollama API"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 512,
                "temperature": 0,
                "top_k": 40,
                "top_p": 0.9,
                "seed": 42  # Fixed seed for consistent outputs
            }
        }
    )
    if response.status_code == 200:
        return response.json()["response"]
    else:
        return f"Error: Received status code {response.status_code} from Ollama API"

def preload_models():
    """Preload models to avoid cold starts"""
    print("Preloading models...")
    try:
        # Preload embedding model
        _ = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": EMBED, "prompt": "warmup"},
            timeout=30
        )
        
        # Preload LLM
        _ = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL, 
                "prompt": "warmup", 
                "stream": False,
                "options": {"num_predict": 1}
            },
            timeout=30
        )
        print("Models preloaded successfully")
    except Exception as e:
        print(f"Warning: Model preloading failed: {e}")
        print("Continuing anyway - first query may be slower")

def load_retriever():
    """Load the vector store from disk and create an optimized retriever"""
    if not os.path.exists(PERSIST_DIRECTORY):
        raise FileNotFoundError(f"Database directory {PERSIST_DIRECTORY} not found. Please run create-database.py first.")
    
    print("Loading existing vector store...")
    
    embedding_function = OptimizedOllamaEmbeddings()
    vectorstore = Chroma(
        collection_name="rag-edgeai-eng-chroma",
        embedding_function=embedding_function,
        persist_directory=PERSIST_DIRECTORY
    )
    
    # Create retriever with optimized settings
    retriever = vectorstore.as_retriever(
        search_type="similarity",  # Basic similarity is fastest
        search_kwargs={
            "k": 2  # Retrieve fewer documents
        }
    )
    return retriever

def answer_question(question, retriever):
    """Generate an answer using the RAG system with optimized processing"""
    # Start timing
    start_time = time.time()
    
    # Retrieve relevant documents
    print(f"Question: {question}")
    print("Retrieving documents...")
    docs = retriever.invoke(question)
    
    # Early check if we found any relevant documents
    if not docs:
        end_time = time.time()
        latency = end_time - start_time
        print(f"No relevant documents found. Response latency: {latency:.2f} seconds")
        return "I don't have enough information to answer this question accurately."
    
    # Process documents - extract only what we need
    docs_content = "\n\n".join(doc.page_content for doc in docs)
    print(f"Retrieved {len(docs)} document chunks")
    
    # Generate answer
    print("Generating answer...")
    
    # Simplified RAG prompt for efficiency
    rag_prompt = f"""
You are an AI assistant specialized in Edge AI Engineering with Raspberry Pi.
Answer the following question based only on the information provided in the context below.
Be concise and direct. If the context doesn't contain relevant information, admit that you don't know.

Context:
{docs_content}

Question: {question}

Answer:
"""
    
    # Generate answer through direct API call
    answer = generate_llm_response(rag_prompt)
    
    # Calculate and print latency
    end_time = time.time()
    latency = end_time - start_time
    print(f"Response latency: {latency:.2f} seconds using model: {MODEL}")
    
    return answer

def interactive_mode():
    """Run an interactive query session"""
    try:
        # Preload models to avoid cold start latency
        preload_models()
        
        # Load the retriever once
        retriever = load_retriever()
        
        print("\n==== Optimized RAG Query System ====")
        print("Type your questions and press Enter. Type 'quit' to exit.")
        
        while True:
            question = input("\nYour question: ")
            if question.lower() in ['quit', 'exit', 'q']:
                break
            
            print("\nGenerating answer...\n")
            answer = answer_question(question, retriever)
            
            print("\nANSWER:")
            print("="*50)
            print(answer)
            print("="*50)
    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    interactive_mode()