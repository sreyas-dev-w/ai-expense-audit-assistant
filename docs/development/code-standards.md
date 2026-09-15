# Code Standards

## Code Quality

Prefer code that is:

- typed
- explicit
- small and composable
- easy to test
- easy to reason about
- appropriately documented
- consistent with existing project conventions

Avoid:

- unnecessary abstractions
- premature generic frameworks
- duplicated business logic
- giant agent functions
- giant route handlers
- hidden global state
- magic constants
- untyped agent communication

Do not introduce an abstraction merely because it is theoretically reusable.

## Python Style

Use modern Python typing:

```python
def get_claim(claim_id: UUID) -> ExpenseClaim | None:
    ...
```

over outdated typing patterns where the newer syntax is supported by the project's Python version.

Use type hints for:

- function arguments
- return values
- important variables
- agent state
- Pydantic models
- service interfaces

Keep functions focused on one responsibility.

## Dependencies

Keep dependencies intentional. Before introducing a new package:

1. Check whether an existing dependency already provides the required capability.
2. Check whether the functionality belongs in the standard library.
3. Consider maintenance and security implications.
4. Avoid adding a dependency for trivial functionality.

Do not introduce another ORM, agent framework, vector database, or database driver without an explicit
architectural decision.

## Documentation

Keep architectural documentation concise and useful. Document decisions that affect:

- agent workflow
- data contracts
- database architecture
- RAG architecture
- tool capabilities
- external integrations
- important tradeoffs

Avoid documenting obvious implementation details that can be understood directly from the code.

## Working With Existing Code

Before changing an existing implementation:

1. Inspect the relevant code.
2. Understand the existing architecture.
3. Identify existing schemas and contracts.
4. Reuse existing abstractions where appropriate.
5. Avoid unrelated refactoring.
6. Make the smallest coherent change required.

Do not rewrite working sections merely to match a preferred personal coding style. Consistency with the existing
project is generally more valuable than introducing a theoretically cleaner pattern in isolation.