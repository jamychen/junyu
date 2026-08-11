# -*- coding: utf-8 -*-
"""
高一学习助手 —— 理科方向（语数英 + 物化生）
基于 wxPython 的桌面学习程序：章节导航、知识点 / 考点 / 例题查看、随堂笔记、搜索与学习进度。
"""
import os
import sys
import wx
import wx.html

from data_manager import DataManager, escape_html

# 程序所在目录（便于定位 data 文件夹）
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")

# 科目主题色
SUBJECT_COLORS = {
    "语文": "#b85450",
    "数学": "#3a76d8",
    "英语": "#6a4ca0",
    "物理": "#2e8b57",
    "化学": "#c0392b",
    "生物": "#16a085",
}


class NotesPanel(wx.Panel):
    """笔记面板：左侧笔记列表 + 右侧编辑器，每章节独立保存。"""

    def __init__(self, parent, dm):
        super().__init__(parent)
        self.dm = dm
        self.chapter_id = None
        self.current_note_id = None

        top = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_new = wx.Button(self, label="＋ 新建笔记")
        self.btn_save = wx.Button(self, label="💾 保存")
        self.btn_del = wx.Button(self, label="🗑 删除")
        self.lbl_hint = wx.StaticText(self, label="（请先在左侧选择章节）")
        top.Add(self.btn_new, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        top.Add(self.btn_save, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        top.Add(self.btn_del, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        top.Add(self.lbl_hint, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)

        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        # 左：笔记列表
        left = wx.Panel(splitter)
        left_sz = wx.BoxSizer(wx.VERTICAL)
        left_sz.Add(wx.StaticText(left, label="我的笔记列表"), 0, wx.ALL, 4)
        self.note_list = wx.ListCtrl(left, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
        self.note_list.InsertColumn(0, "时间", width=120)
        self.note_list.InsertColumn(1, "标题", width=180)
        left_sz.Add(self.note_list, 1, wx.EXPAND | wx.ALL, 4)
        left.SetSizer(left_sz)

        # 右：编辑器
        right = wx.Panel(splitter)
        right_sz = wx.BoxSizer(wx.VERTICAL)
        title_row = wx.BoxSizer(wx.HORIZONTAL)
        title_row.Add(wx.StaticText(right, label="标题："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        self.title_ctrl = wx.TextCtrl(right, style=wx.TE_PROCESS_ENTER)
        title_row.Add(self.title_ctrl, 1, wx.ALL, 4)
        right_sz.Add(title_row, 0, wx.EXPAND)
        right_sz.Add(wx.StaticText(right, label="内容："), 0, wx.LEFT | wx.TOP, 4)
        self.content_ctrl = wx.TextCtrl(right, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_WORDWRAP)
        right_sz.Add(self.content_ctrl, 1, wx.EXPAND | wx.ALL, 4)
        right.SetSizer(right_sz)

        splitter.SplitVertically(left, right, 300)
        splitter.SetMinimumPaneSize(200)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(top, 0, wx.EXPAND)
        sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.btn_new.Bind(wx.EVT_BUTTON, self.on_new)
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_del.Bind(wx.EVT_BUTTON, self.on_delete)
        self.note_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_note)
        self.title_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_save)
        self.set_enabled(False)

    def set_enabled(self, enabled):
        self.btn_new.Enable(enabled)
        self.btn_save.Enable(enabled)
        self.btn_del.Enable(enabled)
        self.title_ctrl.Enable(enabled)
        self.content_ctrl.Enable(enabled)

    def load_chapter(self, chapter_id, chapter_title):
        self.chapter_id = chapter_id
        self.current_note_id = None
        self.lbl_hint.SetLabel(f"当前章节：{chapter_title}")
        self.refresh_list()
        self.title_ctrl.SetValue("")
        self.content_ctrl.SetValue("")
        self.set_enabled(chapter_id is not None)

    def refresh_list(self):
        self.note_list.DeleteAllItems()
        if not self.chapter_id:
            return
        notes = self.dm.get_notes(self.chapter_id)
        # 倒序显示（最新在上）
        for idx, note in enumerate(reversed(notes)):
            pos = self.note_list.InsertItem(idx, note.get("time", ""))
            self.note_list.SetItem(pos, 1, note.get("title", ""))
            self.note_list.SetItemData(pos, idx)
        # 记录倒序索引映射
        self._order = list(reversed(notes))

    def on_new(self, event):
        if not self.chapter_id:
            return
        self.current_note_id = None
        self.title_ctrl.SetValue("")
        self.content_ctrl.SetValue("")
        self.title_ctrl.SetFocus()

    def on_save(self, event):
        if not self.chapter_id:
            return
        title = self.title_ctrl.GetValue().strip()
        content = self.content_ctrl.GetValue()
        if not title and not content.strip():
            wx.MessageBox("请输入笔记标题或内容后再保存。", "提示", wx.ICON_INFORMATION)
            return
        if self.current_note_id:
            self.dm.update_note(self.chapter_id, self.current_note_id, title, content)
        else:
            note = self.dm.add_note(self.chapter_id, title, content)
            self.current_note_id = note["id"]
        self.refresh_list()
        # 重新选中刚保存的笔记
        for i in range(self.note_list.GetItemCount()):
            if self._order and self._order[i].get("id") == self.current_note_id:
                self.note_list.Select(i, True)
                break

    def on_delete(self, event):
        if not self.chapter_id or not self.current_note_id:
            return
        if wx.MessageBox("确定删除当前笔记？", "确认", wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
            return
        self.dm.delete_note(self.chapter_id, self.current_note_id)
        self.current_note_id = None
        self.title_ctrl.SetValue("")
        self.content_ctrl.SetValue("")
        self.refresh_list()

    def on_select_note(self, event):
        if not getattr(self, "_order", None):
            return
        idx = event.GetIndex()
        if idx < 0 or idx >= len(self._order):
            return
        note = self._order[idx]
        self.current_note_id = note.get("id")
        self.title_ctrl.SetValue(note.get("title", ""))
        self.content_ctrl.SetValue(note.get("content", ""))


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="高一学习助手 · 佛山理科方向", size=(1180, 760))
        self.dm = DataManager(DATA_DIR)
        self.font_size = 14
        self.tree_item_chapter = {}   # tree item id -> chapter_id
        self.chapter_item_map = {}    # chapter_id -> tree item
        self.current_chapter_id = None

        self._build_menu()
        self._build_ui()
        self._populate_tree()
        self._show_welcome()
        self._update_progress()
        self.Centre()
        self.Show()

    # ---------------- 菜单 ----------------
    def _build_menu(self):
        mb = wx.MenuBar()
        m_file = wx.Menu()
        self.id_export = wx.NewIdRef()
        self.id_import = wx.NewIdRef()
        m_file.Append(self.id_export, "导出笔记…\tCtrl+E")
        m_file.Append(self.id_import, "导入笔记…\tCtrl+I")
        m_file.AppendSeparator()
        m_file.Append(wx.ID_EXIT, "退出\tCtrl+Q")
        mb.Append(m_file, "文件")

        m_view = wx.Menu()
        self.mi_font_inc = m_view.Append(wx.ID_ANY, "放大字体\tCtrl+=")
        self.mi_font_dec = m_view.Append(wx.ID_ANY, "缩小字体\tCtrl+-")
        m_view.AppendSeparator()
        self.mi_mark = m_view.Append(wx.ID_ANY, "标记/取消 已学习\tCtrl+Space")
        mb.Append(m_view, "视图")

        m_help = wx.Menu()
        m_help.Append(wx.ID_ABOUT, "关于…")
        mb.Append(m_help, "帮助")

        self.SetMenuBar(mb)

        self.Bind(wx.EVT_MENU, self.on_export_notes, id=self.id_export)
        self.Bind(wx.EVT_MENU, self.on_import_notes, id=self.id_import)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.on_font_inc, id=self.mi_font_inc.GetId())
        self.Bind(wx.EVT_MENU, self.on_font_dec, id=self.mi_font_dec.GetId())
        self.Bind(wx.EVT_MENU, self.on_toggle_mark, id=self.mi_mark.GetId())
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)

    # ---------------- 界面 ----------------
    def _build_ui(self):
        # 工具栏
        tb = self.CreateToolBar(style=wx.TB_HORIZONTAL | wx.TB_TEXT | wx.TB_NODIVIDER)
        tb.AddStretchableSpace()
        tb.AddControl(wx.StaticText(tb, label="搜索："))
        self.search_ctrl = wx.TextCtrl(tb, size=(220, -1), style=wx.TE_PROCESS_ENTER)
        tb.AddControl(self.search_ctrl)
        self.btn_search = wx.Button(tb, label="搜索")
        tb.AddControl(self.btn_search)
        tb.AddStretchableSpace()
        self.progress_lbl = wx.StaticText(tb, label="学习进度：0/0")
        tb.AddControl(self.progress_lbl)
        tb.AddStretchableSpace()
        tb.Realize()
        self.btn_search.Bind(wx.EVT_BUTTON, self.on_search)
        self.search_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_search)

        # 主体：左右分栏
        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(240)

        # 左侧导航树
        left = wx.Panel(splitter)
        left_sz = wx.BoxSizer(wx.VERTICAL)
        left_sz.Add(wx.StaticText(left, label="📚 科目 · 章节"), 0, wx.ALL, 6)
        self.tree = wx.TreeCtrl(left, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.BORDER_SUNKEN)
        self.root = self.tree.AddRoot("全部")
        left_sz.Add(self.tree, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        left.SetSizer(left_sz)

        # 右侧内容区
        right = wx.Panel(splitter)
        right_sz = wx.BoxSizer(wx.VERTICAL)

        # 章节标题栏
        title_bg = wx.Panel(right)
        title_bg.SetBackgroundColour(wx.Colour(245, 247, 250))
        self.title_bar = wx.StaticText(title_bg, label="", style=wx.ST_NO_AUTORESIZE)
        self.title_bar.SetFont(wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        tb_sz = wx.BoxSizer(wx.HORIZONTAL)
        tb_sz.Add(self.title_bar, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        self.btn_mark = wx.Button(title_bg, label="标记已学习")
        tb_sz.Add(self.btn_mark, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 6)
        title_bg.SetSizer(tb_sz)
        right_sz.Add(title_bg, 0, wx.EXPAND)

        # 标签页
        self.nb = wx.Notebook(right)
        self.html_knowledge = wx.html.HtmlWindow(self.nb)
        self.html_exam = wx.html.HtmlWindow(self.nb)
        self.html_examples = wx.html.HtmlWindow(self.nb)
        self.notes_panel = NotesPanel(self.nb, self.dm)
        self.nb.AddPage(self.html_knowledge, "知识点")
        self.nb.AddPage(self.html_exam, "考点精析")
        self.nb.AddPage(self.html_examples, "典型例题")
        self.nb.AddPage(self.notes_panel, "我的笔记")
        self._apply_html_fonts()
        right_sz.Add(self.nb, 1, wx.EXPAND | wx.ALL, 2)

        # 状态栏
        right.SetSizer(right_sz)
        splitter.SplitVertically(left, right, 300)
        self.CreateStatusBar(2)
        self.SetStatusWidths([-1, 200])

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_select)
        self.btn_mark.Bind(wx.EVT_BUTTON, self.on_toggle_mark)
        self.nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)

    def _apply_html_fonts(self):
        for hw in (self.html_knowledge, self.html_exam, self.html_examples):
            hw.SetStandardFonts(self.font_size, "Microsoft YaHei", "Consolas")

    # ---------------- 导航树 ----------------
    def _populate_tree(self):
        self.tree.DeleteChildren(self.root)
        self.tree_item_chapter = {}
        self.chapter_item_map = {}
        for subj in self.dm.get_subjects():
            sname = subj.get("subject", "?")
            if subj.get("_missing"):
                snode = self.tree.AppendItem(self.root, f"{sname}（待补充）")
                self.tree.SetItemTextColour(snode, wx.Colour(180, 180, 180))
                continue
            color = SUBJECT_COLORS.get(sname, "#333333")
            snode = self.tree.AppendItem(self.root, sname)
            self.tree.SetItemTextColour(snode, wx.Colour(color))
            self.tree.SetItemBold(snode, True)
            for book in subj.get("books", []):
                bnode = self.tree.AppendItem(snode, book.get("name", ""))
                self.tree.SetItemTextColour(bnode, wx.Colour(90, 90, 90))
                for ch in book.get("chapters", []):
                    cnode = self.tree.AppendItem(bnode, ch.get("title", ""))
                    self.tree_item_chapter[cnode] = ch["id"]
                    self.chapter_item_map[ch["id"]] = cnode
                    self._style_chapter_node(ch["id"])
            self.tree.Expand(snode)

    def _style_chapter_node(self, chapter_id):
        node = self.chapter_item_map.get(chapter_id)
        if node is None:
            return
        if self.dm.is_studied(chapter_id):
            self.tree.SetItemTextColour(node, wx.Colour(46, 160, 67))
            self.tree.SetItemBold(node, True)
        else:
            self.tree.SetItemTextColour(node, wx.BLACK)
            self.tree.SetItemBold(node, False)

    # ---------------- 事件 ----------------
    def on_tree_select(self, event):
        item = event.GetItem()
        chapter_id = self.tree_item_chapter.get(item)
        if chapter_id:
            self.load_chapter(chapter_id)
        event.Skip()

    def load_chapter(self, chapter_id):
        chapter = self.dm.get_chapter(chapter_id)
        if not chapter:
            return
        self.current_chapter_id = chapter_id
        subj, book, title = self.dm.get_location(chapter_id)
        self.title_bar.SetLabel(f"{subj} · {book} · {title}")
        self.html_knowledge.SetPage(self.dm.render_knowledge(chapter))
        self.html_exam.SetPage(self.dm.render_exam_points(chapter))
        self.html_examples.SetPage(self.dm.render_examples(chapter))
        self.notes_panel.load_chapter(chapter_id, title)
        self._sync_mark_button()
        self.SetStatusText(f"{subj} / {book} / {title}", 0)

    def _sync_mark_button(self):
        if self.current_chapter_id and self.dm.is_studied(self.current_chapter_id):
            self.btn_mark.SetLabel("取消已学习")
        else:
            self.btn_mark.SetLabel("标记已学习")

    def on_toggle_mark(self, event):
        if not self.current_chapter_id:
            wx.MessageBox("请先选择一个章节。", "提示", wx.ICON_INFORMATION)
            return
        cur = self.dm.is_studied(self.current_chapter_id)
        self.dm.set_studied(self.current_chapter_id, not cur)
        self._style_chapter_node(self.current_chapter_id)
        self._sync_mark_button()
        self._update_progress()

    def on_tab_changed(self, event):
        event.Skip()

    def _update_progress(self):
        total = self.dm.total_chapters()
        done = self.dm.studied_count()
        self.progress_lbl.SetLabel(f"学习进度：{done}/{total}")
        self.SetStatusText(f"已学习 {done} / {total} 章节", 1)

    def _show_welcome(self):
        welcome = (
            "<html><body><h2>欢迎使用 高一学习助手</h2>"
            "<p>本程序收录高一理科方向（语文、数学、英语、物理、化学、生物）各章节的"
            "<b>关键知识点</b>、<b>考点精析</b>与<b>典型例题</b>。</p>"
            "<p>使用方法：</p>"
            "<ul>"
            "<li>在左侧导航树中选择「科目 → 册 → 章节」即可查看内容；</li>"
            "<li>切换「知识点 / 考点精析 / 典型例题」标签页浏览；</li>"
            "<li>在「我的笔记」标签页可像在书本上一样为每个章节记录笔记；</li>"
            "<li>顶部搜索框可跨章节检索知识点与考点；</li>"
            "<li>阅读完成后点击「标记已学习」记录进度。</li>"
            "</ul>"
            "<p><font color='#888888'>提示：Ctrl+= 放大字体，Ctrl+- 缩小字体。</font></p>"
            "</body></html>"
        )
        self.html_knowledge.SetPage(welcome)
        self.html_exam.SetPage("<html><body><p><font color='#999'>请先在左侧选择章节。</font></p></body></html>")
        self.html_examples.SetPage("<html><body><p><font color='#999'>请先在左侧选择章节。</font></p></body></html>")

    # ---------------- 搜索 ----------------
    def on_search(self, event):
        kw = self.search_ctrl.GetValue().strip()
        if not kw:
            wx.MessageBox("请输入搜索关键词。", "提示", wx.ICON_INFORMATION)
            return
        results = self.dm.search(kw)
        if not results:
            wx.MessageBox(f"未找到与「{kw}」相关的内容。", "搜索结果", wx.ICON_INFORMATION)
            return
        dlg = wx.SingleChoiceDialog(
            self, f"找到 {len(results)} 个相关章节，请选择：", f"搜索：{kw}",
            [f"{r['subject']} · {r['book']} · {r['chapter']}" for r in results]
        )
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetSelection()
            ch_id = results[sel]["chapter_id"]
            node = self.chapter_item_map.get(ch_id)
            if node is not None:
                self.tree.SelectItem(node)
                self.tree.EnsureVisible(node)
        dlg.Destroy()

    # ---------------- 字体 ----------------
    def on_font_inc(self, event):
        self.font_size = min(self.font_size + 1, 28)
        self._apply_html_fonts()
        self._reload_html()

    def on_font_dec(self, event):
        self.font_size = max(self.font_size - 1, 9)
        self._apply_html_fonts()
        self._reload_html()

    def _reload_html(self):
        if self.current_chapter_id:
            chapter = self.dm.get_chapter(self.current_chapter_id)
            if chapter:
                self.html_knowledge.SetPage(self.dm.render_knowledge(chapter))
                self.html_exam.SetPage(self.dm.render_exam_points(chapter))
                self.html_examples.SetPage(self.dm.render_examples(chapter))

    # ---------------- 笔记导入导出 ----------------
    def on_export_notes(self, event):
        if not any(self.dm.notes.values()):
            wx.MessageBox("当前没有任何笔记可导出。", "提示", wx.ICON_INFORMATION)
            return
        dlg = wx.FileDialog(self, "导出笔记", defaultDir=os.path.expanduser("~"),
                            defaultFile="我的笔记.json", wildcard="JSON 文件 (*.json)|*.json",
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            import json
            with open(dlg.GetPath(), "w", encoding="utf-8") as f:
                json.dump(self.dm.notes, f, ensure_ascii=False, indent=2)
            wx.MessageBox("笔记已导出。", "完成", wx.ICON_INFORMATION)
        dlg.Destroy()

    def on_import_notes(self, event):
        dlg = wx.FileDialog(self, "导入笔记", defaultDir=os.path.expanduser("~"),
                            wildcard="JSON 文件 (*.json)|*.json", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            import json
            try:
                with open(dlg.GetPath(), "r", encoding="utf-8") as f:
                    incoming = json.load(f)
                for cid, notes in incoming.items():
                    self.dm.notes.setdefault(cid, []).extend(notes)
                self.dm.save_notes()
                wx.MessageBox("笔记已导入并合并。", "完成", wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"导入失败：{e}", "错误", wx.ICON_ERROR)
        dlg.Destroy()

    # ---------------- 关于 ----------------
    def on_about(self, event):
        info = wx.adv.AboutDialogInfo() if hasattr(wx, "adv") else None
        if info:
            info.SetName("高一学习助手")
            info.SetVersion("1.0")
            info.SetDescription("面向高一理科方向（语数英 + 物化生）的章节学习与笔记程序。\n内容依据人教版新教材（广东高考 3+1+2 模式）整理。")
            info.SetCopyright("© 2026")
            wx.adv.AboutBox(info)
        else:
            wx.MessageBox("高一学习助手 v1.0\n面向高一理科方向的学习程序。", "关于", wx.ICON_INFORMATION)


def main():
    app = wx.App(False)
    # 高 DPI 适配
    try:
        app.SetTopWindow(MainFrame())
    except Exception as e:
        wx.MessageBox(f"程序启动失败：{e}", "错误", wx.ICON_ERROR)
        raise
    app.MainLoop()


if __name__ == "__main__":
    main()
