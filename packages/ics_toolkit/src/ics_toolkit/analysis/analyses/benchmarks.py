"""Industry benchmarks and traffic-light thresholds for ICS analysis."""

# Average interchange rate for debit card transactions (Durbin-regulated)
INTERCHANGE_RATE = 0.0182

# Traffic-light thresholds: (green_min, yellow_min)
# Values >= green_min are green, >= yellow_min are yellow, below are red.
THRESHOLDS = {
    "activation_rate": (60.0, 40.0),
    "active_rate": (50.0, 30.0),
    "penetration_rate": (70.0, 50.0),
}


def traffic_light(value: float, metric: str) -> str:
    """Return 'green', 'yellow', or 'red' for a metric value."""
    if metric not in THRESHOLDS:
        return "gray"
    green_min, yellow_min = THRESHOLDS[metric]
    if value >= green_min:
        return "green"
    if value >= yellow_min:
        return "yellow"
    return "red"
