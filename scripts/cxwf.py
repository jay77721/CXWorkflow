#!/usr/bin/env python3
"""CXWorkflow state CLI — file-backed single source of truth for the team.

Why this exists:
  CXWorkflow's protocol says "Secretary is the single source of truth". A
  Secretary session's conversation memory is not durable: it can be compacted
  or lost. This CLI makes the source of truth a real, file-backed store under
  `.cxworkflow/` so any session (or the user) can read/write state across
  threads, restarts, and crashes.

Layout (all created by `cxwf init`):
  .cxworkflow/
  ├── README.md        # format documentation (committed)
  ├── .gitignore       # ignores transient state (committed)
  ├── state.json       # task state machine: id -> task record
  ├── events.log       # append-only JSONL event log
  ├── decisions.md     # Commander decision log (appended)
  └── briefs/          # Secretary briefs forwarded to Commander

Commands:
  cxwf init [--force]
  cxwf task add --title <t> [--owner <o>] [--id <id>]
  cxwf task set <id> --status <s> [--by <role>]
  cxwf event --event <e> --source <s> [--task <id>] [--status <s>] \
        [--severity <sev>] [--evidence <t>] [--suggested-next <t>] \
        [--needs-commander yes|no]
  cxwf decision <text>            # append a Commander decision
  cxwf brief <text>               # write a Secretary brief file
  cxwf get [--id <id>]
  cxwf check
  cxwf prompt --level <0-3> [--lang zh|en]   # one-click session prompt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_VERSION = 1

STATE_MACHINE = [
    "Planned",
    "Assigned",
    "Implementing",
    "ReadyForTest",
    "Testing",
    "Fixing",
    "Accepted",
    "Reported",
]

# Allowed forward transitions plus the re-work edges that real teams need.
ALLOWED_TRANSITIONS = {
    "Planned": {"Assigned"},
    "Assigned": {"Implementing"},
    "Implementing": {"ReadyForTest"},
    "ReadyForTest": {"Testing"},
    "Testing": {"Fixing", "Accepted"},
    "Fixing": {"Implementing", "ReadyForTest"},
    "Accepted": {"Reported"},
    "Reported": set(),
}

EVENTS = {
    "TaskCreated",
    "TaskFinished",
    "TestFailed",
    "TestPassed",
    "Blocked",
    "MilestoneReached",
    "RateLimitWarning",
    "ProgressReport",
    "RecoverySuggestion",
}

SEVERITIES = {"info", "warning", "blocking", "critical"}

ROLES = {"commander", "secretary", "developer", "tester", "reporter", "obs", "user"}

LEVELS = {
    0: ["commander"],
    1: ["commander", "developer"],
    2: ["commander", "developer", "tester"],
    3: ["commander", "secretary", "developer", "tester", "reporter", "obs"],
}

ROLE_NAMES = {
    "commander": "指挥",
    "secretary": "秘书",
    "developer": "开发",
    "tester": "测试",
    "reporter": "汇报",
    "obs": "obs",
}

# ---------------------------------------------------------------------------
# State store
# ---------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_state() -> dict:
    return {"version": STATE_VERSION, "load_level": 1, "paused": False, "updated_at": now_iso(), "tasks": {}}


def state_path(root: Path) -> Path:
    return root / ".cxworkflow" / "state.json"


def load_state(root: Path) -> dict:
    path = state_path(root)
    if not path.is_file():
        raise SystemExit(f"No state file at {path}. Run `cxwf init` first.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Corrupt state file {path}: {exc}")
    return data


def save_state(root: Path, state: dict) -> None:
    state["updated_at"] = now_iso()
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def events_path(root: Path) -> Path:
    return root / ".cxworkflow" / "events.log"


def append_event(root: Path, record: dict) -> None:
    path = events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def cxwf_dir(root: Path) -> Path:
    return root / ".cxworkflow"


def init_store(root: Path, force: bool) -> None:
    base = cxwf_dir(root)
    if base.exists() and not force and state_path(root).exists():
        raise SystemExit(f"{base} already initialized. Use --force to reinitialize.")
    base.mkdir(parents=True, exist_ok=True)
    (base / "briefs").mkdir(exist_ok=True)
    if not (base / "README.md").is_file():
        (base / "README.md").write_text(CXWF_README, encoding="utf-8")
    if not (base / ".gitignore").is_file():
        (base / ".gitignore").write_text("state.json\nevents.log\ndecisions.md\nbriefs/\n", encoding="utf-8")
    if not state_path(root).is_file():
        save_state(root, empty_state())
    if not events_path(root).is_file():
        (base / "events.log").touch()
    print(f"Initialized CXWorkflow state store at {base}")


# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------


def normalize_role(role: str) -> str:
    return role.strip().lower()


def valid_transition(state: dict, task_id: str, new_status: str) -> None:
    task = state["tasks"].get(task_id)
    if task is None:
        raise SystemExit(f"Unknown task id: {task_id}")
    old = task["status"]
    if old == new_status:
        return
    allowed = ALLOWED_TRANSITIONS.get(old, set())
    if new_status not in allowed:
        allowed_text = ", ".join(sorted(allowed)) if allowed else "(terminal state)"
        raise SystemExit(
            f"Invalid transition {old} -> {new_status} for task {task_id}; "
            f"allowed: {allowed_text}"
        )


def apply_transition(state: dict, task_id: str, new_status: str, by: str) -> None:
    task = state["tasks"][task_id]
    task["history"].append({"status": new_status, "at": now_iso(), "by": by})
    task["status"] = new_status


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_task_add(args: argparse.Namespace, root: Path) -> None:
    state = load_state(root)
    task_id = args.id or f"T{len(state['tasks']) + 1:03d}"
    if task_id in state["tasks"]:
        raise SystemExit(f"Task id already exists: {task_id}")
    owner = normalize_role(args.owner) if args.owner else "developer"
    if owner not in ROLES:
        raise SystemExit(f"Unknown owner role: {owner}")
    state["tasks"][task_id] = {
        "title": args.title,
        "owner": owner,
        "status": "Planned",
        "severity": "info",
        "evidence": "",
        "suggested_next": "",
        "needs_commander": False,
        "created_at": now_iso(),
        "history": [{"status": "Planned", "at": now_iso(), "by": "commander"}],
    }
    save_state(root, state)
    print(f"Added task {task_id}: {args.title} (owner: {owner}, status: Planned)")


def cmd_task_set(args: argparse.Namespace, root: Path) -> None:
    state = load_state(root)
    by = normalize_role(args.by) if args.by else "user"
    valid_transition(state, args.task, args.status)
    apply_transition(state, args.task, args.status, by)
    save_state(root, state)
    print(f"Task {args.task}: -> {args.status} (by {by})")


def cmd_event(args: argparse.Namespace, root: Path) -> None:
    event = args.event
    source = normalize_role(args.source)
    if event not in EVENTS:
        raise SystemExit(f"Unknown event: {event}; known: {', '.join(sorted(EVENTS))}")
    if source not in ROLES:
        raise SystemExit(f"Unknown source role: {source}")
    severity = args.severity or "info"
    if severity not in SEVERITIES:
        raise SystemExit(f"Unknown severity: {severity}; use {', '.join(sorted(SEVERITIES))}")
    needs = (args.needs_commander or "no").lower()
    if needs not in {"yes", "no"}:
        raise SystemExit("--needs-commander must be yes or no")
    if needs == "yes" and not args.suggested_next:
        raise SystemExit("--needs-commander yes requires --suggested-next")

    record = {
        "ts": now_iso(),
        "event": event,
        "source": source,
        "task": args.task,
        "status": args.status,
        "severity": severity,
        "evidence": args.evidence or "",
        "suggested_next": args.suggested_next or "",
        "needs_commander": needs == "yes",
    }
    append_event(root, record)

    if args.task and args.status:
        state = load_state(root)
        valid_transition(state, args.task, args.status)
        apply_transition(state, args.task, args.status, source)
        save_state(root, state)

    print(f"Logged {event} from {source}" + (f" -> task {args.task}: {args.status}" if args.task and args.status else ""))


def cmd_decision(args: argparse.Namespace, root: Path) -> None:
    path = cxwf_dir(root) / "decisions.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"## {now_iso()}\n\n{args.text.strip()}\n\n")
    print(f"Appended decision to {path}")


def cmd_brief(args: argparse.Namespace, root: Path) -> None:
    briefs = cxwf_dir(root) / "briefs"
    briefs.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = briefs / f"brief-{ts}.md"
    path.write_text(args.text.strip() + "\n", encoding="utf-8")
    print(f"Wrote brief {path}")


def cmd_get(args: argparse.Namespace, root: Path) -> None:
    state = load_state(root)
    if args.id:
        if args.id not in state["tasks"]:
            raise SystemExit(f"Unknown task id: {args.id}")
        print(json.dumps(state["tasks"][args.id], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(state, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# message / level / rate-limit
# ---------------------------------------------------------------------------

MESSAGE_FIELDS = (
    "Event", "Source", "Task", "Status", "Severity",
    "Evidence", "Suggested Next", "Needs Commander",
)


def parse_message_block(text: str) -> dict:
    """Parse a Secretary message in the 8-field format into a dict."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise SystemExit(f"Malformed message line (expected `Field: value`): {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key in MESSAGE_FIELDS:
            fields[key] = value
    return fields


def cmd_message(args: argparse.Namespace, root: Path) -> None:
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    fields = parse_message_block(text)
    missing = [f for f in MESSAGE_FIELDS if not fields.get(f)]
    if missing:
        raise SystemExit(f"Message missing required fields: {', '.join(missing)}")

    needs = fields["Needs Commander"].lower()
    if needs not in {"yes", "no"}:
        raise SystemExit("Needs Commander must be yes or no")
    if needs == "yes" and not fields.get("Suggested Next"):
        raise SystemExit("Needs Commander: yes requires Suggested Next")
    if fields["Event"] not in EVENTS:
        raise SystemExit(f"Unknown event: {fields['Event']}")
    if fields["Source"].lower() not in ROLES:
        raise SystemExit(f"Unknown source role: {fields['Source']}")
    if fields["Severity"] not in SEVERITIES:
        raise SystemExit(f"Unknown severity: {fields['Severity']}")

    append_event(root, {
        "ts": now_iso(),
        "event": fields["Event"],
        "source": fields["Source"].lower(),
        "task": fields.get("Task") or None,
        "status": fields.get("Status") or None,
        "severity": fields["Severity"],
        "evidence": fields.get("Evidence") or "",
        "suggested_next": fields.get("Suggested Next") or "",
        "needs_commander": needs == "yes",
    })

    task_id = fields.get("Task")
    status = fields.get("Status")
    if task_id and status:
        state = load_state(root)
        valid_transition(state, task_id, status)
        apply_transition(state, task_id, status, fields["Source"].lower())
        save_state(root, state)
    print(f"Recorded {fields['Event']} from {fields['Source']}")


def cmd_level(args: argparse.Namespace, root: Path) -> None:
    state = load_state(root)
    state["load_level"] = args.level
    state["paused"] = False
    save_state(root, state)
    print(f"Load level set to L{args.level} (active roles: {', '.join(LEVELS[args.level])})")


def cmd_rate_limit(args: argparse.Namespace, root: Path) -> None:
    state = load_state(root)
    count = args.count
    if count < 0:
        raise SystemExit("--count must be >= 0")
    if count == 0:
        print("No rate-limit pressure; load level unchanged.")
        return
    if count >= 5:
        state["load_level"] = 0
        state["paused"] = True
        action = "连续 5 次 429：保存状态并暂停工作流，等待冷却后从低等级恢复"
    elif count >= 3:
        state["load_level"] = min(state["load_level"], 2)
        state["paused"] = False
        action = "连续 3 次 429：停止 Reporter 和 obs，只保留 Commander 和必要执行线程"
    else:
        state["load_level"] = max(0, state["load_level"] - 1)
        state["paused"] = False
        action = "1 次 429：降低负载等级，暂停非必要线程"
    save_state(root, state)
    append_event(root, {
        "ts": now_iso(),
        "event": "RateLimitWarning",
        "source": "obs",
        "task": None,
        "status": None,
        "severity": "warning",
        "evidence": f"consecutive 429 count={count}",
        "suggested_next": action,
        "needs_commander": count >= 3,
    })
    print(f"Applied rate-limit policy (count={count}): {action}")


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace, root: Path) -> int:
    errors: list[str] = []
    state = load_state(root)
    if state.get("version") != STATE_VERSION:
        errors.append(f"state version {state.get('version')} != expected {STATE_VERSION}")

    required_task_fields = (
        "title", "owner", "status", "severity", "evidence",
        "suggested_next", "needs_commander", "created_at", "history",
    )
    for task_id, task in state.get("tasks", {}).items():
        if not isinstance(task, dict):
            errors.append(f"task {task_id}: must be an object")
            continue
        for field in required_task_fields:
            if field not in task:
                errors.append(f"task {task_id}: missing required field {field!r}")
        status = task.get("status")
        if status not in STATE_MACHINE:
            errors.append(f"task {task_id}: invalid status {status!r}")
        if task.get("owner") not in ROLES:
            errors.append(f"task {task_id}: invalid owner {task.get('owner')!r}")
        if task.get("severity") not in SEVERITIES:
            errors.append(f"task {task_id}: invalid severity {task.get('severity')!r}")
        if task.get("needs_commander") not in (True, False):
            errors.append(f"task {task_id}: needs_commander must be a boolean")

        history = task.get("history")
        if not isinstance(history, list) or not history:
            errors.append(f"task {task_id}: history must be a non-empty list")
            continue
        if not isinstance(history[0], dict) or history[0].get("status") != "Planned":
            errors.append(f"task {task_id}: history must start at Planned")
        prev = None
        for index, entry in enumerate(history):
            if not isinstance(entry, dict) or "status" not in entry:
                errors.append(f"task {task_id}: history[{index}] must be an object with status")
                continue
            cur = entry["status"]
            if cur not in STATE_MACHINE:
                errors.append(f"task {task_id}: history[{index}] invalid status {cur!r}")
            if prev is not None and cur != prev and cur not in ALLOWED_TRANSITIONS.get(prev, set()):
                errors.append(f"task {task_id}: invalid history transition {prev} -> {cur}")
            prev = cur
        last_status = history[-1].get("status") if isinstance(history[-1], dict) else None
        if last_status != status:
            errors.append(
                f"task {task_id}: history tail {last_status!r} != current status {status!r}"
            )

    log = events_path(root)
    if log.is_file():
        for lineno, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"events.log:{lineno}: invalid JSON: {exc}")
                continue
            if rec.get("event") not in EVENTS:
                errors.append(f"events.log:{lineno}: unknown event {rec.get('event')!r}")
            if rec.get("severity") not in SEVERITIES:
                errors.append(f"events.log:{lineno}: unknown severity {rec.get('severity')!r}")
            if rec.get("needs_commander") and not rec.get("suggested_next"):
                errors.append(f"events.log:{lineno}: needs_commander=yes requires suggested_next")

    if errors:
        print("CXWorkflow check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("CXWorkflow check OK")
    return 0


# ---------------------------------------------------------------------------
# prompt (level-parameterized one-click session prompt)
# ---------------------------------------------------------------------------

ROLE_BRIEFS = {
    "commander": (
        "职责：你是项目总指挥。读取整个项目和现有上下文，理解目标，拆分任务，制定开发路线，并向其他线程分配工作。"
        "你只接受秘书转交的汇总消息，不直接接收测试、汇报、obs 或执行线程的零散状态。你不直接做大量实现，"
        "优先负责决策、规划、调度和验收标准。"
    ),
    "secretary": (
        "职责：你是秘书长，也是项目唯一事实源和指挥收件箱。负责记录项目决策、任务状态、各线程进展、待办事项、阻塞点、"
        "测试结果和恢复动作。测试、汇报、obs 和执行线程的消息都先汇总到你这里；你负责去重、分级、补齐上下文，再转交给指挥。"
        "任何角色需要上下文时都应优先读取你的记录。"
    ),
    "developer": (
        "职责：你是主开发手。根据指挥线程的任务进行代码实现、bug 修复、重构和功能落地。每次修改前先理解代码结构，"
        "修改后运行必要验证，并把结果汇报给秘书，由秘书转交给指挥。"
    ),
    "tester": (
        "职责：你是测试手和代码审查员。负责审查代码质量、运行测试、发现 bug、覆盖率缺口、架构风险和回归风险。"
        "请把问题按严重程度汇总给秘书，不要直接打断指挥；由秘书转交给指挥。"
    ),
    "reporter": (
        "职责：你是汇报手。你只在里程碑、用户请求或指挥要求时生成项目进度报告，优先读取秘书状态，不要频繁轮询其他线程。"
        "报告先写给秘书，由秘书决定是否转交给指挥。"
    ),
    "obs": (
        "职责：你是 Workflow Watchdog。正常情况下保持休眠。发现线程掉线、职责漂移、信息不同步、阻塞无人处理、"
        "连续测试失败、429、任务偏离目标或协作流程失效时，你要指出问题，提醒对应线程恢复职责，并把纠偏建议汇总给秘书；"
        "由秘书转交给指挥，帮助团队回到正常轨道。"
    ),
}

# L0-L2 role briefs avoid referencing Secretary/Reporter/obs sessions that do
# not exist at those load levels.
ROLE_BRIEFS_LITE = {
    "commander": (
        "职责：你是项目总指挥。读取整个项目和现有上下文，理解目标，拆分任务，制定开发路线，并向其他线程分配工作。"
        "你负责决策、规划、调度和验收标准；执行线程的进度和结果通过 .cxworkflow/ 状态（scripts/cxwf.py）汇总到你这里。"
    ),
    "developer": (
        "职责：你是主开发手。根据指挥线程的任务进行代码实现、bug 修复、重构和功能落地。每次修改前先理解代码结构，"
        "修改后运行必要验证，并把结果写入 .cxworkflow/ 状态（scripts/cxwf.py event / task set）。"
    ),
    "tester": (
        "职责：你是测试手和代码审查员。负责审查代码质量、运行测试、发现 bug、覆盖率缺口、架构风险和回归风险。"
        "请把结果按严重程度写入 .cxworkflow/ 状态（TestPassed / TestFailed 事件），不要直接打断指挥。"
    ),
}


def role_brief(role: str, level: int) -> str:
    if level >= 3:
        return ROLE_BRIEFS[role]
    return ROLE_BRIEFS_LITE.get(role, ROLE_BRIEFS[role])


def protocol_rules(level: int) -> str:
    """Level-appropriate operating rules; Secretary routing only exists at L3."""
    if level == 0:
        return "\n".join([
            "- 指挥直接决策，无需其他线程。",
            "- 需要跨会话保留的状态写入 .cxworkflow/（scripts/cxwf.py）。",
        ])
    if level == 1:
        return "\n".join([
            "- 开发完成任务后把结果写入 .cxworkflow/ 状态（cxwf.py event / task set），指挥在下一轮读取。",
            "- 任务状态机：Planned -> Assigned -> Implementing -> ReadyForTest -> Testing -> Fixing -> Accepted -> Reported，用 cxwf.py 推进，禁止跳步。",
        ])
    if level == 2:
        return "\n".join([
            "- 开发完成任务后把结果写入 .cxworkflow/ 状态；测试把结果（TestPassed / TestFailed）也写入 .cxworkflow/。",
            "- 任务状态机：Planned -> Assigned -> Implementing -> ReadyForTest -> Testing -> Fixing -> Accepted -> Reported，用 cxwf.py 推进，禁止跳步。",
            "- 测试失败或验收受影响时，由指挥在下一轮决定是否指派修复。",
        ])
    return PROTOCOL_RULES


PROTOCOL_RULES = (
    "- 非指挥线程写给秘书时必须包含 Event、Source、Task、Status、Severity、Evidence、Suggested Next、Needs Commander。\n"
    "- 秘书只在阻塞、测试失败、验收受影响、计划需调整、里程碑完成、429、资源压力、线程失控、职责漂移或用户明确需要决策时转交指挥。\n"
    "- 普通进度和低风险观察只记录在秘书，按阶段或检查点批量汇总。\n"
    "- 秘书维护任务状态机：Planned -> Assigned -> Implementing -> ReadyForTest -> Testing -> Fixing -> Accepted -> Reported。\n"
    "- obs 只写异常和恢复建议给秘书，不直接调度或改计划。\n"
    "- 汇报只读取秘书记录并把报告写回秘书，不轮询其他线程。\n"
    "- 阶段后期进入收敛模式：开发停止主动扩展，测试停止轮询，汇报完成后休眠，obs 无异常则休眠。"
)

PROMPT_FIELDS = [
    "Event", "Source", "Task", "Status", "Severity", "Evidence", "Suggested Next", "Needs Commander",
]


def cmd_prompt(args: argparse.Namespace, root: Path) -> None:
    if args.level not in LEVELS:
        raise SystemExit(f"--level must be one of {sorted(LEVELS)}")
    roles = LEVELS[args.level]
    output = prompt_en(args.level, roles) if args.lang == "en" else prompt_zh(args.level, roles)
    if args.out:
        Path(args.out).write_text(output + "\n", encoding="utf-8")
        print(f"Prompt written to {args.out}")
    else:
        print(output)


def prompt_zh(level: int, roles: list[str]) -> str:
    lines = [
        f"请基于当前项目创建 Codex 多线程开发团队（负载等级 L{level}），所有线程都使用当前仓库作为工作目录。",
        "",
        "请创建并命名以下 session：",
        "",
    ]
    for index, role in enumerate(roles, start=1):
        lines.append(f"{index}. {ROLE_NAMES[role]}")
        lines.append(role_brief(role, level))
        lines.append("")
    lines.append("运行协议：")
    lines.append(protocol_rules(level))
    lines.append("")
    if level == 3:
        lines.append(
            "秘书应把状态写入 .cxworkflow/ 状态目录（state.json / events.log / decisions.md / briefs/），"
            "并在需要时用 scripts/cxwf.py 记录事件、推进任务状态和生成简报。"
        )
        lines.append("")
    lines.append("创建完成后，请把每个 session 的 threadId、标题和职责列出来，并尽量 pin 这些线程。")
    return "\n".join(lines)


def prompt_en(level: int, roles: list[str]) -> str:
    lines = [
        f"Create a Codex multi-session development team (load level L{level}) based on this project. "
        "All sessions use the current repository as their working directory.",
        "",
        "Create and name the following sessions:",
        "",
    ]
    for index, role in enumerate(roles, start=1):
        lines.append(f"{index}. {role}")
        lines.append(role_brief(role, level))
        lines.append("")
    lines.append("Operating protocol:")
    lines.append(protocol_rules(level))
    lines.append("")
    if level == 3:
        lines.append(
            "Secretary should persist state under .cxworkflow/ (state.json / events.log / decisions.md / briefs/) "
            "and use scripts/cxwf.py to record events, advance task state, and write briefs."
        )
        lines.append("")
    lines.append("After creation, list each session's threadId, title, and duties, and pin those threads.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

CXWF_README = """# CXWorkflow state store

This directory is the file-backed single source of truth for a CXWorkflow team.

- `state.json` — task state machine (`Planned -> Assigned -> Implementing -> ReadyForTest -> Testing -> Fixing -> Accepted -> Reported`).
- `events.log` — append-only JSONL event log (`TaskCreated`, `TaskFinished`, `TestFailed`, `TestPassed`, `Blocked`, `MilestoneReached`, `RateLimitWarning`, `ProgressReport`, `RecoverySuggestion`).
- `decisions.md` — Commander decisions, appended.
- `briefs/` — Secretary briefs forwarded to Commander.

All roles read state from these files instead of asking other sessions. Manage the
store with `python3 scripts/cxwf.py` (see `--help`). Transient files are git-ignored.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cxwf",
        description="CXWorkflow state CLI — file-backed single source of truth.",
    )
    parser.add_argument("--root", default=".", help="Repository root (default: current directory).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize the .cxworkflow state store.")
    p_init.add_argument("--force", action="store_true")

    p_add = sub.add_parser("task", help="Task operations.")
    task_sub = p_add.add_subparsers(dest="task_command", required=True)
    p_task_add = task_sub.add_parser("add", help="Add a task (starts in Planned).")
    p_task_add.add_argument("--title", required=True)
    p_task_add.add_argument("--owner", default="developer")
    p_task_add.add_argument("--id")
    p_task_set = task_sub.add_parser("set", help="Transition a task to a new state.")
    p_task_set.add_argument("task")
    p_task_set.add_argument("--status", required=True)
    p_task_set.add_argument("--by", default="user")

    p_event = sub.add_parser("event", help="Append an event and optionally advance a task.")
    p_event.add_argument("--event", required=True)
    p_event.add_argument("--source", required=True)
    p_event.add_argument("--task")
    p_event.add_argument("--status")
    p_event.add_argument("--severity", default="info")
    p_event.add_argument("--evidence")
    p_event.add_argument("--suggested-next")
    p_event.add_argument("--needs-commander", default="no")

    p_dec = sub.add_parser("decision", help="Append a Commander decision.")
    p_dec.add_argument("text")

    p_brief = sub.add_parser("brief", help="Write a Secretary brief file.")
    p_brief.add_argument("text")

    p_get = sub.add_parser("get", help="Print state (optionally one task).")
    p_get.add_argument("--id")

    sub.add_parser("check", help="Validate state and event log.")

    p_prompt = sub.add_parser("prompt", help="Generate a level-parameterized one-click session prompt.")
    p_prompt.add_argument("--level", type=int, required=True, choices=sorted(LEVELS))
    p_prompt.add_argument("--lang", default="zh", choices=["zh", "en"])
    p_prompt.add_argument("--out", help="Write the prompt to a file instead of stdout.")

    p_msg = sub.add_parser("message", help="Record a Secretary message in the 8-field format.")
    p_msg.add_argument("--text", help="Message block as a string.")
    p_msg.add_argument("--file", help="Read the message block from a file.")

    p_level = sub.add_parser("level", help="Manage the load level.")
    level_sub = p_level.add_subparsers(dest="level_command", required=True)
    p_level_set = level_sub.add_parser("set", help="Set the load level (0-3).")
    p_level_set.add_argument("level", type=int, choices=sorted(LEVELS))

    p_rl = sub.add_parser("rate-limit", help="Apply the 429 rate-limit downgrade policy.")
    p_rl.add_argument("--count", type=int, required=True, help="Consecutive 429 count.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command == "init":
            init_store(root, args.force)
        elif args.command == "task":
            if args.task_command == "add":
                cmd_task_add(args, root)
            else:
                cmd_task_set(args, root)
        elif args.command == "event":
            cmd_event(args, root)
        elif args.command == "decision":
            cmd_decision(args, root)
        elif args.command == "brief":
            cmd_brief(args, root)
        elif args.command == "get":
            cmd_get(args, root)
        elif args.command == "check":
            return cmd_check(args, root)
        elif args.command == "prompt":
            cmd_prompt(args, root)
        elif args.command == "message":
            cmd_message(args, root)
        elif args.command == "level":
            cmd_level(args, root)
        elif args.command == "rate-limit":
            cmd_rate_limit(args, root)
    except SystemExit as exc:
        # argparse uses SystemExit too; re-raise with clean message.
        raise exc
    return 0


if __name__ == "__main__":
    sys.exit(main())
