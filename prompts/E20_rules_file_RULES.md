# Rules (this file is protected by CODEOWNERS; the AI cannot change it)
- A change is small and covers one topic; each change is explained in one sentence.
- A failing test is not changed; the code is fixed.
- rules.yaml, the tests, the reconcile() tolerance and this file are not changed.
- No files nobody asked for; no copies of an existing function.
- Errors are not silenced; every caught error is logged.
- Permission, delete, cost and core transformation code is reviewed line by line by a human.
- Before saying "done", run the tests and list the changed files.
- An unexplained change is not merged.
