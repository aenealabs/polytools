---
name: Bug report
about: Something isn't working correctly
labels: bug
---

## Description

A clear description of the bug.

## Reproduction

```python
from polytools import tool
from typing import ...

@tool
def my_func(...):
    ...

# What you called:
my_func.to_openai()  # or to_anthropic(), to_gemini(), to_mcp()

# What you expected:

# What you got:
```

## Environment

- polytools version:
- Python version:
- OS:

## Traceback

```
Paste the full traceback here, if any.
```
