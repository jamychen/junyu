# -*- coding: utf-8 -*-
"""
数据管理模块
负责加载各科内容、笔记与学习进度，并提供搜索与 HTML 渲染。
"""
import json
import os
import uuid
from datetime import datetime


# 六科对应的内容文件（理科方向：语数英 + 物化生）
SUBJECT_FILES = [
    ("语文", "语文.json"),
    ("数学", "数学.json"),
    ("英语", "英语.json"),
    ("物理", "物理.json"),
    ("化学", "化学.json"),
    ("生物", "生物.json"),
]


def escape_html(text):
    """转义 HTML 特殊字符。"""
    if text is None:
        return ""
    text = str(text)
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>"))


class DataManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.subjects = []          # list[dict] 按固定顺序的科目数据
        self._chapter_map = {}      # chapter_id -> (subject, book, chapter)
        self.notes = {}             # chapter_id -> [note, ...]
        self.state = {}             # chapter_id -> {"studied": bool}
        self.notes_path = os.path.join(data_dir, "notes.json")
        self.state_path = os.path.join(data_dir, "progress.json")
        self.load_content()
        self.load_notes()
        self.load_state()

    # ---------------- 内容加载 ----------------
    def load_content(self):
        self.subjects = []
        self._chapter_map = {}
        for subject, fname in SUBJECT_FILES:
            path = os.path.join(self.data_dir, fname)
            if not os.path.exists(path):
                # 内容文件缺失时仍保留科目占位，便于后续补充
                placeholder = {"subject": subject, "books": [], "_missing": True}
                self.subjects.append(placeholder)
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[警告] 加载 {fname} 失败: {e}")
                self.subjects.append({"subject": subject, "books": [], "_error": True})
                continue
            data.setdefault("subject", subject)
            self.subjects.append(data)
            for book in data.get("books", []):
                for ch in book.get("chapters", []):
                    if not ch.get("id"):
                        ch["id"] = f"{subject}_{book.get('name', '')}_{ch.get('title', '')}"
                    self._chapter_map[ch["id"]] = (data, book, ch)

    def get_subjects(self):
        return self.subjects

    def get_chapter(self, chapter_id):
        item = self._chapter_map.get(chapter_id)
        return item[2] if item else None

    def get_location(self, chapter_id):
        """返回 (科目名, 册名, 章节标题)。"""
        item = self._chapter_map.get(chapter_id)
        if not item:
            return ("", "", "")
        subj, book, ch = item
        return (subj.get("subject", ""), book.get("name", ""), ch.get("title", ""))

    def all_chapters(self):
        for subj in self.subjects:
            for book in subj.get("books", []):
                for ch in book.get("chapters", []):
                    yield subj, book, ch

    def total_chapters(self):
        return sum(1 for _ in self.all_chapters())

    def studied_count(self):
        return sum(1 for cid in self._chapter_map if self.is_studied(cid))

    # ---------------- 笔记 ----------------
    def load_notes(self):
        self.notes = {}
        if os.path.exists(self.notes_path):
            try:
                with open(self.notes_path, "r", encoding="utf-8") as f:
                    self.notes = json.load(f)
            except Exception:
                self.notes = {}

    def save_notes(self):
        try:
            with open(self.notes_path, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[警告] 保存笔记失败: {e}")
            return False

    def get_notes(self, chapter_id):
        return self.notes.get(chapter_id, [])

    def add_note(self, chapter_id, title, content):
        note = {
            "id": uuid.uuid4().hex[:12],
            "title": (title or "未命名笔记").strip() or "未命名笔记",
            "content": content or "",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.notes.setdefault(chapter_id, []).append(note)
        self.save_notes()
        return note

    def update_note(self, chapter_id, note_id, title, content):
        for note in self.notes.get(chapter_id, []):
            if note["id"] == note_id:
                if title is not None:
                    note["title"] = title.strip() or "未命名笔记"
                if content is not None:
                    note["content"] = content
                note["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.save_notes()
                return True
        return False

    def delete_note(self, chapter_id, note_id):
        lst = self.notes.get(chapter_id, [])
        self.notes[chapter_id] = [n for n in lst if n["id"] != note_id]
        self.save_notes()

    # ---------------- 学习进度 ----------------
    def load_state(self):
        self.state = {}
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception:
                self.state = {}

    def save_state(self):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def is_studied(self, chapter_id):
        return self.state.get(chapter_id, {}).get("studied", False)

    def set_studied(self, chapter_id, studied):
        self.state.setdefault(chapter_id, {})["studied"] = bool(studied)
        self.save_state()

    # ---------------- 搜索 ----------------
    def search(self, keyword):
        kw = keyword.strip().lower()
        if not kw:
            return []
        results = []
        for subj, book, ch in self.all_chapters():
            parts = [ch.get("title", ""), ch.get("summary", "")]
            for kp in ch.get("knowledge", []):
                parts.append(kp.get("title", "") + " " + kp.get("content", ""))
            for ep in ch.get("exam_points", []):
                parts.append(ep.get("title", "") + " " + ep.get("content", ""))
            for ex in ch.get("examples", []):
                parts.append(ex.get("question", "") + " " + (ex.get("analysis") or ex.get("分析", "")) + " " + (ex.get("answer") or ex.get("答案", "")))
            haystack = " ".join(parts).lower()
            if kw in haystack:
                results.append({
                    "subject": subj.get("subject", ""),
                    "book": book.get("name", ""),
                    "chapter": ch.get("title", ""),
                    "chapter_id": ch["id"],
                })
        return results

    # ---------------- HTML 渲染 ----------------
    def render_knowledge(self, chapter):
        rows = ['<html><body>']
        rows.append(f'<h2>{escape_html(chapter.get("title", ""))}</h2>')
        if chapter.get("summary"):
            rows.append(f'<p><font color="#888888"><i>{escape_html(chapter["summary"])}</i></font></p>')
        rows.append('<hr noshade size="1">')
        rows.append('<h3>一、关键知识点</h3>')
        kps = chapter.get("knowledge", [])
        if not kps:
            rows.append('<p><font color="#999999">暂无内容</font></p>')
        for i, kp in enumerate(kps, 1):
            rows.append(f'<p><b><font color="#1a73e8">{i}. {escape_html(kp.get("title", ""))}</font></b></p>')
            rows.append(f'<p>{escape_html(kp.get("content", ""))}</p>')
        rows.append('</body></html>')
        return "".join(rows)

    def render_exam_points(self, chapter):
        rows = ['<html><body>']
        rows.append(f'<h3>二、考点精析 — {escape_html(chapter.get("title", ""))}</h3>')
        eps = chapter.get("exam_points", [])
        if not eps:
            rows.append('<p><font color="#999999">暂无内容</font></p>')
        for i, ep in enumerate(eps, 1):
            rows.append(f'<p><b><font color="#d33">{i}. {escape_html(ep.get("title", ""))}</font></b></p>')
            rows.append(f'<p>{escape_html(ep.get("content", ""))}</p>')
        rows.append('</body></html>')
        return "".join(rows)

    def render_examples(self, chapter):
        rows = ['<html><body>']
        rows.append(f'<h3>三、典型例题 — {escape_html(chapter.get("title", ""))}</h3>')
        exs = chapter.get("examples", [])
        if not exs:
            rows.append('<p><font color="#999999">暂无内容</font></p>')
        for i, ex in enumerate(exs, 1):
            rows.append(f'<p><b>例 {i}　{escape_html(ex.get("title", ""))}</b></p>')
            rows.append(f'<p><font color="#0a7d28"><b>【题目】</b></font>{escape_html(ex.get("question", ""))}</p>')
            if ex.get("analysis") or ex.get("分析"):
                rows.append(f'<p><font color="#b26a00"><b>【分析】</b></font>{escape_html(ex.get("analysis") or ex.get("分析", ""))}</p>')
            if ex.get("answer") or ex.get("答案"):
                rows.append(f'<p><font color="#1a73e8"><b>【解答】</b></font>{escape_html(ex.get("answer") or ex.get("答案", ""))}</p>')
            rows.append('<hr noshade size="1">')
        rows.append('</body></html>')
        return "".join(rows)
