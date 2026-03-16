import os
import json
import logging
import numpy as np
import PyPDF2
from pathlib import Path
from django.conf import settings
from .models import CourseContentChunk, Course

logger = logging.getLogger(__name__)

# Using Google Generative AI for embeddings and generation to avoid massive ML library installations
# Ensure GOOGLE_API_KEY is available in your settings/environment.
try:
    import google.generativeai as genai
    import faiss
except ImportError:
    genai = None
    faiss = None

class EmbeddingService:
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if self.api_key and genai:
            genai.configure(api_key=self.api_key)
        else:
            logger.warning("GOOGLE_API_KEY is not set or google-generativeai is missing.")

    def get_embedding(self, text):
        if not self.api_key or not genai:
            return []
        
        try:
            # gemini-embedding-001 is supported on this key
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type="retrieval_document",
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

class FAISSVectorStore:
    def __init__(self, course_id):
        self.faiss = faiss
        self.course_id = course_id
        # Define a path to store FAISS index on disk persistently
        self.index_path = Path(settings.MEDIA_ROOT) / 'faiss_indexes'
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.file_path = self.index_path / f"course_{course_id}.index"
        
        # gemini-embedding-001 embeddings are 3072 dimensions
        self.vector_dim = 3072 
        
        if self.faiss:
            if self.file_path.exists():
                self.index = self.faiss.read_index(str(self.file_path))
            else:
                self.index = self.faiss.IndexFlatL2(self.vector_dim)

    def add_texts(self, embeddings, chunk_ids):
        if not self.faiss or not embeddings:
            return
        
        vectors = np.array(embeddings).astype('float32')
        ids = np.array(chunk_ids).astype('int64')

        # To store IDs mapping, we need an IndexIDMap wrapper
        if self.file_path.exists():
            id_index = self.faiss.read_index(str(self.file_path))
        else:
            base_index = self.faiss.IndexFlatL2(self.vector_dim)
            id_index = self.faiss.IndexIDMap(base_index)
            
        id_index.add_with_ids(vectors, ids)
        self.faiss.write_index(id_index, str(self.file_path))

    def search(self, query_embedding, k=3):
        if not self.faiss or not self.file_path.exists() or len(query_embedding) == 0:
            return []
        
        try:
            id_index = self.faiss.read_index(str(self.file_path))
            if id_index.ntotal == 0:
                return []

            query_vector = np.array([query_embedding]).astype('float32')
            distances, indices = id_index.search(query_vector, k)
            
            # Retrieve actual chunks from Database using FAISS matched IDs
            matched_ids = indices[0].tolist()
            # Clean out any -1s (if there were fewer vectors than k)
            matched_ids = [idx for idx in matched_ids if idx != -1]
            
            if not matched_ids:
                return []
            
            return CourseContentChunk.objects.filter(id__in=matched_ids)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

class TextExtractor:
    @staticmethod
    def extract_from_pdf(file_path):
        text = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    new_text = page.extract_text()
                    if new_text:
                        text += new_text + "\n"
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
        return text

    @staticmethod
    def chunk_text(text, chunk_size=500):
        # A simple whitespace split based chunking
        words = text.split()
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i:i + chunk_size])

class RAGService:
    def __init__(self, course_id):
        self.course_id = course_id
        self.embedder = EmbeddingService()
        self.vector_store = FAISSVectorStore(course_id)
        
    def generate_answer(self, question):
        # 1. Embed Question
        query_embedding = self.embedder.get_embedding(question)
        
        # 2. Retrieve relevant Documents
        relevant_chunks = self.vector_store.search(query_embedding, k=4)
        context_texts = [chunk.chunk_text for chunk in relevant_chunks]
        context = "\n\n---\n\n".join(context_texts)
        
        if not context:
            context = "No course materials indexed yet. Please inform the student."
            
        # 3. Call LLM
        prompt = f"""You are an AI learning assistant integrated into an LMS course platform. 
        Your goal is to answer the student's question using ONLY the provided course material below.
        If the answer is not found in the materials, explicitly state that you cannot find it in the course. 
        Do not make up facts outside the course scope.
        
        COURSE MATERIALS CONTEXT:
        {context}
        
        STUDENT QUESTION:
        {question}
        
        ANSWER:"""
        
        return self._call_llm(prompt)

    def _call_llm(self, prompt):
        api_key = getattr(settings, 'GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if not api_key or not genai:
            return "The AI Assistant is currently unavilable because the API key is not configured."
            
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return "An internal error occurred while generating the response."
            
    def test_rag_pipeline(self, question):
        # 1. Embed Question
        query_embedding = self.embedder.get_embedding(question)
        if not query_embedding:
            return {"error": "Failed to generate question embedding."}
            
        # 2. Retrieve relevant Documents
        if not self.vector_store.faiss or not self.vector_store.file_path.exists():
            return {"error": "No course materials indexed yet."}
            
        id_index = self.vector_store.faiss.read_index(str(self.vector_store.file_path))
        if id_index.ntotal == 0:
            return {"error": "No course materials indexed yet."}

        # 3. Search restricted to Top 5 chunks (Requirement 9)
        query_vector = np.array([query_embedding]).astype('float32')
        distances, indices = id_index.search(query_vector, 5) 
        
        matched_ids = indices[0].tolist()
        dist_list = distances[0].tolist()
        
        chunk_data = []
        for d, idx in zip(dist_list, matched_ids):
            if idx != -1:
                chunk = CourseContentChunk.objects.filter(id=idx).first()
                if chunk:
                    # Conversion from L2 distance context to a similarity-like visual
                    similarity_score = 1.0 / (1.0 + float(d))
                    chunk_data.append({
                        "id": chunk.id,
                        "text": chunk.chunk_text,
                        "similarity": round(float(similarity_score), 4)
                    })
                    
        if not chunk_data:
            return {"error": "I cannot find that information in the course materials."}
            
        context_texts = [c["text"] for c in chunk_data]
        context = "\n\n---\n\n".join(context_texts)
        
        # 4. Prompt generation
        prompt = f"""You are an AI learning assistant integrated into an LMS course platform. 
Your goal is to answer the student's question using ONLY the provided course material below.
If the answer is not found in the materials, explicitly state:
"I cannot find that information in the course materials."
Do not make up facts outside the course scope.

COURSE MATERIALS CONTEXT:
{context}

STUDENT QUESTION:
{question}

ANSWER:"""

        response_text = self._call_llm(prompt)
        
        return {
            "retrieved_chunks": chunk_data,
            "prompt": prompt,
            "ai_response": response_text
        }

    def process_course_material(self, text, metadata=None):
        """Processes raw text from a lecture/PDF, stores in DB, embeds, and saves to FAISS."""
        if metadata is None:
            metadata = {}
            
        chunks = list(TextExtractor.chunk_text(text))
        embeddings = []
        chunk_ids = []
        
        for chunk in chunks:
            embedding = self.embedder.get_embedding(chunk)
            if embedding:
                db_chunk = CourseContentChunk.objects.create(
                    course_id=self.course_id,
                    chunk_text=chunk,
                    embedding=embedding,
                    metadata=metadata
                )
                embeddings.append(embedding)
                chunk_ids.append(db_chunk.id)
                
        if embeddings:
            self.vector_store.add_texts(embeddings, chunk_ids)
            return len(embeddings)
        return 0
