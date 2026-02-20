"""V4 Storyline modules for transaction analysis.

These modules are called via thin adapters in analyses/storyline_adapters.py.
The adapters import each module directly (lazy), so this __init__ only
documents which modules are actively used.

Active modules (called by ANALYSIS_REGISTRY):
    S5  Demographics & Branch   -> analyze_demographics adapter
    S7  Campaign Effectiveness  -> analyze_campaigns adapter
    S8  Payroll & Circular Economy -> analyze_payroll adapter
    S9  Lifecycle Management    -> analyze_lifecycle adapter
"""
