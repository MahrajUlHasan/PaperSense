"""
LLM service using Google Gemini API for text generation
"""
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from loguru import logger
from config import settings


class LLMService:
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
    
    def answer_question(self, question: str, context_chunks: List[Dict[str, any]], conversation_history: str = "") -> Dict[str, any]:
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
                table_parts.append(f"{ref} :{chunk['text']}")
            elif content_type == 'image':
                image_parts.append(f"{ref} :{chunk['text']}")
            else:
                text_parts.append(f"{ref} :{chunk['text']}")

            meta = chunk.get('metadata', {})
            citations.append({
                "index": i + 1,
                "section": chunk.get('section', 'unknown'),
                "score": chunk.get('score', 0.0),
                "document_id": chunk.get('document_id', ''),
                "filename": meta.get('filename', ''),
                "text": chunk.get('text', ''),
                "content_type": content_type,
                "page": chunk.get('page') or meta.get('page') or meta.get('page_number'),
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

        #todo: remove logging
        logger.info(f"Context sections:\n{context_sections}")
        # Build optional conversation-history block
        history_block = ""
        if conversation_history:
            history_block = f"""
Previous conversation (use this to understand follow-up questions):
{conversation_history}
---
"""

        # Create prompt
        prompt = f"""
You are an AI assistant helping researchers analyze academic papers.
Identify the questions intent and reformulate a more articulated question if needed.
If there is no relevant contex then use your knowledgebase for answering the question , but put a warning that it is not based on the provided source.
Answer the following question based ONLY on the provided context from research papers.
The context may include regular text excerpts, structured tables, and figure/image captions.
If the context doesn't contain enough information to answer the question, say so.
Always cite your sources using the reference numbers [1], [2], etc.

When the answer involves data from a TABLE, present the relevant data clearly
(you may re-format as a table if it helps readability).

{history_block}
Context from research papers:
{context}

Question: {question}

Instructions:
1. Provide a clear, accurate answer based on the context, do not include thinking process or question reformulation.
2. Cite specific sources using [1], [2], etc.
3. When tables are relevant, reference and summarize the tabular data
4. When figures are relevant, mention them by their captions
5. If information is insufficient, acknowledge it
6. Be concise but comprehensive
7. If the question is a follow-up to the previous conversation, use the conversation history to provide a coherent answer.

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

    # ── Research helpers ──────────────────────────────────────────

    def generate_research_breakdown(self, topic: str, description: str) -> str:
        """
        Generate a detailed breakdown of the research topic that can be
        used later to score uploaded documents for relevance.
        """
        prompt = f"""
You are a research methodology expert. Given the following research topic and
description, produce a **detailed breakdown** that covers:

1. Core research questions
2. Key themes and sub-topics
3. Relevant methodologies and approaches
4. Expected data types and sources
5. Important keywords and phrases
6. Related academic fields and disciplines

Research topic: {topic}
Description: {description}

Provide the breakdown in structured Markdown so it can be used later to
evaluate how relevant a given paper is to this research.

Breakdown:
"""
        return self.generate_response(prompt, temperature=0.4)

    def score_document_relevance(
        self, doc_text: str, filename: str,
        research_topic: str, research_breakdown: str
    ) -> Dict[str, any]:
        """
        Score a document's relevance to the research on a 0-100 scale.

        Returns dict with keys: score (int), explanation (str).
        """
        prompt = f"""
You are an academic research evaluator. Score the following document's
relevance to the given research topic on a scale of 0 to 100.

Research topic: {research_topic}

Research breakdown:
{research_breakdown}

Document filename: {filename}
Document content (excerpt):
{doc_text[:6000]}

Return your response in EXACTLY this format (no other text):
SCORE: <number 0-100>
EXPLANATION: <one paragraph explaining the score>
"""
        response = self.generate_response(prompt, temperature=0.2)

        # Parse score
        score = 50  # default
        explanation = response
        for line in response.strip().split('\n'):
            if line.strip().upper().startswith('SCORE:'):
                try:
                    score = int(''.join(c for c in line.split(':', 1)[1] if c.isdigit())[:3])
                    score = max(0, min(100, score))
                except Exception:
                    pass
            elif line.strip().upper().startswith('EXPLANATION:'):
                explanation = line.split(':', 1)[1].strip()

        return {"score": score, "explanation": explanation}

