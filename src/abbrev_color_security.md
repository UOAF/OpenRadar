# Abbrev Color — UOAF Sheet Loader Security Hardening

This document describes the sanity and security checks applied to the UOAF
signup-sheet loader in [`abbrev_color.py`](./abbrev_color.py) (the **UOAF →
LOAD** feature, which fetches a user-pasted Google Sheets URL and populates
the Abbrev Color table from range `K5:O30`).

Threat model: the URL field accepts arbitrary pasted text, and the fetched
document is attacker-controllable (anyone can send the operator a link).
The loader must therefore treat both the URL and the sheet contents as
untrusted input.

## 1. URL validation (`_sheet_csv_url`)

Applied before any network activity:

| Check | Rejects |
|---|---|
| Control/non-printable characters stripped from the pasted text | Terminal escape / homoglyph trickery in the URL itself |
| Empty input | — (shows "Paste a URL first") |
| Length cap: 2048 characters | Oversized inputs, regex abuse |
| Scheme must be `https` | `javascript:`, `file:`, `data:`, `ftp:`, plain `http:` |
| Hostname must be exactly `docs.google.com` | Arbitrary hosts (SSRF), suffix spoofs such as `docs.google.com.evil.com` |
| Path must match `/spreadsheets/d/<id>` or `/spreadsheets/d/e/<id>` | Non-spreadsheet Google URLs |
| Document ID must match `^[A-Za-z0-9_-]{10,120}$` | Path traversal (`../`), percent-encoded junk, short garbage IDs |
| `gid` must be purely numeric, ≤ 12 digits (otherwise ignored) | Query-string smuggling via the tab ID |

**Request rebuilding:** the outgoing CSV-export URL is constructed from
scratch using only the validated document ID and gid. No part of the pasted
string is ever forwarded to the network request, so there is no query-string,
path, or header injection surface.

## 2. Network fetch (`_fetch_csv_grid`)

| Check | Purpose |
|---|---|
| Redirect allowlist: redirects are only followed to `https` URLs on `docs.google.com`, `*.google.com`, or `*.googleusercontent.com` | Google's export endpoint redirects to `googleusercontent.com`; anything else (open-redirect abuse, downgrade to `http`) aborts with "Blocked a redirect to an untrusted address" |
| 10-second timeout | Hung connections cannot stall the app indefinitely |
| Content-type must be `text/csv` or `text/plain` | A private/nonexistent sheet returns an HTML login or error page; this is rejected with a hint to share the sheet "Anyone with the link" instead of being parsed |
| Download size cap: 2 MB | Memory exhaustion via a huge document |
| Response decoded with `errors="replace"` | Malformed/overlong UTF-8 sequences cannot crash the decoder |

Note: the fetch runs synchronously on the UI thread; the timeout bounds the
worst-case freeze.

## 3. Content validation and sanitization (`_parse_uoaf_grid`)

The parser never executes or evaluates sheet content; cells are only compared
and copied into table fields. In addition:

| Check | Purpose |
|---|---|
| Only the fixed region `K5:O30` is read; rows/columns outside it are never touched | A sheet cannot redirect parsing elsewhere |
| Flight count structurally capped at 15 (3 bands × 5 columns) | Row-flooding the table |
| Callsigns must match `^[A-Za-z]+[A-Za-z0-9-]*$` after whitespace collapse, capped at 24 chars | Strips `<script>`-style content, control characters, Unicode bidi-override tricks; a non-conforming callsign rejects the whole flight |
| Roles reduced to `A-Z 0-9 space / ( ) -`, capped at 24 chars | Same, for the mission field |
| Zero parsed flights leaves the existing table untouched | A junk or wrong document cannot wipe the operator's work |

Parsed values end up in `GameObject.override_name` / imgui text fields only —
both are display-only sinks (no `eval`, no SQL, no shell, and the values are
imgui widget *values*, not widget labels, so `##` ID injection does not apply).

## 4. User feedback

The UOAF window shows a status line under the URL field:

* **Red** — validation rejections ("Only docs.google.com spreadsheet links are
  accepted", "Blocked a redirect to an untrusted address", …), network/HTTP
  failures ("Couldn't load the sheet (HTTP Error 404: Not Found)"), or an
  empty/wrong document ("No occupied flights in K5:O30 - is this the right
  sheet/tab?").
* **Green** — success: "Loaded N flights".

Internal exception details are limited to the short exception message; no
stack traces are rendered to the UI.

## 5. Residual risks / out of scope

* The sheet itself is trusted *content-wise*: whoever can edit the signup
  sheet controls the (sanitized) callsigns and roles that appear in the table.
  That is inherent to the feature.
* TLS certificate validation relies on Python's default `ssl` context and the
  OS trust store.
* A malicious actor who controls `docs.google.com` responses (i.e. Google) is
  out of scope.
