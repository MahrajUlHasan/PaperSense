"""
LLM service using Google Gemini API for text generation
"""
from typing import List, Dict, Optional
import google.generativeai as genai
from loguru import logger
from config import settings


class LLMService:
    """Google Gemini LLM service for generation"""
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        
        # Generation configuration
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
    
    def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate response from Gemini
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Generated text response
        """
        try:
            config = self.generation_config.copy()
            config["temperature"] = temperature
            
            response = self.model.generate_content(
                prompt,
                generation_config=config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return f"Error generating response: {str(e)}"
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Generate a summary of the given text"""
        prompt = f"""
Please provide a concise summary of the following research paper text.
Focus on the key findings, methodology, and conclusions.
Keep the summary under {max_length} words.

Text:
{text}

Summary:
"""
        return self.generate_response(prompt, temperature=0.5)
    
    def answer_question(self, question: str, context_chunks: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Answer a question based on retrieved context chunks
        
        Args:
            question: User's question
            context_chunks: Retrieved relevant chunks from vector store
            
        Returns:
            Dictionary with answer and citations
        """
        # Build context from chunks
        context_parts = []
        citations = []
        
        for i, chunk in enumerate(context_chunks):
            context_parts.append(f"[{i+1}] {chunk['text']}")
            citations.append({
                "index": i + 1,
                "section": chunk.get('section', 'unknown'),
                "score": chunk.get('score', 0.0),
                "document_id": chunk.get('document_id', '')
            })
        
        context = "\n\n".join(context_parts)
        
        # Create prompt
        prompt = f"""
You are an AI assistant helping researchers analyze academic papers.
Answer the following question based ONLY on the provided context from research papers.
If the context doesn't contain enough information to answer the question, say so.
Always cite your sources using the reference numbers [1], [2], etc.

Context from research papers:
{context}

Question: {question}

Instructions:
1. Provide a clear, accurate answer based on the context
2. Cite specific sources using [1], [2], etc.
3. If information is insufficient, acknowledge it
4. Be concise but comprehensive

Answer:
"""
        
        answer = self.generate_response(prompt, temperature=0.3)
        
        return {
            "answer": answer,
            "citations": citations,
            "context_used": len(context_chunks)
        }
    
    def extract_key_findings(self, text: str) -> List[str]:
        """Extract key findings from research paper text"""
        prompt = f"""
Analyze the following research paper text and extract the key findings.
List them as bullet points, focusing on the most important discoveries and conclusions.

Text:
{text}

Key Findings (as bullet points):
"""
        response = self.generate_response(prompt, temperature=0.4)
        
        # Parse bullet points
        findings = [line.strip() for line in response.split('\n') if line.strip().startswith(('-', '•', '*'))]
        return findings
    
    def identify_methodology(self, text: str) -> str:
        """Identify and summarize the methodology used in the paper"""
        prompt = f"""
Analyze the following research paper text and describe the methodology used.
Focus on the research methods, techniques, and approaches employed.

Text:
{text}

Methodology Summary:
"""
        return self.generate_response(prompt, temperature=0.4)
    
    def extract_limitations(self, text: str) -> List[str]:
        """Extract limitations mentioned in the paper"""
        prompt = f"""
Analyze the following research paper text and identify any limitations mentioned by the authors.
List them as bullet points.

Text:
{text}

Limitations (as bullet points):
"""
        response = self.generate_response(prompt, temperature=0.4)
        
        # Parse bullet points
        limitations = [line.strip() for line in response.split('\n') if line.strip().startswith(('-', '•', '*'))]
        return limitations

