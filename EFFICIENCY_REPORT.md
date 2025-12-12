# OpenHands Efficiency Improvement Report

This report identifies several areas in the OpenHands codebase where efficiency could be improved.

## 1. Redundant `task.result()` Calls in `wait_all` Function

**File:** `openhands/utils/async_utils.py` (lines 82-93)

**Issue:** The `wait_all` function calls `task.result()` twice for each successful task - once during error checking and again in the final return statement.

**Current Code:**
```python
results = []
errors = []
for task in tasks:
    try:
        results.append(task.result())
    except Exception as e:
        errors.append(e)
if errors:
    if len(errors) == 1:
        raise errors[0]
    raise AsyncException(errors)
return [task.result() for task in tasks]  # Redundant call!
```

**Impact:** For N successful tasks, this makes 2N calls to `task.result()` instead of N.

**Recommended Fix:** Return the already-collected `results` list instead of calling `task.result()` again.

---

## 2. Repeated String Splitting in StuckDetector

**File:** `openhands/controller/stuck.py` (lines 186-227)

**Issue:** In `_check_for_consistent_invalid_syntax`, the code calls `obs.content.strip().split('\n')` and then later accesses `obs.content.strip().split('\n')[:-2][-1]` for the same observations, performing redundant string operations.

**Current Code:**
```python
for obs in observations:
    content = obs.content
    lines = content.strip().split('\n')
    # ... later ...
    set(obs.content.strip().split('\n')[:-2][-1] for obs in valid_observations)
```

**Impact:** String splitting is O(n) where n is the string length. Doing it multiple times for the same content wastes CPU cycles.

**Recommended Fix:** Cache the split result and reuse it.

---

## 3. Repeated Example Generation in Function Call Converter

**File:** `openhands/llm/fn_call_converter.py` (lines 746-760)

**Issue:** The function `IN_CONTEXT_LEARNING_EXAMPLE_PREFIX(tools)` (which is `get_example_for_tools`) is called multiple times with the same `tools` argument within `convert_non_fncall_messages_to_fncall_messages`.

**Current Code:**
```python
if content.startswith(IN_CONTEXT_LEARNING_EXAMPLE_PREFIX(tools)):
    content = content.replace(IN_CONTEXT_LEARNING_EXAMPLE_PREFIX(tools), '', 1)
# ... and again for list content ...
example = IN_CONTEXT_LEARNING_EXAMPLE_PREFIX(tools)
```

**Impact:** `get_example_for_tools` iterates through all tools and builds a large example string. Calling it multiple times with the same tools is wasteful.

**Recommended Fix:** Cache the example string at the start of the function and reuse it.

---

## 4. List-based Model Name Lookups

**File:** `openhands/llm/llm.py` (lines 50-103)

**Issue:** Model name lookups use lists with the `in` operator, which is O(n). These lookups happen frequently during LLM operations.

**Current Code:**
```python
CACHE_PROMPT_SUPPORTED_MODELS = [
    'claude-3-7-sonnet-20250219',
    # ... many more ...
]

# Used as:
if self.config.model in CACHE_PROMPT_SUPPORTED_MODELS:
```

**Impact:** O(n) lookup for each check instead of O(1).

**Recommended Fix:** Convert these lists to sets for O(1) membership testing.

---

## 5. Unnecessary Deep Copies in LLM Wrapper

**File:** `openhands/llm/llm.py` (lines 238, 311)

**Issue:** The LLM wrapper makes deep copies of messages and responses even when mock function calling is not active.

**Current Code:**
```python
original_fncall_messages = copy.deepcopy(messages)  # Always copied
# ... later ...
non_fncall_response = copy.deepcopy(resp)  # Always copied
```

**Impact:** Deep copying large message lists and responses is expensive. These copies are only needed when mock function calling is active.

**Recommended Fix:** Only perform deep copies when `mock_function_calling` is True.

---

## Summary

| Issue | File | Estimated Impact | Complexity to Fix |
|-------|------|------------------|-------------------|
| Redundant task.result() | async_utils.py | Medium | Low |
| Repeated string splitting | stuck.py | Low | Low |
| Repeated example generation | fn_call_converter.py | Medium | Low |
| List-based lookups | llm.py | Low | Low |
| Unnecessary deep copies | llm.py | High | Medium |

## Recommendation

The fix for Issue #1 (redundant `task.result()` calls) provides a good balance of impact and simplicity. It's a clear bug/inefficiency that can be fixed with a one-line change and improves the performance of all async operations using `wait_all`.
