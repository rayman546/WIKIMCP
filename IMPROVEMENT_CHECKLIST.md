# Code Improvement Checklist

## Phase 1: Refactoring & Async Handling

-   [ ] **Dependency Injection:**
    -   [ ] Create singleton instances of `WikipediaClient`, `CachingService`, `WikipediaParser` in `main.py`.
    -   [ ] Update `api_routes.py` to use FastAPI's `Depends` with functions that return the singletons (e.g., from `app.state` or a dedicated dependency module).
-   [ ] **Async Operations:**
    -   [ ] Replace `time.sleep` with `asyncio.sleep` in `WikipediaClient._respect_rate_limit`.
    -   [ ] Investigate/implement `run_in_threadpool` for blocking calls in `WikipediaClient` (e.g., `wikipedia.page`, `wikipedia.search`).
    -   [ ] Make `CachingService._load_cache` and `_save_cache` (for `PERSIST`) async using `aiofiles` or similar.
    -   [ ] Remove synchronous `_save_cache` calls from `set`, `delete`, `clear` in `CachingService` (`PERSIST`).
    -   [ ] Ensure `diskcache` usage in `CachingService` is safe for async context or use its async API if available.
    -   [ ] Run `BeautifulSoup` parsing in `WikipediaParser` methods using `run_in_executor`.

## Phase 2: Error Handling & Caching

-   [ ] **Error Handling:**
    -   [ ] Define a specific `DisambiguationAPIError` in `models.py`.
    -   [ ] Update `WikipediaClient` to raise `DisambiguationAPIError` instead of returning a dict.
    -   [ ] Update `WikipediaClient` to catch more specific exceptions from the `wikipedia` library.
    -   [ ] Update `api_routes.py` `get_article` to handle `DisambiguationAPIError`.
    -   [ ] Consider creating middleware for common `try...except APIError...finally` logic in `api_routes.py` (logging, headers).
-   [ ] **Caching:**
    -   [ ] Implement a stable cache key generation function for the `cached` decorator (e.g., using `hashlib` on serialized args/kwargs).
    -   [ ] Refactor `PERSIST` cache: load once at startup, save only on shutdown, consider a more robust serialization format if needed.
    -   [ ] Correct `DISK` cache `size_limit` calculation in `CachingService` (use bytes directly).

## Phase 3: Models, Parsing & Security

-   [ ] **Data Models:**
    -   [ ] Update `models.WikipediaArticle` to include fields extracted by `parser.py` (infobox, tables, citations, etc.).
    -   [ ] Update `models.SearchResult` to match data returned by `WikipediaClient.search` (currently just titles).
-   [ ] **Parser Logic:**
    -   [ ] Review and potentially improve `WikipediaParser._extract_sections` robustness.
    -   [ ] Change parser extraction methods (`_extract_citations`, etc.) to raise specific `ParsingError` on failure instead of returning empty data.
    -   [ ] Update `WikipediaParser.parse_article` to handle potential `ParsingError` from extraction methods.
-   [ ] **Security:**
    -   [ ] Evaluate `RateLimitMiddleware` scalability; consider replacing with Redis-backed limiter if needed for production.
    -   [ ] Rename `RATE_LIMIT` setting or `WikipediaClient` parameter to avoid confusion.

## Phase 4: Utilities, Testing & Final Review

-   [ ] **Utilities:**
    -   [ ] Read and review `src/api_utils.py`.
    -   [ ] Refactor utility functions as needed.
-   [ ] **Testing:**
    -   [ ] Review existing tests in `tests/`.
    -   [ ] Add new tests for refactored code and new error handling.
    -   [ ] Ensure sufficient test coverage.
-   [ ] **Final Review:**
    -   [ ] Check for any remaining TODOs or potential issues.
    -   [ ] Ensure consistency and adherence to best practices.
