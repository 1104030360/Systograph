# GitHub Codex Code Review Setup

This document tracks how KAI-Mind should use Codex with GitHub pull requests.

## Recommended Path

Use official Codex GitHub code review first. Add a custom GitHub Action later only if the team needs more control.

## Setup Checklist

1. Enable Codex Cloud for this repository.
2. Go to Codex settings.
3. Turn on Code review for this repository.
4. Turn on Automatic reviews if every PR should be reviewed automatically.
5. Add repository review guidance in `AGENTS.md`.
6. Keep human review required. Codex is an additional reviewer, not a replacement.

## Manual Review Trigger

In a pull request comment:

```text
@codex review
```

Focused examples:

```text
@codex review for security regressions, missing tests, and risky behavior changes.
@codex review for scanner safety and accidental secret exposure.
@codex review for CI gate behavior and JSON schema compatibility.
```

## Automatic Reviews

When automatic reviews are enabled in Codex settings, Codex can review PRs when they are opened or marked ready for review. This is useful once the team has a steady PR flow.

## Repository Guidance

The root `AGENTS.md` should tell Codex what matters in this project:

- Scanner behavior must be read-only by default.
- Do not print secret values.
- Flag network exposure and cloud fallback risks.
- Check JSON schema compatibility.
- Check missing tests for scanner behavior.

## Optional Custom GitHub Action

If the team later wants a custom workflow, use `openai/codex-action`:

- Trigger on `pull_request`.
- Checkout the PR merge commit.
- Run Codex with a review prompt.
- Post the final Codex output as a PR comment.

This gives more control but also requires managing API keys, workflow permissions, sandboxing, and cost.

## Current Recommendation

For MVP:

- Use official Codex PR review after Codex Cloud is enabled.
- Keep `AGENTS.md` focused and short.
- Ask Codex manually with `@codex review` until the team is comfortable.
- Turn on automatic reviews once PR volume increases.
