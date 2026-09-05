# Python Imports

All imports MUST be at module level (top of file). Never inside function bodies.

```python
# BAD
def get_data():
    from tuttle.app.core.formatting import fmt_currency
    return fmt_currency(value, "EUR")

# GOOD
from tuttle.app.core.formatting import fmt_currency

def get_data():
    return fmt_currency(value, "EUR")
```

Applies to all `.py` files.
