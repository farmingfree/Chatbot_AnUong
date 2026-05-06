"""Text normalization utilities"""
import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalize Vietnamese text for comparison"""
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Remove special characters, keep only alphanumeric and spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity between two texts (0.0 to 1.0)"""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Simple word-based Jaccard similarity
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)
