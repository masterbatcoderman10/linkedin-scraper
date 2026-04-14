# LinkedIn Scraper — Analysis

## What the wiki proposes
Automated LinkedIn profile scraper using a stealth Firefox browser (camoufox) injected with the user's live `li_at` session cookie from their Firefox profile. Takes profile URLs → outputs markdown. Supports parallel execution.

Architecture: browser-first discovery of the API surface, then API replay via extracted session cookies.

## What the environment has
- **camoufox** 0.4.11 — stealth Firefox automation (macOS Python package)
- **playwright** 1.58.0 — browser automation
- **selenium** 4.36.0 — legacy browser automation
- **Firefox profile** `6rd2ksu0.default-release` — active, has `li_at` (152-char session cookie), `JSESSIONID`, `li_theme`, `lidc`, `bscookie`, etc.

## Key auth artifacts found
- `li_at` — 152-char session token (primary auth)
- `JSESSIONID` — 26-char servlet session
- `li_theme` / `li_theme_set` — UI state
- `lidc` — 108-char datacenter cookie
- `bscookie` — 88-char secure cookie
- `liap` — 4-char (likely "liap" = LinkedIn Analytics Platform flag)

## Open questions (interview needed)
1. **Read scope**: Are you scraping publicly-visible profiles only, or do you need authenticated-only content (connection requests, InMail, private flags, recruiter-view data)?
2. **Profile URL pattern**: Do you have a list of URLs ready, or do you also need search/discovery built in?
3. **Markdown schema**: What fields do you want in the output? (Name, headline, about, experience, education, skills, connections count, etc. — all of these or a subset?)
4. **Parallelism**: How many profiles at once? LinkedIn rate-limits aggressively — what's your tolerance for throttling/bans?
5. **Session lifetime**: `li_at` can expire. Should the scraper auto-refresh or just fail with a clear error?
6. **Output**: Save to files? Return as JSON/string? Both?
7. **CLI interface**: Just a script? A proper CLI with subcommands? `linkedin-scrape url1 url2 ...` vs `linkedin scrape --input urls.txt`?
8. **Error handling**: Skip bad URLs? Save failures to a separate log? Continue on error?
