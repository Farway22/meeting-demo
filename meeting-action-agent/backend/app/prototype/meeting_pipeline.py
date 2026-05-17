"""
会议文本 -> 行动项（LLM 结构化 JSON）-> 补全负责人 -> 按人聚合 To-do。

仅在 prototype 层做轻量结构增强（不引入 FastAPI/DB/OpenClaw/前端）。
第四阶段：稳定 task_id + subtasks 结构化 + 依赖驱动排序
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.prototype.llm import call_llm

UNASSIGNED = "未分配"
_TASK_KEYS = ("task", "text", "title", "content")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
EXTRACT_SYSTEM_PROMPT = """你是一个「会议行动项分析助手」。

你的任务是：从会议内容中提取所有「需要执行或跟进的事项（action items）」，并只输出可被 json.loads 解析的 JSON 数组，不要 Markdown、不要解释、不要代码围栏。

## 什么是任务（非常重要）

任务是会议中出现的、需要后续执行或推进的事项，包括：
- 明确执行任务（如开发、修改、提交等）
- 多人协作任务（如联调、推进某项目）
- 需要进一步拆解或确认的事项

## 什么不算任务

以下内容不要当作任务：
- 纯讨论
- 情绪表达
- 意见或建议（未形成行动）
- 背景描述
- 单纯信息同步

## 关于任务类型

每个任务必须判断：
- task_level：atomic（单人可完成）或 composite（多人协作或需拆解）
- needs_decomposition：composite 则为 true，atomic 则为 false

## 复合任务（composite）-> 多人推断（重点）

当任务为以下类型时：
- 联调（frontend/backend integration）
- 对接
- 协作开发
- 上线准备
- 系统推进
- 流程推进

请主动推断可能需要多个角色参与，而不仅仅是一个人。
要求：
- 如果识别为 composite 任务：优先输出多个 owners（即使原文只提到一个人）
- owners 可以基于参与者列表进行合理补全
- owner_type = "multi"

## 关于负责人（owners）的人 vs 角色区分（重点）

会议中可能出现两种负责人：

### 1. 具体人（person）
- 张三
- 李四

### 2. 角色（role）
- 行政
- 测试
- 前端
- 产品

要求：
- 如果是明确人名 -> 填入 owners.name
- 如果是角色（如"行政处理一下"）：
  - 仍然填入 owners，但 role 字段必须正确
  - owners.name 可以保持为该角色名称（如"行政"）
  - 并标记为"基于角色的负责人"（owner_resolution = "role"）

不要强行虚构人名。

## 关于负责人（owners）

- 会议中明确提到负责人则填入，格式为对象数组：[{"name":"...","role":"..."}]，role 可空字符串
- 多人协作则填多个
- 无法判断则 owners 为 []

并给出 owner_type：
- single：一人
- multi：多人
- unknown：无法确定

## 关于优先级（priority）

请综合判断，而不是只看时间。考虑：是否紧急、是否影响核心流程、是否会阻塞其他任务、影响范围、风险程度。

输出：
- priority：必须是 high、medium、low 之一
- priority_reason：一句话说明为何是该优先级

## 关于任务置信度（confidence）【必须输出】

请为每个任务给出一个 confidence（0~1），表示该任务是否明确来自会议内容。
规则参考：
- 明确责任 + 明确动作（如"我来做""张三负责"）-> >= 0.8
- 明确任务但无负责人 -> 0.6 ~ 0.8
- 推断型任务 -> 0.4 ~ 0.6
- 模糊任务 -> <= 0.4

## 关于子任务（subtasks，composite 任务必须给出结构化子任务）

如果任务是 composite（多人协作/需要拆解）：
- 必须给出子任务（subtasks），不能返回 []
- 每个 subtask 必须是结构化对象，不能是字符串：
  {"task":"...","owner":"姓名或 null","depends_on":"前置 subtask 的 task 文本或 null"}
- 子任务必须是独立可执行任务，具备清晰动作，尽量可分配负责人
- subtask 之间必须尽量形成「链式依赖」，体现执行顺序：
  第一步 depends_on=null，后续步骤的 depends_on 指向上一步的 task 文本
- 避免无关联的并列子任务，优先体现「先做什么，再做什么」
- atomic 任务返回 []。

## 关于任务依赖关系（dependencies，仅识别简单情况但字段必须存在）

