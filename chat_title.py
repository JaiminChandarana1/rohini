from keybert import KeyBERT

kw_model = KeyBERT()

def generate_semantic_title(message,id=None):
    if id is not None:
        keywords = kw_model.extract_keywords(message, keyphrase_ngram_range=(1, 3), stop_words='english', top_n=1)
        title = ' '.join([kw[0].title() for kw in keywords])
        return title 