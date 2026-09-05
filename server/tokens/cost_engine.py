"""
Cost Calculation Engine for Token Usage.
Maintains model pricing rates and computes estimated cost in USD.
"""

# Pricing per 1,000,000 tokens (USD)
MODEL_PRICING = {
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
    "gpt-4-turbo": {"prompt": 10.00, "completion": 30.00},
    "gpt-3.5-turbo": {"prompt": 0.50, "completion": 1.50},
    "text-embedding-3-small": {"prompt": 0.02, "completion": 0.00},
    "text-embedding-3-large": {"prompt": 0.13, "completion": 0.00},
    "whisper-1": {"prompt": 0.006, "completion": 0.00},  # Estimated rate
}

DEFAULT_PRICING = {"prompt": 0.15, "completion": 0.60}

def get_model_pricing(model: str) -> dict:
    """
    Find pricing dictionary for a given model string, with prefix matching for snapshots.
    """
    model_lower = model.lower()
    
    # 1. Exact match
    if model_lower in MODEL_PRICING:
        return MODEL_PRICING[model_lower]
        
    # 2. Prefix match (e.g., "gpt-4o-mini-2024-07-18" -> "gpt-4o-mini")
    for key, pricing in MODEL_PRICING.items():
        if model_lower.startswith(key):
            return pricing
            
    return DEFAULT_PRICING

def calculate_token_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate estimated cost in USD based on model and token counts.
    Returns float rounded to 6 decimal places.
    """
    pricing = get_model_pricing(model)
    
    prompt_cost = (prompt_tokens / 1_000_000.0) * pricing["prompt"]
    completion_cost = (completion_tokens / 1_000_000.0) * pricing["completion"]
    
    total_cost = prompt_cost + completion_cost
    return round(total_cost, 6)
