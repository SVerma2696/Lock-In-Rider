# Security Policy

Lock In is a personal desktop app (Pomodoro timer + app blocker). It
runs on your own machine. It only uses the network in these ways:

- The Claude fallback (off by default) sends a single window title
  string and nothing else. See the README's "Claude fallback" section.
- The update check asks GitHub for the latest release. It's on by
  default and runs once, shortly after the app opens, without asking.
  Turn it off in Settings ("Automatically check for updates") — the
  README's "Auto-Update" section has details.
- Revice's buddy link (only while Revice is the picked Rider, and only
  after you press Share or Receive) talks to one other computer on the
  same local network. Either of you can press Pull History at any time
  to send your focus blocks and their tasks to the other side, with no
  extra confirmation, and your computer's name is shown to your buddy
  the whole time you're paired. Pairing uses a 4-digit code that is
  never sent over the network as-is, and it is locked after 3 wrong
  tries. That stops guessing, but a device on the same network that
  answers the pairing call, or watches a pairing happen, can work the
  code out. What's sent after pairing is not encrypted. Only use it on
  a network you trust. See the README's Tier 6 section.

## Supported versions

Only the **latest released version** is supported. This is a small
solo project, not something with a long-term support branch — if a
security issue is found, the fix goes into the next release, not a
backport.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security problem.

Instead, use GitHub's private vulnerability reporting:

1. Go to the **Security** tab on this repository.
2. Click **Report a vulnerability**.
3. Describe the issue — what it is, how to reproduce it, and what it
   affects.

This opens a private conversation that only you and the maintainer can
see, so the issue isn't public until there's a fix.

## What counts as a security issue here

Realistic examples for this project: something that lets a window
title or config value execute unintended code, a way to escalate the
app's blocking/minimize permissions beyond what's documented, or a way
to leak more than the single window-title string the README says the
Claude fallback sends.

General bugs, feature requests, and "the classifier misjudged my
window" are regular GitHub issues, not security reports.
