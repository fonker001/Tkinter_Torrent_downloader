# src/core/semantic_search.py
import numpy as np
import pickle
import os
from datetime import datetime, timedelta

class YTSSemanticSearch:
    def __init__(self, cache_dir=".semantic_cache", model_name="all-MiniLM-L6-v2"):
        self.cache_dir = cache_dir
        self.model_name = model_name
        self.model = None
        self.movie_embeddings = {}  # {movie_id: embedding_vector}
        self.movie_data = {}        # {movie_id: movie_dict}
        self.initialized = False
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Try to load model
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading semantic search model...")
            self.model = SentenceTransformer(self.model_name)
            self.initialized = True
            print("✅ Semantic search model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load semantic model: {e}")
            self.model = None
            self.initialized = False
    
    def is_ready(self):
        """Check if model is ready for use"""
        return self.initialized and self.model is not None
    
    def update_with_movies(self, movies_list):
        """Update search index with movies - THIS IS THE CRITICAL FIX"""
        if not self.is_ready():
            print("⚠️ Semantic search not ready yet, skipping update")
            return
        
        if not movies_list:
            print("⚠️ No movies to update")
            return
        
        print(f"📥 Updating semantic index with {len(movies_list)} movies")
        
        new_movies_added = 0
        for movie in movies_list:
            movie_id = movie.get('id')
            if not movie_id or movie_id in self.movie_embeddings:
                continue  # Skip if no ID or already processed
            
            # Store movie data
            self.movie_data[movie_id] = movie
            
            # Create searchable text
            search_text = self._create_search_text(movie)
            
            try:
                # Create embedding for this movie
                embedding = self.model.encode(search_text)
                self.movie_embeddings[movie_id] = embedding
                new_movies_added += 1
            except Exception as e:
                print(f"⚠️ Failed to create embedding for movie {movie_id}: {e}")
        
        print(f"✅ Semantic index updated. Total movies indexed: {len(self.movie_embeddings)} (Added {new_movies_added} new)")
    
    def _create_search_text(self, movie):
        """Create rich text for semantic search from movie data"""
        parts = []
        
        # Title (most important - repeat for emphasis)
        title = movie.get('title', '')
        if title:
            parts.append(title)
            parts.append(title)  # Add twice for emphasis
        
        # Plot/summary/description
        if movie.get('description_full'):
            parts.append(movie['description_full'][:500])  # Limit length
        elif movie.get('summary'):
            parts.append(movie['summary'])
        
        # Genres as keywords
        if movie.get('genres'):
            # Add each genre separately
            for genre in movie['genres']:
                parts.append(genre)
            # Also add as a joined string
            parts.append(' '.join(movie['genres']))
        
        # Cast (if available)
        if movie.get('cast'):
            cast_names = [actor.get('name', '') for actor in movie['cast'][:3]]
            parts.append(' '.join(cast_names))
        
        # Year and rating as context
        if movie.get('year'):
            parts.append(f"released in {movie['year']}")
        
        if movie.get('rating'):
            parts.append(f"rating {movie['rating']}")
        
        # Join all parts with spaces
        return ' '.join(parts)
    
    def search_by_description(self, query, top_n=10, min_similarity=0.25):
        """Search movies by natural language description"""
        if not self.is_ready():
            print("⚠️ Semantic search not ready")
            return []
        
        if not self.movie_embeddings:
            print("⚠️ No movies indexed for semantic search")
            return []
        
        print(f"🔍 Semantic search for: '{query}'")
        
        try:
            # Encode the query
            query_embedding = self.model.encode(query)
            
            # Calculate similarities with all indexed movies
            results = []
            for movie_id, movie_embedding in self.movie_embeddings.items():
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, movie_embedding)
                
                if similarity >= min_similarity:
                    movie_data = self.movie_data.get(movie_id, {})
                    results.append({
                        'movie_id': movie_id,
                        'similarity_score': float(similarity),
                        'movie': movie_data
                    })
            
            # Sort by similarity (highest first)
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Return top N results
            top_results = results[:top_n]
            
            print(f"✅ Found {len(top_results)} movies with similarity >= {min_similarity}")
            
            # Return list of movies with similarity scores
            return [{
                'movie': result['movie'],
                'similarity_score': result['similarity_score']
            } for result in top_results]
            
        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)
    
    def get_movie_by_id(self, movie_id):
        """Get movie data by ID"""
        return self.movie_data.get(movie_id)
    
    def clear_cache(self):
        """Clear search cache"""
        self.movie_embeddings.clear()
        self.movie_data.clear()
        print("🗑️ Semantic cache cleared")
    
    def get_stats(self):
        """Get statistics about indexed movies"""
        return {
            'total_movies': len(self.movie_embeddings),
            'ready': self.is_ready(),
            'model': self.model_name
        }