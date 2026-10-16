# Cairn

**The short documents every new collaborator needs, and a check that they stay true.**

A cairn is a stack of stones that marks a trail. Cairn writes a few short
onboarding pages for your project and checks that they stay small, current
and linked. A session, human or agent, starts on about 5 KB and reads
deeper only as the task needs.

You get a root `CLAUDE.md`, `README.md`, `ARCHITECTURE.md`,
`CONTRIBUTING.md` and `CHANGELOG.md`, plus a page in each working folder of
a code project. It works on a codebase or a novel alike, and never
overwrites a file you wrote.

## Install

Copy the skill into your Claude Code skills folder:

```bash
cp -r skills/cairn ~/.claude/skills/cairn
```

```powershell
Copy-Item -Recurse skills\cairn $HOME\.claude\skills\cairn
```

Python's standard library is the only dependency.

## Use

Run `/cairn` in your project and answer five questions: name, intent,
project type, new or existing project, tracked or local files. Then:

```
/cairn status    last done, next, and what waits on you
/cairn audit     check budgets, links and freshness
/cairn maintain  session-end refresh of generated lines and pages
/cairn migrate   move a 1.x project to these pages
```

The full guide is [docs/usage.md](docs/usage.md).

## Help and contributing

Open an issue for questions or ideas. To change Cairn, read
[CONTRIBUTING.md](CONTRIBUTING.md); `main` takes pull requests only.

## License

MIT © 2026 Johnathan Hyden
