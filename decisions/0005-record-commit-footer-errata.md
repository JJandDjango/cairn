# 5. Record commit-footer errata in-repo, don't rewrite pushed history

Status: accepted
Date: 2026-07-13

## Context
Three commits on `main` — `6af1f09`, `0ebd26c`, `e86f47b` — carry an inaccurate
`Claude-Session` footer. They read `.../session_01XBx2WZwXdpEdrCAS769pZz`; the
actual authoring session was `.../session_019CxTne8ZDJaCdLPxbVB9b8` — a wrong id
was written into the first commit message and copied into the next two. The
commits' content and their `Co-Authored-By` lines are correct; only the session
URL is wrong.

## Decision
Leave the history intact and record the correction here rather than rewrite it. An
interactive rebase + force-push of three already-published commits on `main` is
disproportionate for a cosmetic metadata error and would invalidate any existing
clone or reference to those SHAs.

## Consequences
- The `Claude-Session` footer on `6af1f09`, `0ebd26c`, and `e86f47b` is
  **inaccurate**; the authoritative session for all three is
  `https://claude.ai/code/session_019CxTne8ZDJaCdLPxbVB9b8`.
- Any tooling that reads commit footers for provenance should treat this record as
  the correction for those three SHAs.
- Convention reaffirmed: copy the `Claude-Session` footer from the live session,
  never transcribe it from memory.
