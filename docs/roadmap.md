# Roadmap - cairn

The 1.x ladder (1.0 standalone tool, 1.1 audit and maintain, 1.2 conventions)
is complete and retired by 2.0 ([ADR 0009](../decisions/0009-onboarding-documents-replace-the-strata.md)).
Current: `2.0.0`, per `.claude-plugin/plugin.json`. What shipped is in
[CHANGELOG.md](../CHANGELOG.md); the design is in [design-2.0.md](design-2.0.md).

## Open

- [ ] **Stranger onboarding**: harden the quickstart for someone who has
      never seen Cairn, including the marketplace install-test.
- [ ] **Publish** to the plugin marketplace. Held.
- [ ] **First consumer**: the SDLC kit migrates with `/cairn migrate`, in
      its own repo.
- [ ] **Other project types** become modules once the software module has
      run in anger; the wiki project is the first candidate.