- 如果明确出现"等...完成后""依赖...""先...再..."等依赖/先后关系，可以填 dependencies
- dependencies 必须指向「任务本身的名称」，而不是描述性句子
  错误："等接口好了"
  正确："补齐后端接口"
- 尽量使用与其他 task 字段完全一致的表达，方便后处理关联
- 如果一个任务已存在，dependencies 中必须复用该任务名称，不要用不同表述
- 否则返回 []。

## 关于阻塞任务标记（is_blocker）【必须输出】

请为每个任务判断是否是「阻塞型任务」：
- 如果该任务被其他任务依赖（其他任务必须等它完成才能开始）→ is_blocker = true
- 如果该任务一旦延误会直接阻塞关键流程 → is_blocker = true
- 否则 → is_blocker = false

## 输出格式（必须严格为 JSON 数组）

每个元素字段齐全：
- task：字符串
- task_level："atomic" 或 "composite"
- needs_decomposition：布尔
- subtasks：list（composite 则给出结构化子任务，atomic 则 []）
- owners：数组，元素为 {"name":"...","role":"..."}
- owner_type："single"、"multi" 或 "unknown"
- owner_resolution："person" 或 "role"
- deadline：字符串或 null
- priority："high"、"medium" 或 "low"
- priority_reason：字符串
- confidence：0~1 浮点数
- is_blocker：布尔
- dependencies：list（没有则 []）
- evidence：来自会议的原句

