# Cooper — Known Patterns

## Learned from past debugging sessions

---

## Pattern: HAVING COUNT(s.id) > 10 filters out noise

The hot_deploy voyage uses HAVING COUNT(s.id) > 10. This is intentional —
deploys with fewer than 10 new errors are likely pre-existing noise, not regressions.
Do not lower this threshold without measuring the false positive rate.

## Pattern: local_codebase.symbols may lag behind git HEAD by ~60 seconds

The local-codebase Coral source re-indexes on a 60-second watchdog cycle.
If a symbol query returns no results for a very recent file, wait 60s and retry.

## Pattern: touched_symbols from window functions can include test files

The `array_agg(DISTINCT sym.name)` in V1 includes symbols from test files if the
PR changed them. Always filter `sym.file NOT LIKE '%test%' AND sym.file NOT LIKE
'%spec%'` when looking for production symbols.
