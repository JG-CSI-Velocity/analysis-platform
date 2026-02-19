"""Run this on Windows to verify spine-stripping code is loaded."""
import inspect
from ars_analysis.mailer_common import save_chart

# Check if save_chart has our spine-stripping code
source = inspect.getsource(save_chart)
if "spine.set_visible(False)" in source:
    print("PASS: save_chart has spine stripping")
    print(source)
else:
    print("FAIL: save_chart is MISSING spine stripping!")
    print("You need to run: git pull origin main && uv sync")
    print()
    print("Current source:")
    print(source)
