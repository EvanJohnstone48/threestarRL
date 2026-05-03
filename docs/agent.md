# Agent Operating Process

This codebase is built with an agent-assisted development process.

The goal is not to let the agent vaguely “build the app.” The goal is to give the agent a clear shared understanding, a precise product direction, a structured set of implementation issues, and a repeatable execution loop.

The agent should always treat this file as the operating guide for how work moves from idea to implementation.

---

## Core Principle

Before coding, the agent must understand the project.

The agent should not jump straight from a vague idea to code. It should first help clarify the idea, convert that idea into a product requirement document, break the product into small implementation issues, and then execute one small vertical slice at a time.

The preferred unit of progress is a **tracer bullet**.

A tracer bullet is a thin, working slice through the full system. It may be rough, but it proves the path from input to output. It should touch the real architecture early instead of building isolated pieces that only connect later.

---

## Documentation Structure

This codebase may contain multiple PRDs.

Each PRD belongs to a specific documentation folder. The agent should treat each documentation folder as its own planning context.

Example structure:

```md
docs/
  sandbox/
    prd.md
    issues/
      issue-001.md
      issue-002.md

  barracks/
    prd.md
    issues/
      issue-001.md
      issue-002.md

  image-to-grid/
    prd.md
    issues/
      issue-001.md
      issue-002.md