参与者名单仅作姓名与角色参考（见用户消息），输出中的 name 尽量与会议原文一致。"""


# ---------------------------------------------------------------------------
# 参与者规范化
# ---------------------------------------------------------------------------

def normalize_participants(
    participants: list[str] | list[dict[str, Any]],
) -> list[dict[str, str]]:
    """
    统一为 [{ "name": str, "role": str}, ...]
    兼容：
    - ["张三", "李四"]
    - [{"name":"张三","role":"产品经理"}, ...]
    """
    out: list[dict[str, str]] = []
    for p in participants:
        if isinstance(p, str):
            n = p.strip()
            if n:
                out.append({"name": n, "role": ""})
            continue
        if isinstance(p, dict):
            name = str(p.get("name", "")).strip()
            if not name:
                continue
            role = str(p.get("role", "") or "").strip()
            out.append({"name": name, "role": role})
    return out


def _participant_prompt_lines(parts: list[dict[str, str]]) -> str:
    lines = []
    for x in parts:
        if x.get("role"):
            lines.append(f"- {x['name']}（{x['role']}）")
        else:
            lines.append(f"- {x['name']}")
    return "\n".join(lines) if lines else "（无）"


def _role_lookup(participants: list[dict[str, str]]) -> dict[str, str]:
    return {p["name"]: p.get("role", "") or "" for p in participants if p.get("name")}


def _role_names(participants: list[dict[str, str]]) -> list[str]:
    return [p["name"] for p in participants if p.get("name")]


# ---------------------------------------------------------------------------
# 字段规范化辅助函数
# ---------------------------------------------------------------------------

def _null_if_empty(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _normalize_priority(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in ("high", "medium", "low"):
        return s
    if s in ("高",):
        return "high"
    if s in ("中",):
        return "medium"
    if s in ("低",):
        return "low"
    return "medium"


def _normalize_task_level(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in ("atomic", "composite"):
        return s
    if s in ("原子", "单一"):
        return "atomic"
    if s in ("复合", "组合"):
        return "composite"
    return "atomic"


def _normalize_owner_type(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in ("single", "multi", "unknown"):
        return s
    return "unknown"


def _parse_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "是"):
        return True
    if s in ("false", "0", "no", "否"):
        return False
    return default


def _parse_confidence(v: Any, default: float = 0.5) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        f = default
    return max(0.0, min(1.0, f))


def _coerce_list(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return []


def _parse_owners_raw(raw: Any, role_by_name: dict[str, str]) -> list[dict[str, str]]:
    if not raw:
        return []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for o in raw:
        if isinstance(o, str):
            n = o.strip()
            if n:
                out.append({"name": n, "role": role_by_name.get(n, "")})
            continue
        if isinstance(o, dict):
            n = str(o.get("name", "")).strip()
            if not n:
                continue
            role = str(o.get("role", "") or "").strip() or role_by_name.get(n, "")
            out.append({"name": n, "role": role})
    return out


def _coerce_task_item(item: Any, role_by_name: dict[str, str]) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    task_text = ""
    for k in _TASK_KEYS:
        if item.get(k) is not None:
            task_text = str(item[k]).strip()
            if task_text:
                break
    if not task_text:
        return None

    tl = _normalize_task_level(item.get("task_level"))
    nd = _parse_bool(item.get("needs_decomposition"), tl == "composite")
    if tl == "composite" and not nd:
        nd = True
    if tl == "atomic" and nd:
        nd = False

    owners = _parse_owners_raw(item.get("owners"), role_by_name)
    ot = _normalize_owner_type(item.get("owner_type"))
    if owners:
        ot = "single" if len(owners) == 1 else "multi"
    elif ot not in ("single", "multi", "unknown"):
        ot = "unknown"

    pr = str(item.get("priority_reason", "") or "").strip()
    if not pr:
        pr = "模型未给出理由，已按 priority 字段保留。"

    owner_resolution = str(item.get("owner_resolution", "") or "").strip().lower()
    if owner_resolution not in ("person", "role"):
        if owners and all(o.get("name") in role_by_name for o in owners if isinstance(o, dict)):
            owner_resolution = "person"
        else:
            owner_resolution = "role"

    return {
        "task": task_text,
        "task_level": tl,
        "needs_decomposition": nd,
        "subtasks": _coerce_list(item.get("subtasks")),
        "owners": owners,
        "owner_type": ot,
        "owner_resolution": owner_resolution,
        "deadline": _null_if_empty(item.get("deadline")),
        "priority": _normalize_priority(item.get("priority")),
        "priority_reason": pr,
        "confidence": _parse_confidence(item.get("confidence"), default=0.5),
        "is_blocker": bool(item.get("is_blocker", False)),
        "dependencies": _coerce_list(item.get("dependencies")),
        "evidence": str(item.get("evidence", "") or "").strip(),
    }


def _parse_json_array_from_response(text: str) -> list[Any]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        data = json.loads(t)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", t)
    if m:
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            pass
    return []


def _is_heading_only_line(s: str) -> bool:
    t = s.strip()
    if len(t) < 2:
        return True
    return bool(re.match(r"^.{1,24}[：:]\s*$", t))


# ---------------------------------------------------------------------------
# Fallback（无 LLM 时的启发式拆分）
# ---------------------------------------------------------------------------

def extract_tasks_fallback(meeting_text: str) -> list[dict[str, Any]]:
    """无 LLM 时的启发式拆分；字段与正式 schema 对齐。"""
    fb_reason = (
        "未调用语言模型或 JSON 解析失败；启发式路径下优先级默认 medium，"
        "后续负责人由规则从正文匹配补全。"
    )
    text = meeting_text.strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"[。\n]+", text) if p.strip()]
    if not parts:
        parts = [text]

    out: list[dict[str, Any]] = []
    for p in parts:
        if _is_heading_only_line(p):
            continue
        out.append(
            {
                "task": p,
                "task_level": "atomic",
                "needs_decomposition": False,
                "subtasks": [],
                "owners": [],
                "owner_type": "unknown",
                "owner_resolution": "role",
                "deadline": None,
                "priority": "medium",
                "priority_reason": fb_reason,
                "confidence": 0.5,
                "is_blocker": False,
                "dependencies": [],
                "evidence": p,
            }
        )
    return out


# ---------------------------------------------------------------------------
# 任务抽取
# ---------------------------------------------------------------------------

def extract_tasks(meeting_text: str, participants: list[dict[str, str]]) -> list[dict[str, Any]]:
    role_by_name = _role_lookup(participants)
    user_msg = (
        "会议内容：\n"
        f"{meeting_text.strip()}\n\n"
        "参与者（姓名与角色参考）：\n"
        f"{_participant_prompt_lines(participants)}\n"
    )
    raw = call_llm(user_msg, system=EXTRACT_SYSTEM_PROMPT, temperature=0.1)
    if not raw:
        return extract_tasks_fallback(meeting_text)

    arr = _parse_json_array_from_response(raw)
    if not arr:
        return extract_tasks_fallback(meeting_text)

    tasks: list[dict[str, Any]] = []
    for el in arr:
        coerced = _coerce_task_item(el, role_by_name)
        if coerced:
            tasks.append(coerced)
    return tasks if tasks else extract_tasks_fallback(meeting_text)


# ---------------------------------------------------------------------------
# 负责人补全
# ---------------------------------------------------------------------------

def _names_in_text(blob: str, names: list[str]) -> list[str]:
    seen: list[str] = []
    for n in names:
        if n and n in blob and n not in seen:
            seen.append(n)
    return seen


def assign_roles(
    tasks: list[dict[str, Any]],
    participants: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """
    owners 非空则保留（并补全 role）。
    owners 为空则从 task+evidence 匹配参与者名字。
    """
    role_by_name = _role_lookup(participants)
    names = _role_names(participants)
    out: list[dict[str, Any]] = []

    for t in tasks:
        owners = list(t.get("owners") or [])
        if owners:
            filled: list[dict[str, str]] = []
            for o in owners:
                if not isinstance(o, dict):
                    continue
                nm = str(o.get("name", "")).strip()
                if not nm:
                    continue
                role = str(o.get("role", "") or "").strip() or role_by_name.get(nm, "")
                filled.append({"name": nm, "role": role})
            ot = "single" if len(filled) == 1 else "multi"
            owner_resolution = str(t.get("owner_resolution", "") or "").strip().lower()
            if owner_resolution not in ("person", "role"):
                owner_resolution = "person" if filled and all(x.get("name") in role_by_name for x in filled) else "role"
            out.append({**t, "owners": filled, "owner_type": ot, "owner_resolution": owner_resolution})
            continue

        blob = f"{t.get('task', '')} {t.get('evidence', '')}"
        matched = _names_in_text(blob, names)
        if not matched:
            out.append({**t, "owners": [], "owner_type": "unknown", "owner_resolution": "role"})
        elif len(matched) == 1:
            nm = matched[0]
            out.append({**t, "owners": [{"name": nm, "role": role_by_name.get(nm, "")}], "owner_type": "single", "owner_resolution": "person"})
        else:
            out.append({**t, "owners": [{"name": nm, "role": role_by_name.get(nm, "")} for nm in matched], "owner_type": "multi", "owner_resolution": "person"})
    return out


def normalize_confidence(task: dict[str, Any]) -> None:
    """owners 非空时 confidence 至少抬到 0.7。"""
    if task.get("owners"):
        task["confidence"] = max(_parse_confidence(task.get("confidence"), default=0.5), 0.7)


# ---------------------------------------------------------------------------
# 第四阶段：稳定 task_id + dependency 结构化 + subtasks 规范化 + 依赖驱动排序
# ---------------------------------------------------------------------------

def generate_task_id(task_name: str) -> str:
    """基于任务名称 MD5 前6位生成稳定 ID（同名同 ID，跨次运行不变）。"""
    return "TASK-" + hashlib.md5(task_name.encode("utf-8")).hexdigest()[:6].upper()


def assign_task_ids(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """为每个任务分配稳定 ID（基于任务名称 hash，不依赖顺序索引）。"""
    allocated: dict[str, int] = {}
    for task in tasks:
        base_id = generate_task_id(str(task.get("task", "")))
        count = allocated.get(base_id, 0)
        task["task_id"] = base_id if count == 0 else f"{base_id}-{count}"
        allocated[base_id] = count + 1
    return tasks


def link_dependencies(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将 dependencies 文本替换为对应 task_id；无法匹配的保留原文本；去重保序。"""
    name_to_id: dict[str, str] = {
        t["task"]: t["task_id"] for t in tasks if t.get("task_id") and t.get("task")
    }
    for task in tasks:
        new_deps: list[str] = []
        for dep in task.get("dependencies", []):
            dep_str = str(dep).strip()
            matched_id: str | None = None
            for name, tid in name_to_id.items():
                if tid == task.get("task_id"):
                    continue
                if dep_str in name or name in dep_str:
                    matched_id = tid
                    break
            entry = matched_id or dep_str
            if entry:
                new_deps.append(entry)
        task["dependencies"] = list(dict.fromkeys(new_deps))
    return tasks


