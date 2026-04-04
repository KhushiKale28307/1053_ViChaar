import numpy as np


# -----------------------------
# Utility: Remove Outliers
# -----------------------------
def remove_outliers_with_sources(prices, sources):
    """
    Removes extreme price values using median-based filtering.
    Keeps prices within 50% to 150% of median.
    """
    median = np.median(prices)
    lower = 0.5 * median
    upper = 1.5 * median

    filtered_pairs = [
        (p, s) for p, s in zip(prices, sources)
        if lower <= p <= upper
    ]

    filtered_prices = [p for p, _ in filtered_pairs]
    filtered_sources = [s for _, s in filtered_pairs]

    return filtered_prices, filtered_sources


# -----------------------------
# Assign weights based on source reliability
# -----------------------------
def compute_weights(sources, source_weights):
    return [source_weights.get(s, 0.5) for s in sources]


# -----------------------------
# Weighted average calculation
# -----------------------------
def weighted_mean(prices, weights):
    return sum(p * w for p, w in zip(prices, weights)) / sum(weights)


# -----------------------------
# Confidence estimation
# -----------------------------
def compute_confidence(prices, weighted_mean_val, std_dev):
    """
    Confidence depends on variation in prices.
    Lower variation → higher confidence
    """
    if len(prices) < 3:
        return "low"

    variation = std_dev / weighted_mean_val

    if variation > 0.25:
        return "low"
    elif variation > 0.15:
        return "medium"
    else:
        return "high"


# -----------------------------
# Market Price Estimation
# -----------------------------
def market_price_estimation(prices, sources):
    if len(prices) != len(sources):
        raise ValueError("Prices and sources must have same length")

    # Step 1: Clean data
    filtered_prices, filtered_sources = remove_outliers_with_sources(prices, sources)

    # Handle edge cases
    if len(filtered_prices) == 0:
        return {"error": "All prices removed as outliers", "confidence": "low"}

    if len(filtered_prices) < 2:
        fallback_price = np.mean(prices)
        return {
            "market_price": round(fallback_price, 2),
            "confidence": "low",
            "note": "Fallback to average due to insufficient clean data"
        }

    # Step 2: Source reliability
    source_weights = {
        "amazon": 1.0,
        "flipkart": 0.9,
        "robu": 0.95,
        "industry_site": 1.0,
        "unknown": 0.5
    }

    weights = compute_weights(filtered_sources, source_weights)

    # Step 3: Weighted mean
    w_mean = weighted_mean(filtered_prices, weights)

    # Step 4: Statistics
    min_price = min(filtered_prices)
    max_price = max(filtered_prices)
    median_price = np.median(filtered_prices)
    std_dev = np.std(filtered_prices)

    # Step 5: Market range
    market_range = [
        round(w_mean - std_dev, 2),
        round(w_mean + std_dev, 2)
    ]

    # Step 6: Confidence
    confidence = compute_confidence(filtered_prices, w_mean, std_dev)

    return {
        "min_price": min_price,
        "max_price": max_price,
        "median_price": median_price,
        "weighted_mean": round(w_mean, 2),
        "std_dev": round(std_dev, 2),
        "market_range": market_range,
        "confidence": confidence
    }


# -----------------------------
# Pricing Decision Engine
# -----------------------------
def pricing_decision_engine(market, cost, desired_margin):
    """
    Decides pricing strategy based on market and cost
    """

    if "error" in market:
        return {
            "recommended_price": None,
            "strategy": "insufficient_data",
            "risk": "high",
            "reasoning": ["Market data insufficient"]
        }

    market_min = market["min_price"]
    market_max = market["max_price"]
    market_median = market["median_price"]
    confidence = market["confidence"]

    min_viable_price = cost * (1 + desired_margin)

    # CASE 1: Cannot compete
    if min_viable_price > market_max:
        return {
            "recommended_price": None,
            "strategy": "reject_or_differentiate",
            "risk": "high",
            "min_viable_price": round(min_viable_price, 2),
            "reasoning": [
                "Cost is higher than market",
                "Try adding value or skip bidding"
            ]
        }

    # CASE 2: Strong advantage
    elif min_viable_price < market_min:
        recommended_price = market_median
        expected_margin = (recommended_price - cost) / cost

        return {
            "recommended_price": round(recommended_price, 2),
            "strategy": "profit_maximization",
            "expected_margin": round(expected_margin, 2),
            "min_viable_price": round(min_viable_price, 2),
            "risk": "low" if confidence == "high" else "medium",
            "reasoning": ["Cost is much lower → maximize profit"]
        }

    # CASE 3: Competitive zone
    else:
        recommended_price = min(market_median, market_max * 0.98)
        expected_margin = (recommended_price - cost) / cost

        return {
            "recommended_price": round(recommended_price, 2),
            "strategy": "competitive_pricing",
            "expected_margin": round(expected_margin, 2),
            "min_viable_price": round(min_viable_price, 2),
            "risk": "medium" if confidence == "medium" else "low",
            "reasoning": ["Within market → stay competitive"]
        }


# -----------------------------
# User Input Handling
# -----------------------------
def get_user_input():
    print("\nEnter prices (comma-separated):")
    prices = list(map(float, input().split(",")))

    print("\nEnter corresponding sources (comma-separated):")
    sources = input().split(",")

    if len(prices) != len(sources):
        raise ValueError("Prices and sources must match")

    print("\nEnter your cost price:")
    cost = float(input())

    print("\nEnter desired margin (e.g., 0.15 for 15%):")
    margin = float(input())

    return prices, sources, cost, margin


# -----------------------------
# Main Execution
# -----------------------------
if __name__ == "__main__":
    try:
        prices, sources, cost, margin = get_user_input()

        print("\n--- Market Analysis ---")
        market = market_price_estimation(prices, sources)
        for k, v in market.items():
            print(f"{k}: {v}")

        print("\n--- Pricing Decision ---")
        decision = pricing_decision_engine(market, cost, margin)
        for k, v in decision.items():
            print(f"{k}: {v}")

    except Exception as e:
        print("Error:", e)