"""Guardrailed Financial Search Tool — DDGS search restricted to NBFC/finance topics only."""

from duckduckgo_search import DDGS

# Whitelist of finance-related keywords
FINANCE_KEYWORDS = {
    "loan", "emi", "interest", "rate", "credit", "cibil", "score", "bank", "nbfc",
    "mortgage", "personal loan", "home loan", "auto loan", "business loan",
    "rbi", "repo rate", "inflation", "investment", "mutual fund", "fd",
    "fixed deposit", "insurance", "gold loan", "sip", "nifty", "sensex",
    "tax", "gst", "income tax", "hra", "pf", "epf", "nps", "ppf",
    "salary", "aadhaar", "pan", "kyc", "nach", "ecs", "cheque",
    "prepayment", "foreclosure", "balance transfer", "top up loan",
    "debt", "dti", "foir", "eligibility", "sanction", "disburse",
}


def is_finance_query(query: str) -> bool:
    """Check if the query is related to finance/banking."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in FINANCE_KEYWORDS)


def financial_search(query: str, max_results: int = 3) -> str:
    """Search DuckDuckGo ONLY for finance-related queries.
    
    Args:
        query: User's search query.
        max_results: Maximum number of results to return.
        
    Returns:
        Formatted search results or a polite refusal.
    """
    if not is_finance_query(query):
        return (
            "🚫 I can only search for finance and banking related information. "
            "Please ask me about loans, interest rates, credit scores, investments, or similar topics."
        )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{query} India NBFC finance", max_results=max_results))

        if not results:
            return f"No results found for: {query}"

        formatted = []
        for r in results:
            formatted.append(f"**{r['title']}**\n{r['body']}\n🔗 {r['href']}")

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        return f"Search failed: {str(e)}"


if __name__ == "__main__":
    # Test
    print(financial_search("current repo rate India"))
    print("\n---\n")
    print(financial_search("who won cricket match"))  # Should refuse
