# Meridian data platform — working rules (abridged)
- Table and column names follow the names in contracts/ and glossary.yaml; ask before proposing a new name.
- A change is at most 300 lines and covers a single topic.
- Do not change a failing test; fix the code. If you think the test is wrong, stop and explain.
- If an existing function does the job, do not write a new one; look in lib/.
- Do not create files, folders or settings nobody asked for.
- Silencing an error (empty except, default value, removed check) is forbidden.
- When done: write what you changed, what you tested and what you could not do.
