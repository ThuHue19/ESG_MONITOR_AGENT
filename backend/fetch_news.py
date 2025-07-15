import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

def fetch_news(query: str, limit: int = 10) -> List[Dict]:
    """
    Truy vấn bài báo liên quan đến query từ NewsAPI
    """
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={query}&language=en&pageSize={limit}&sortBy=relevancy&apiKey={NEWSAPI_KEY}"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        if not articles:
            return []
        return [
            {
                "title": article["title"],
                "url": article["url"],
                "source": article["source"]["name"],
                "content": article.get("content") or article.get("description", ""),
                "publishedAt": article.get("publishedAt")
            }
            for article in articles
        ]
    except requests.RequestException as e:
        print(f"⚠️ News fetch failed for query '{query}': {e}")
        return []