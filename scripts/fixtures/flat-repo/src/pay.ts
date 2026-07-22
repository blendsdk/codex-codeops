// Minimal source file in the flat-repo fixture.
//
// It lives OUTSIDE the planning tree (plans/ + requirements/), so migration never moves it.
// A plan doc links here with a source-relative path; after migration that link must be
// surfaced as a warning (it points out of the moved tree), never silently rewritten.
export function pay(amountCents: number): { ok: boolean } {
  return { ok: amountCents > 0 };
}
