"""Print required environment variable names for deployment"""

required = {
    "frontend": ["BASE_URL", "API_TIMEOUT", "LOG_LEVEL"],
    "backend": [
        "GROQ_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "EXCHANGE_RATE_API_KEY",
        "OPENWEATHERMAP_API_KEY",
        "GOOGLE_PLACES_API_KEY",
        "OPENAI_API_KEY",
        "GRAPHQL_API_KEY",
        "GOOGLE_API_KEY",
        "FOURSQUARE_API_KEY",
        "TAVILY_API_KEY",
    ],
}

if __name__ == "__main__":
    print("Frontend env vars:")
    for k in required["frontend"]:
        print(f"- {k}")
    print("\nBackend env vars (set in backend service only):")
    for k in required["backend"]:
        print(f"- {k}")