def normalize_subtasks(task: dict[str, Any]) -> dict[str, Any]:
    """
    将 subtasks 统一为结构化对象：{"task": str, "owner": str|None, "depends_on": str|None}
    向后兼容旧的字符串格式。
    """
    subs = task.get("subtasks") or []
    new_subs: list[dict[str, Any]] = []
    for s in subs:
        if isinstance(s, str):
            new_subs.append({"task": s.strip(), "owner": None, "depends_on": None})
        elif isinstance(s, dict):
            new_subs.append({
                "task": str(s.get("task", "") or "").strip(),
                "owner": s.get("owner") or None,
                "depends_on": s.get("depends_on") or None,
            })
    task["subtasks"] = new_subs
    return task


def sort_tasks_with_dependencies(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    BFS 拓扑排序（Kahn 算法）：按"执行层次"给出顺序。
    同一层内按 priority 排序（high > medium > low），层次清晰，避免 DFS 任意性。
    """
    _ORDER = {"high": 0, "medium": 1, "low": 2}
    id_map: dict[str, dict[str, Any]] = {t["task_id"]: t for t in tasks if t.get("task_id")}

    # 构建入度表和反向邻接表
    in_degree: dict[str, int] = {tid: 0 for tid in id_map}
    dependents: dict[str, list[str]] = {tid: [] for tid in id_map}
    for t in tasks:
        tid = t.get("task_id", "")
        if not tid:
            continue
        for dep in t.get("dependencies", []):
            if dep in id_map:
                in_degree[tid] = in_degree.get(tid, 0) + 1
                dependents[dep].append(tid)

    def _pri(tid: str) -> int:
        return _ORDER.get(str(id_map[tid].get("priority", "")), 3)

    def _wave_key(tid: str) -> tuple[int, int]:
        # 有下游依赖的任务排在前（关键路径优先），standalone 任务排在后
        has_downstream = 0 if dependents.get(tid) else 1
        return (has_downstream, _pri(tid))

    # 初始波：入度为 0，关键路径任务优先，同层再按 priority 排序
    wave = sorted([tid for tid, deg in in_degree.items() if deg == 0], key=_wave_key)
    result: list[dict[str, Any]] = []
    visited: set[str] = set()

    while wave:
        next_wave: set[str] = set()
        for tid in wave:
            if tid in visited:
                continue
            visited.add(tid)
            result.append(id_map[tid])
            for dep_tid in dependents.get(tid, []):
                if dep_tid in visited:
                    continue
                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    next_wave.add(dep_tid)
        wave = sorted(next_wave, key=_wave_key)

    # 处理环形依赖（防御性兜底）
    for t in tasks:
        if t.get("task_id", "") not in visited:
            result.append(t)

    return result


# ---------------------------------------------------------------------------
# 第五阶段：subtask 展开 + blocker 标记 + execution_plan
# ---------------------------------------------------------------------------

def _char_similarity(a: str, b: str) -> float:
    """字符集相似度：共有字符数 / 较短字符串的字符集大小。中文适用。"""
    sa = set(a.replace(" ", ""))
    sb = set(b.replace(" ", ""))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def flatten_subtasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    将 composite 任务的 subtasks 展开为独立任务节点。
    语义去重（阈值 0.5）：若 subtask 与已有任务字符集相似度 >= 0.5，跳过展开。
    当 subtask 被跳过时，记录映射关系，后续 subtask 的 depends_on 自动重定向。
    """
    existing_tasks: list[str] = [str(t.get("task", "")).strip() for t in tasks]
    existing_lower: set[str] = {n.lower() for n in existing_tasks}
    new_tasks: list[dict[str, Any]] = list(tasks)
    # dedup_remap: 被跳过的子任务名 -> 语义等价的已有任务名（用于重定向 depends_on）
    dedup_remap: dict[str, str] = {}

    _SIM_THRESHOLD = 0.5

    for t in tasks:
        for sub in t.get("subtasks", []):
            if not isinstance(sub, dict) or not sub.get("task"):
                continue
            sub_name = str(sub["task"]).strip()

            # 1. 精确去重
            if sub_name.lower() in existing_lower:
                dedup_remap[sub_name] = next(
                    (n for n in existing_tasks if n.lower() == sub_name.lower()), sub_name
                )
                continue

            # 2. 语义去重（字符集相似度）
            # 关键：排除父任务自身，防止子任务被映射回父任务造成依赖方向反转
            similar_task: str | None = None
            parent_name = str(t.get("task", ""))
            for existing in existing_tasks:
                if existing == parent_name:
                    continue  # 跳过父任务，防止子任务 → 依赖父任务
                if _char_similarity(sub_name, existing) >= _SIM_THRESHOLD:
                    similar_task = existing
                    break
            if similar_task:
                dedup_remap[sub_name] = similar_task
                continue

            # 3. 重定向 depends_on（若前置 subtask 被去重，指向其等价任务）
            dep_text = sub.get("depends_on")
            if dep_text and dep_text in dedup_remap:
                dep_text = dedup_remap[dep_text]

            existing_tasks.append(sub_name)
            existing_lower.add(sub_name.lower())
            owner_name = sub.get("owner")
            owners = [{"name": owner_name, "role": ""}] if owner_name else []
            new_tasks.append({
                "task": sub_name,
                "task_level": "atomic",
                "needs_decomposition": False,
                "subtasks": [],
                "owners": owners,
                "owner_type": "single" if owners else "unknown",
                "owner_resolution": "person" if owners else "role",
                "deadline": t.get("deadline"),
                "priority": t.get("priority", "medium"),
                "priority_reason": f"来自复合任务「{t.get('task', '')}」的子任务",
                "confidence": round(t.get("confidence", 0.7) * 0.9, 2),
                "is_blocker": False,
                "dependencies": [dep_text] if dep_text else [],
                "evidence": t.get("evidence", ""),
                "from_subtask": True,
                "parent_task": t.get("task", ""),
            })
    return new_tasks


def link_composite_to_subtasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    让 composite 任务依赖其展开后的子任务节点（last child）。
    修正 execution_plan 顺序：composite 排在所有子节点完成之后。
    """
    parent_to_children: dict[str, list[str]] = {}
    for t in tasks:
        if t.get("from_subtask") and t.get("parent_task") and t.get("task_id"):
            parent_to_children.setdefault(t["parent_task"], []).append(t["task_id"])

    for t in tasks:
        if t.get("from_subtask"):
            continue
        children = parent_to_children.get(str(t.get("task", "")), [])
        if not children:
            continue
        existing_deps: set[str] = set(t.get("dependencies", []))
        for cid in children:
            if cid not in existing_deps:
                t.setdefault("dependencies", []).append(cid)
    return tasks


def mark_blockers(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    收紧 blocker 规则，避免"链上所有节点都是 blocker"：
    - 被 >= 2 个任务依赖（真正的扇出节点）→ is_blocker = True
    - 自身无依赖 且 被恰好 1 个任务依赖（关键路径根节点）→ is_blocker = True
    - 其余（链路中间节点）→ is_blocker = False
    """
    dep_count: dict[str, int] = {}
    for t in tasks:
        for d in t.get("dependencies", []):
            dep_count[d] = dep_count.get(d, 0) + 1
    for t in tasks:
        tid = t.get("task_id", "")
        count = dep_count.get(tid, 0)
        has_no_deps = not t.get("dependencies")
        t["is_blocker"] = count >= 2 or (count == 1 and has_no_deps)
    return tasks


def build_execution_plan(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    tasks 已由 sort_tasks_with_dependencies（BFS）按正确拓扑顺序排列，
    直接枚举即可，无需重复遍历（避免环路递归）。
    """
    # 预计算：哪些 task_id 被其他任务依赖
    depended_ids: set[str] = set()
    for t in tasks:
        for d in t.get("dependencies", []):
            depended_ids.add(d)

    return [
        {
            "step": i + 1,
            "task": t["task"],
            "task_id": t["task_id"],
            "is_blocker": bool(t.get("is_blocker", False)),
            "priority": t.get("priority", "medium"),
            # main：在依赖图中（有上游或下游）；parallel：完全独立任务
            "track": "parallel" if (not t.get("dependencies") and t["task_id"] not in depended_ids) else "main",
        }
        for i, t in enumerate(tasks)
        if t.get("task_id")
    ]


# ---------------------------------------------------------------------------
# To-do 生成
# ---------------------------------------------------------------------------

def _todo_item_from_task(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": str(t.get("task", "")),
        "task_id": str(t.get("task_id", "")),
        "deadline": t.get("deadline"),
        "priority": str(t.get("priority", "medium")),
        "priority_reason": str(t.get("priority_reason", "")),
        "task_level": str(t.get("task_level", "atomic")),
        "needs_decomposition": bool(t.get("needs_decomposition", False)),
    }


def generate_todos(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """owners 中每个人都要分到任务；owner_type=unknown 或 owners 为空 -> 放入未分配。"""
    personal: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        item = _todo_item_from_task(t)
        owners = t.get("owners") or []
        otype = str(t.get("owner_type", "unknown"))
        if otype == "unknown" or not owners:
            personal.setdefault(UNASSIGNED, []).append(item)
            continue
        for o in owners:
            name = o.get("name") if isinstance(o, dict) else None
            if not name:
                continue
            personal.setdefault(str(name).strip() or UNASSIGNED, []).append(item)
    return personal


# ---------------------------------------------------------------------------
# Pipeline 入口
# ---------------------------------------------------------------------------

def run_pipeline(
    meeting_text: str,
    participants: list[str] | list[dict[str, Any]],
) -> dict[str, Any]:
    parts = normalize_participants(participants)
    tasks = extract_tasks(meeting_text, parts)
    tasks = assign_roles(tasks, parts)
    for t in tasks:
        normalize_confidence(t)
    # 第五阶段：稳定 task_id -> subtasks 结构化 -> flatten -> 二次 ID/依赖 -> blocker -> 排序 -> 计划
    tasks = assign_task_ids(tasks)
    tasks = link_dependencies(tasks)
    tasks = [normalize_subtasks(t) for t in tasks]
    tasks = flatten_subtasks(tasks)            # 展开 subtask 为独立节点（去重）
    tasks = assign_task_ids(tasks)             # 给展开的子任务分配 ID
    tasks = link_dependencies(tasks)           # 子任务依赖也转为 ID
    tasks = link_composite_to_subtasks(tasks)  # composite 依赖其子节点（修正执行顺序）
    tasks = mark_blockers(tasks)               # 根据依赖图计算 is_blocker
    tasks = sort_tasks_with_dependencies(tasks)
    execution_plan = build_execution_plan(tasks)
    todos = generate_todos(tasks)
    return {"tasks": tasks, "execution_plan": execution_plan, "personal_todos": todos}


# ---------------------------------------------------------------------------
# 本地演示与 schema 校验
# ---------------------------------------------------------------------------

def _demo() -> None:
    import sys
    from pathlib import Path

    def validate_result(result: dict[str, Any]) -> bool:
        tasks = result.get("tasks") or []
        if not isinstance(tasks, list):
            return False
        for t in tasks:
            if not str(t.get("task_id", "")).startswith("TASK-"):
                return False
            if "confidence" not in t:
                return False
            if t.get("owner_resolution") not in ("person", "role"):
                return False
            if not isinstance(t.get("subtasks"), list):
                return False
            if not isinstance(t.get("dependencies"), list):
                return False
            if "is_blocker" not in t:
                return False
            # subtasks 必须全是结构化 dict（不能是字符串）
            for s in t.get("subtasks", []):
                if not isinstance(s, dict):
                    return False
                if "task" not in s:
                    return False
            c = t.get("confidence")
            if not isinstance(c, (int, float)) or not (0.0 <= c <= 1.0):
                return False
        if not isinstance(result.get("execution_plan"), list):
            return False
        try:
            json.loads(json.dumps(result, ensure_ascii=False))
        except Exception:
            return False
        return True

    root = Path(__file__).resolve().parents[3]
    samples = root / "data" / "samples"
    files = sorted(samples.glob("prototype_sample_*.txt"))

    if not files:
        text = "张三在周五前提交 PRD。李四负责后端接口，下周三联调。"
        parts: list[str | dict[str, str]] = [{"name": "张三", "role": "产品经理"}, {"name": "李四", "role": "后端开发"}]
        result = run_pipeline(text, parts)
        ok = validate_result(result)
        if not ok:
            print("Schema validation FAILED (inline sample)", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    for i, fp in enumerate(files, 1):
        print(f"\n{'=' * 60}\n样例 {i}: {fp.name}\n{'=' * 60}")
        text = fp.read_text(encoding="utf-8")
        parts = [
            {"name": "张三", "role": "产品经理"},
            {"name": "李四", "role": "后端开发"},
            {"name": "王五", "role": "测试工程师"},
        ]
        result = run_pipeline(text, parts)
        ok = validate_result(result)
        status = "OK" if ok else "FAILED"
        print(f"[Schema {status}] {fp.name}", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n提示: 设置 OPENAI_API_KEY 后抽取质量更佳；未设置时使用启发式 fallback。", file=sys.stderr)


if __name__ == "__main__":
    _demo()
    