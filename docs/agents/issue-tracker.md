# Issue tracker: GitHub

Issues and specifications live in the GitHub Issues tracker for `chandrabs25/learneros`. Use `gh` from this clone so the remote is resolved automatically.

## Common operations

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."`
- Close: `gh issue close <number> --comment "..."`

## Pull requests as a triage surface

PRs as a request surface: no.

When an engineering skill says to publish to the issue tracker, create a GitHub issue. A bare `#42` may identify an issue or pull request; resolve its type before acting.
