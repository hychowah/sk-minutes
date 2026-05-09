- Purpose: Archive index and rollover rules for historical development notes
- Scope: How DEVNOTES rollover works, where archived notes live, and how to keep both active and archived devnotes small enough to stay reviewable; excludes live repository status and setup instructions
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: DEVNOTES archival structure and rollover policy

# Devnotes Archive

Use [../DEVNOTES.md](../DEVNOTES.md) first for recent verified repository truth.

Use this page only when older implementation history is needed.

## Rollover Rules

1. Keep [../DEVNOTES.md](../DEVNOTES.md) at or below 500 lines.
2. When adding a verified entry would push `DEVNOTES.md` over 500 lines, move the oldest complete dated entries from the bottom of `DEVNOTES.md` into archive files listed here.
3. Keep each archive file at or below 500 lines as well. Split archives by date or date range before an archive grows past that cap.
4. During rollover, move complete dated entries without rewriting their meaning. Only fix links or obvious factual mistakes when necessary.
5. If the archive structure changes, update [../INDEX.md](../INDEX.md), [README.md](README.md), and [../AGENTS.md](../AGENTS.md) so contributors can still find the owner documents quickly.

## Archive Files

- [archive-2026-05-08.md](archive-2026-05-08.md): verified work log entries archived from 2026-05-08.
- [archive-2026-05-05-to-2026-05-07.md](archive-2026-05-05-to-2026-05-07.md): verified work log entries archived from 2026-05-05 through 2026-05-07.