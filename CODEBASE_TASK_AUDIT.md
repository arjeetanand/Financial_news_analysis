# Codebase Issue Audit and Suggested Tasks

## 1) Typo fix task
**Issue found:** The heading in `about.html` says **"About Me"** even though the page title and navigation label are **"About Us"**, which is inconsistent copy and likely a typo in page labeling.

**Proposed task:** Update the section heading text from `About Me` to `About Us` for consistent wording across the UI.

**Why this matters:** Small wording inconsistencies reduce polish and can confuse users about whether the page is personal profile content or broader project/about content.

**Acceptance criteria:**
- The heading in `templates/about.html` matches the page title wording (`About Us`).
- Navigation label and page heading use consistent terminology.

## 2) Bug fix task
**Issue found:** `CustomJSONEncoder` checks `isinstance(obj, np.float)`, but `np.float` is removed/deprecated in modern NumPy versions and can raise runtime errors.

**Proposed task:** Replace deprecated NumPy scalar checks with safe, supported checks (`np.floating` and/or `numbers.Real`) and keep NaN serialization behavior intact.

**Why this matters:** This can break JSON serialization paths and cause failures in API responses under newer NumPy versions.

**Acceptance criteria:**
- `app.py` no longer references `np.float`.
- JSON serialization still converts NaN-like numeric values to `null`.
- `/stock_details/<symbol>` response serialization remains valid for numeric and date fields.

## 3) Comment/documentation discrepancy task
**Issue found:** README route documentation lists `/stock_details/` as a route, but Flask defines `/stock_details/<symbol>`, requiring a path parameter.

**Proposed task:** Correct route documentation in `README.md` to show `/stock_details/<symbol>` and add a concrete example (e.g., `/stock_details/TCS`).

**Why this matters:** Incorrect route docs lead to failed API calls and developer confusion.

**Acceptance criteria:**
- README route section documents parameterized path correctly.
- README includes one working example request path with a symbol.

## 4) Test improvement task
**Issue found:** The repository currently has no automated tests for core behavior (routes, filtering, JSON serialization edge cases).

**Proposed task:** Add a minimal Flask test suite using `pytest` covering:
1. `GET /search_stocks?q=<query>` returns a JSON list and handles empty query.
2. `GET /stock_details/<symbol>` returns JSON with HTTP 200 for known symbol and empty list for unknown symbol.
3. JSON serialization safely handles NumPy/Pandas NaN values.

**Why this matters:** These are high-traffic paths and currently unguarded from regressions.

**Acceptance criteria:**
- New tests run via `pytest` and pass locally.
- Tests include at least one NaN serialization edge case.
- Basic route contract is asserted (status code + response shape).
