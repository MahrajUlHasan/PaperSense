"""
LLM service using Google Gemini API for text generation
Updated to use the latest google.genai library
"""
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from loguru import logger
from config import settings


class LLMService:
    """Google Gemini LLM service for generation using google.genai"""

    def __init__(self):
        # Initialize the Gemini client with API key
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model_name = settings.gemini_model

        # Default generation configuration
        self.default_config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
            response_modalities=["TEXT"],
        )

    def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate response from Gemini

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0 to 2.0)

        Returns:
            Generated text response
        """
        try:
            # Create generation config with custom temperature
            config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
                response_modalities=["TEXT"],
            )

            # Generate content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Extract text from response
            if response.text:
                return response.text
            else:
                logger.warning("Empty response from Gemini")
                return "No response generated"

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return f"Error generating response: {str(e)}"
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Generate a summary of the given text (may include tables/figures)"""
        prompt = f"""
Please provide a concise summary of the following research paper content.
The content may include regular text, structured tables, and figure/image captions.
Focus on the key findings, methodology, and conclusions.
If tables are present, incorporate their key data points into the summary.
If figures are mentioned, reference their significance.
Keep the summary under {max_length} words.

Content:
{text}

Summary:
"""
        return self.generate_response(prompt, temperature=0.5)
    
    def answer_question(self, question: str, context_chunks: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Answer a question based on retrieved context chunks.

        Handles three content types returned by the vector store:
          - text   → regular paper prose
          - table  → structured table data (markdown / HTML)
          - image  → figure captions (base64 available in payload)

        Args:
            question: User's question
            context_chunks: Retrieved relevant chunks from vector store

        Returns:
            Dictionary with answer and citations
        """
        # Separate chunks by content type for clearer prompting
        text_parts = []
        table_parts = []
        image_parts = []
        citations = []

        for i, chunk in enumerate(context_chunks):
            ref = f"[{i+1}]"
            content_type = chunk.get('content_type', 'text')

            if content_type == 'table':
                table_parts.append(f"{ref} {chunk['text']}")
            elif content_type == 'image':
                image_parts.append(f"{ref} {chunk['text']}")
            else:
                text_parts.append(f"{ref} {chunk['text']}")

            citations.append({
                "index": i + 1,
                "section": chunk.get('section', 'unknown'),
                "score": chunk.get('score', 0.0),
                "document_id": chunk.get('document_id', ''),
                "content_type": content_type,
            })

        # Assemble context sections
        context_sections = []
        if text_parts:
            context_sections.append("TEXT EXCERPTS:\n" + "\n\n".join(text_parts))
        if table_parts:
            context_sections.append("TABLES:\n" + "\n\n".join(table_parts))
        if image_parts:
            context_sections.append("FIGURES/IMAGES:\n" + "\n\n".join(image_parts))

        context = "\n\n---\n\n".join(context_sections)

        # Create prompt
        prompt = f"""
You are an AI assistant helping researchers analyze academic papers.
Answer the following question based ONLY on the provided context from research papers.
The context may include regular text excerpts, structured tables, and figure/image captions.
If the context doesn't contain enough information to answer the question, say so.
Always cite your sources using the reference numbers [1], [2], etc.

When the answer involves data from a TABLE, present the relevant data clearly
(you may re-format as a table if it helps readability).

Context from research papers:
{context}

Question: {question}

Instructions:
1. Provide a clear, accurate answer based on the context
2. Cite specific sources using [1], [2], etc.
3. When tables are relevant, reference and summarize the tabular data
4. When figures are relevant, mention them by their captions
5. If information is insufficient, acknowledge it
6. Be concise but comprehensive

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

