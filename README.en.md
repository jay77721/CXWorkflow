# CXWorkflow

[中文 README](./README.md)

CXWorkflow is a multi-session Codex development workflow. It turns one AI coding assistant into a small, persistent development team by giving each Codex thread a clear role, memory boundary, and collaboration responsibility.

This repository is also a Codex plugin. The plugin manifest lives in `.codex-plugin/plugin.json`, and the reusable workflow skill lives in `skills/cxworkflow/SKILL.md`.

## Codex Plugin

This project includes a Codex plugin configuration, so it can be installed and used as a Codex plugin.

- Plugin manifest: `.codex-plugin/plugin.json`
- Plugin name: `cxworkflow`
- Display name: `CXWorkflow`
- Category: `Productivity`
- Skills directory: `skills/`
- Workflow skill: `skills/cxworkflow/SKILL.md`

After installation, Codex can discover the CXWorkflow skill and use it when a user wants to create, explain, or operate a multi-session development team. The plugin default prompt is:

```text
Help me set up a CXWorkflow Codex development team for this project.
```

## What It Solves

A single Codex session is convenient for quick edits and questions, but larger projects often overload one thread with planning, implementation, testing, decision memory, and progress reporting.

CXWorkflow separates those responsibilities:

- Commander owns direction and task breakdown.
- Secretary owns project memory and status synchronization.
- Developer owns implementation.
- Tester owns quality review and risk discovery.
- Reporter owns progress visibility.
- Observer owns system-level workflow and structural review.

This structure is designed for long-running projects, multi-module features, complex refactors, AI-assisted product development, and any repo where a single chat thread becomes too crowded to manage safely.

## Team Roles

| Session | Role | Responsibility |
| --- | --- | --- |
| `Commander` / `指挥` | Project lead | Understands the whole project, breaks down work, assigns tasks, defines priorities, and makes final direction calls. |
| `Secretary` / `秘书` | PMO and project memory | Records decisions, tracks task status, keeps cross-thread context synchronized, and prevents project memory loss. |
| `Developer` / `开发` | Main engineer | Implements features, fixes bugs, refactors code, verifies changes, and reports results back to Commander and Secretary. |
| `Tester` / `测试` | QA and reviewer | Reviews code quality, runs tests, finds bugs, checks regression risk, and reports issues by severity. |
| `Reporter` / `汇报` | Progress reporter | Collects project status from other sessions and produces concise progress reports. |
| `Observer` / `obs` | External observer | Reviews the whole workflow, checks whether the team structure is complete, and identifies missing roles, process gaps, or strategic risks. |

## How It Works

1. Start `Commander` first.
   Commander reads the project, understands the goal, and decomposes the work.

2. Start `Secretary`.
   Secretary records the plan, decisions, task ownership, blockers, and important context.

3. Start `Developer`.
   Developer follows Commander instructions and implements concrete code changes.

4. Start `Tester`.
   Tester reviews the implementation, runs validation, and reports risks or defects.

5. Start `Reporter`.
   Reporter summarizes what each thread is doing and gives the human owner a quick project snapshot.

6. Start `Observer`.
   Observer checks the whole system from a higher level and points out missing coverage, process weaknesses, or architectural concerns.

## Recommended One-Click Setup Prompt

Use this prompt in Codex to create the full team in one step:

```text
Please create a Codex multi-session development team for the current project. Every session should use the current repository as its working directory.

Create and name the following sessions:

1. Commander
Responsibility: You are the project lead. Read the whole project and existing context, understand the goal, break down tasks, define the development route, and assign work to the other sessions. Do not do large implementation work directly. Prioritize decisions, planning, coordination, and acceptance criteria.

2. Secretary
Responsibility: You are the project secretary. Record project decisions, task status, thread progress, todos, and blockers. Regularly organize project status so multi-session collaboration does not lose context.

3. Developer
Responsibility: You are the main developer. Implement code changes, bug fixes, refactors, and features based on Commander instructions. Before each change, understand the code structure. After each change, run necessary validation and report results to Secretary and Commander.

4. Tester
Responsibility: You are the tester and code reviewer. Review code quality, run tests, find bugs, coverage gaps, architectural risks, and regression risks. Report issues to Secretary and Commander by severity.

5. Reporter
Responsibility: You are the progress reporter. Periodically ask for or read status from other sessions and produce progress reports covering completed work, in-progress work, blockers, risks, and recommended next steps.

6. obs
Responsibility: You are the observer. Watch the AI development team from a system-level perspective. Check for missing modules, process gaps, missing roles, strategic drift, or quality risks, and propose improvements.

After creation, list each session's threadId, title, and responsibility, and pin these sessions if possible.
```

Short version:

```text
Please create a Codex multi-session development team for the current project: Commander, Secretary, Developer, Tester, Reporter, and obs. Each session should work in the current repository and separately own project direction, status coordination, implementation, quality review, progress reporting, and system-level observation. After creation, list the threadId and purpose for each session, and pin them.
```

## Suggested Reporting Format

Reporter can use this format when summarizing the team:

```md
# Project Status

## Completed
- ...

## In Progress
- ...

## Blocked
- ...

## Risks
- ...

## Next Steps
- ...
```

## When To Use This Workflow

Use CXWorkflow when:

- The project will last more than one session.
- The work touches multiple modules or files.
- You need continuous planning, coding, testing, and reporting.
- You want Codex to behave more like a development team than a single assistant.
- You are experimenting with AI-native software team structures.

For small one-file fixes or simple questions, a single Codex session is usually enough.
