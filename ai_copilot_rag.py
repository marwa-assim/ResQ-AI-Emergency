import json
import numpy as np
import os
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("SentenceTransformers not installed yet.")
    SentenceTransformer = None

class ClinicalCopilot:
    def __init__(self, knowledge_base_path="protocols.json"):
        self.kb_path = knowledge_base_path
        self.model = None
        self.protocols = []
        self.embeddings = None
        
        # Load Knowledge Base
        self.load_protocols()
        
        # Initialize Model (Lazy Load)
        if SentenceTransformer:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embed_protocols()
            except Exception as e:
                print(f"Failed to load embedding model: {e}")

    def load_protocols(self):
        if not os.path.exists(self.kb_path):
            # Create default protocols if missing
            self.protocols = [
                {"id": "chest_pain", "text": "Chest Pain Protocol: 1. ECG within 10 mins. 2. Aspirin 325mg if not contraindicated. 3. Nitroglycerin for active pain. 4. Troponin I/T levels.", "title": "Chest Pain / ACS"},
                {"id": "sepsis", "text": "Sepsis Bundle: 1. Measure Lactate. 2. Obtain Blood Cultures before antibiotics. 3. Administer Broad Spectrum Antibiotics. 4. IV Fluids 30ml/kg for hypotension.", "title": "Sepsis"},
                {"id": "stroke", "text": "Stroke Protocol: 1. Head CT (Non-contrast) immediately. 2. Check Glucose. 3. NIHSS Score assessment. 4. tPA evaluation if <4.5 hours onset.", "title": "Acute Stroke"},
                {"id": "asthma", "text": "Asthma/COPD Exacerbation: 1. Nebulized Albuterol/Ipratropium. 2. Corticosteroids (Prednisone/Solu-Medrol). 3. Supplemental Oxygen to maintain SpO2 > 90%.", "title": "Respiratory Distress"},
                {"id": "trauma", "text": "Trauma Protocol: 1. Primary Survey (ABCDE). 2. C-Spine Immobilization. 3. Stop major bleeding (Tourniquet/Pressure). 4. Fast Scan for internal bleeding.", "title": "Trauma / ATLS"}
            ]
            with open(self.kb_path, 'w') as f:
                json.dump(self.protocols, f, indent=2)
        else:
            with open(self.kb_path, 'r') as f:
                self.protocols = json.load(f)

    def embed_protocols(self):
        if self.model and self.protocols:
            texts = [p['text'] for p in self.protocols]
            self.embeddings = self.model.encode(texts, convert_to_tensor=True)

    def get_suggestion(self, query):
        if not self.model or self.embeddings is None:
            return self.keyword_fallback(query)
            
        # Neural Search
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(query_embedding, self.embeddings)[0]
        top_k_idx = np.argmax(scores.cpu().numpy())
        
        best_match = self.protocols[top_k_idx]
        confidence = float(scores[top_k_idx])
        
        if confidence < 0.3:
             return {"title": "General Assessment", "suggestion": "Perform standard triage assessment. No specific protocol matched with high confidence.", "confidence": f"{confidence:.2f}"}
             
        return {
            "title": best_match['title'],
            "suggestion": best_match['text'],
            "confidence": f"{confidence:.2f}"
        }

    def keyword_fallback(self, query):
        # Fallback if model fails
        query = query.lower()
        for p in self.protocols:
            if p['id'] in query or p['title'].lower() in query:
                return {"title": p['title'], "suggestion": p['text'], "confidence": "Keyword Match"}
        return {"title": "General", "suggestion": "Assess vitals.", "confidence": "Low"}

# Singleton
copilot = ClinicalCopilot()
