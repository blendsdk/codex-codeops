# Scenario: generic aliases and incremental compiler

Design requirements for a compiled language feature:

- Add generic type aliases: `type Pair<T> = (T, T)`.
- Aliases may reference aliases declared later in the same module.
- Alias expansion happens before type checking.
- Recursive aliases should work when they are useful, but infinite expansion must be rejected.
- The incremental compiler caches expanded aliases by alias name.
- Diagnostics should be helpful and point at the problem.
- Existing modules compiled before this feature must remain compatible.
- The implementation will lower expanded types into the existing typed IR.

Do not invent missing semantics. Identify material questions that must be resolved before a technical plan is executable.
