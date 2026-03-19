"""
Embedding service using OpenAI for vector generation
"""
from typing import List, Dict
import openai
from loguru import logger
from config import settings


class EmbeddingService:
    """Generate embeddings using OpenAI API"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.embedding_dimension = 1536  # Default for text-embedding-3-small
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}, size: {len(batch)}")
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Fallback to individual processing
                for text in batch:
                    try:
                        emb = self.generate_embedding(text)
                        embeddings.append(emb)
                    except:
                        logger.error(f"Failed to embed text: {text[:50]}...")
                        embeddings.append([0.0] * self.embedding_dimension)
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def embed_chunks(self, chunks: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Add embeddings to chunk dictionaries
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Chunks with added 'embedding' field
        """
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.generate_embeddings_batch(texts)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        
        return chunks



########################## LANGCHAIN EMBEDDING ######################################
#todo: implement langchain embedding under here
