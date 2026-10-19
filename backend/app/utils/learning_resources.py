"""
根据面试历史关键词合并「公开学习链接」，补充 AI 返回的 learning_resources。
"""

from __future__ import annotations

from typing import Any, Dict, List

# 与岗位/能力维度相关的精选公开资源（标题 + 可访问 URL）
CURATED_LINKS: List[Dict[str, Any]] = [
    {
        "title": "MDN Web 文档",
        "url": "https://developer.mozilla.org/zh-CN/",
        "topic": "前端与 Web 基础",
        "keywords": ("前端", "html", "css", "javascript", "web", "浏览器"),
    },
    {
        "title": "Vue.js 官方文档",
        "url": "https://cn.vuejs.org/",
        "topic": "Vue 框架",
        "keywords": ("vue", "前端", "组件"),
    },
    {
        "title": "React 官方文档",
        "url": "https://react.dev/",
        "topic": "React",
        "keywords": ("react", "前端", "hooks"),
    },
    {
        "title": "Go 语言官方文档",
        "url": "https://go.dev/doc/",
        "topic": "Go",
        "keywords": ("go", "golang", "后端"),
    },
    {
        "title": "Python 官方教程",
        "url": "https://docs.python.org/zh-cn/3/tutorial/",
        "topic": "Python",
        "keywords": ("python", "后端", "脚本"),
    },
    {
        "title": "Kubernetes 官方文档",
        "url": "https://kubernetes.io/zh-cn/docs/home/",
        "topic": "云原生 / K8s",
        "keywords": ("k8s", "kubernetes", "容器", "运维", "devops"),
    },
    {
        "title": "Redis 官方文档",
        "url": "https://redis.io/docs/",
        "topic": "缓存与 Redis",
        "keywords": ("redis", "缓存", "中间件"),
    },
    {
        "title": "MySQL 8.0 参考手册",
        "url": "https://dev.mysql.com/doc/refman/8.0/en/",
        "topic": "数据库",
        "keywords": ("mysql", "sql", "数据库"),
    },
    {
        "title": "力扣（LeetCode）",
        "url": "https://leetcode.cn/",
        "topic": "算法与数据结构",
        "keywords": ("算法", "数据结构", "leetcode", "刷题", "笔试"),
    },
    {
        "title": "Hello 算法",
        "url": "https://www.hello-algo.com/",
        "topic": "算法可视化",
        "keywords": ("算法", "数据结构", "刷题"),
    },
    {
        "title": "系统设计入门（GitHub）",
        "url": "https://github.com/donnemartin/system-design-primer",
        "topic": "系统设计",
        "keywords": ("系统设计", "高并发", "分布式", "架构"),
    },
    {
        "title": "Linux Kernel 文档",
        "url": "https://docs.kernel.org/",
        "topic": "Linux / 内核与运维",
        "keywords": ("linux", "shell", "运维", "操作系统"),
    },
    {
        "title": "计算机网络（维基）",
        "url": "https://zh.wikipedia.org/wiki/计算机网络",
        "topic": "计算机网络",
        "keywords": ("网络", "tcp", "http", "计网"),
    },
    {
        "title": "维基：沟通",
        "url": "https://zh.wikipedia.org/wiki/%E6%B2%9F%E9%80%9A",
        "topic": "沟通基础",
        "keywords": ("沟通", "表达", "倾听", "反馈", "协作", "职场"),
    },
    {
        "title": "Toastmasters（公众表达与演讲）",
        "url": "https://www.toastmasters.org/",
        "topic": "演讲与结构化表达",
        "keywords": ("演讲", "ppt", "汇报", "紧张", "口才", "表达"),
    },
    {
        "title": "OAuth 2.0 / OpenID Connect 概览",
        "url": "https://oauth.net/2/",
        "topic": "安全与认证",
        "keywords": ("oauth", "安全", "鉴权", "登录"),
    },
]


def _norm(s: str) -> str:
    return s.lower() if s else ""


def pick_curated_links(text: str, limit: int = 8) -> List[Dict[str, str]]:
    """根据薄弱点/岗位描述文本挑选相关链接。"""
    t = _norm(text)
    scored: List[tuple] = []
    for item in CURATED_LINKS:
        score = sum(1 for k in item["keywords"] if k in t)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: -x[0])
    out: List[Dict[str, str]] = []
    for _, item in scored[:limit]:
        out.append(
            {
                "title": item["title"],
                "url": item["url"],
                "topic": item["topic"],
                "reason": "结合你的历史评价关键词推荐补充学习",
            }
        )
    if not out:
        # 通用兜底
        for item in CURATED_LINKS[:4]:
            out.append(
                {
                    "title": item["title"],
                    "url": item["url"],
                    "topic": item["topic"],
                    "reason": "通用计算机基础能力拓展",
                }
            )
    return out


def merge_learning_resources(
    advice: Dict[str, Any],
    weaknesses_blob: str,
    position: str,
    max_items: int = 12,
) -> None:
    """合并 AI 输出与关键词匹配链接，写回 advice['learning_resources']。"""
    ai_list = advice.get("learning_resources")
    if not isinstance(ai_list, list):
        ai_list = []
    seen = set()
    merged: List[Dict[str, str]] = []
    for x in ai_list:
        if not isinstance(x, dict):
            continue
        url = (x.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append(
            {
                "title": str(x.get("title") or "学习资源")[:120],
                "url": url,
                "topic": str(x.get("topic") or "")[:80],
                "reason": str(x.get("reason") or "")[:200],
            }
        )
    blob = f"{weaknesses_blob} {position}"
    for item in pick_curated_links(blob, limit=8):
        if item["url"] not in seen:
            merged.append(item)
            seen.add(item["url"])
        if len(merged) >= max_items:
            break
    advice["learning_resources"] = merged[:max_items]


def ensure_knowledge_graph(advice: Dict[str, Any]) -> None:
    """若模型未返回合法知识图谱，则根据薄弱点生成简易图结构。"""
    kg = advice.get("knowledge_graph")
    if isinstance(kg, dict) and isinstance(kg.get("nodes"), list) and len(kg.get("nodes")) >= 4:
        return
    wps = advice.get("weak_points")
    if not isinstance(wps, list):
        wps = []
    nodes = [{"id": "goal", "label": "面试能力提升", "group": "goal"}]
    edges = []
    for i, wp in enumerate(wps[:10]):
        if not isinstance(wp, dict):
            continue
        dim = (wp.get("dimension") or f"维度{i+1}").strip()[:12]
        nid = f"w{i}"
        nodes.append({"id": nid, "label": dim, "group": "weak"})
        edges.append({"from": "goal", "to": nid, "label": "需加强"})
    # 学习主题卫星节点
    topics = ["系统学习", "刻意练习", "复盘反馈"]
    for j, tlabel in enumerate(topics):
        tid = f"t{j}"
        nodes.append({"id": tid, "label": tlabel, "group": "method"})
        edges.append({"from": "goal", "to": tid, "label": "路径"})
    advice["knowledge_graph"] = {"nodes": nodes, "edges": edges}
