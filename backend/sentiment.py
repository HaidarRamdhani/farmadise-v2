from transformers import pipeline
from rapidfuzz import process, fuzz
import re
from sklearn.ensemble import IsolationForest

sentiment_model = pipeline("text-classification", model="w11wo/indonesian-roberta-base-sentiment-classifier")

def normalize_text(text):
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    text = re.sub(r"[^a-zA-Z0-9 ]", "", text)
    return text

def correct_typo(text, vocab, threshold=85):
    corrected_words = []
    for word in text.split():
        match = process.extractOne(word, vocab, scorer=fuzz.partial_ratio)
        corrected_words.append(match[0] if match and match[1] >= threshold else word)
    return " ".join(corrected_words)

def preprocess_text(text):
    vocab = ["sapi", "kerbau", "ayam", "domba", "ternak", "mati", "lemas", "tolong", 
             "sakit", "menggigil", "muntah", "lesu", "kurus", "kenapa", "pingsan", "demam"]
    return correct_typo(normalize_text(text.lower()), vocab)

def rule_based_sentiment(text):
    negative_keywords = ["mati", "sakit", "lemas", "muntah", "menggigil", "kurus", 
                         "kenapa", "tolong", "meninggal", "terkapar", "demam", 
                         "lesu", "pingsan", "tidak mau makan", "drop", "lemes"]
    positive_keywords = ["sehat", "baik", "aman", "damai", "bagus", "stabil", "tidak apaapa"]
    relevant_entities = ["sapi", "kerbau", "ternak", "ayam", "domba", "bebek", 
                         "kambing", "itik", "peternakan", "hewan ternak"]
    unrelated_phrases = ["hari ini panas", "belum makan siang", "tidak ada makanan enak"]
    
    if any(phrase in text for phrase in unrelated_phrases):
        return 0
    if any(phrase in text for phrase in positive_keywords):
        return 0
    if any(entity in text for entity in relevant_entities) and any(word in text for word in negative_keywords):
        return 1
    return None

def classify_sentiment(text):
    preprocessed = preprocess_text(text)
    rule_result = rule_based_sentiment(preprocessed)
    if rule_result is not None:
        return rule_result
    result = sentiment_model(preprocessed)[0]
    return 1 if result['label'] == "NEGATIVE" and result['score'] > 0.15 else 0

def detect_anomalies(data):
    if "sentimen_negatif" not in data.columns:
        data["sentimen_negatif"] = 0
    data = data.dropna(subset=["sentimen_negatif"])
    
    # Inisialisasi model Isolation Forest
    model = IsolationForest(contamination=0.05, random_state=42)
    
    # Deteksi anomali
    data["anomaly"] = model.fit_predict(data[["sentimen_negatif"]])
    data["anomaly"] = data["anomaly"].apply(lambda x: 1 if x == -1 else 0)
    
    return data