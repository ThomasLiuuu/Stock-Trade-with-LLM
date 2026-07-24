"""
Sentiment analysis module.
Scores news articles from both sources on a common -1 to +1 scale using VADER.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize VADER once at module level
_vader = SentimentIntensityAnalyzer()


def score_article(headline: str, summary: str = "") -> float:
    """
    Score a single article using VADER.
    Prefers headline (more concise, better for VADER); uses summary as fallback.

    Returns compound score on -1 to +1 scale.
    """
    text = headline if headline else summary
    if not text:
        return 0.0
    return _vader.polarity_scores(text)["compound"]


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Score a list of news articles using VADER on their headlines.

    Returns the same list with an added 'score' field (-1 to +1).
    """
    scored = []
    for article in articles:
        compound = score_article(article.get("headline", ""), article.get("summary", ""))
        scored.append({
            **article,
            "score": compound,
        })
    return scored


def aggregate_sentiment(scored_articles: list[dict]) -> dict:
    """
    Aggregate scored articles into a summary.

    Returns:
        - avg_score:       float  (average sentiment, -1 to +1)
        - bullish_count:   int    (score > 0.05)
        - bearish_count:   int    (score < -0.05)
        - neutral_count:   int
        - total_count:     int
    """
    if not scored_articles:
        return {
            "avg_score": 0.0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "total_count": 0,
        }

    bullish = sum(1 for a in scored_articles if a["score"] > 0.05)
    bearish = sum(1 for a in scored_articles if a["score"] < -0.05)
    neutral = len(scored_articles) - bullish - bearish
    avg_score = sum(a["score"] for a in scored_articles) / len(scored_articles)

    return {
        "avg_score": round(avg_score, 4),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "total_count": len(scored_articles),
    }
