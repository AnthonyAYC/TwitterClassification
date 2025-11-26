import re
import unicodedata

# dicionário de normalização de gírias/abreviações
giria_map = {
    "n": "não",
    "nao": "não",
    "vdd": "verdade",
    "pq": "porque",
    "q": "que",
    "tb": "também",
    "td": "tudo",
    "blz": "beleza",
    "tbm": "também",
    "mano": "irmão",
}

def normalize_girias(text):
    words = text.split()
    new_words = []
    for w in words:
        lw = w.lower()
        if lw in giria_map:
            new_words.append(giria_map[lw])
        else:
            new_words.append(w)
    return " ".join(new_words)

def clean_text(text):
    if not text:
        return text

    # remoção de URLs
    text = re.sub(r"http\S+|www\S+", "", text)

    # remoção de hashtags e @menções
    text = re.sub(r"#\S+|@\S+", "", text)

    # remoção de emojis
    emoji_pattern = re.compile(
        "["  
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)

    # normalização de espaços
    text = re.sub(r"\s+", " ", text).strip()

    # normalização de gírias
    text = normalize_girias(text)

    # remoção de acentos (opcional)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

    return text
