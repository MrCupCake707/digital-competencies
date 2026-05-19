"""
Главное окно приложения.

Это самый большой файл интерфейса. В нем создаются экраны:
обзор, компетенции, тестирование, траектория, граф знаний,
экспорт и администрирование.

Большая часть методов здесь отвечает не за расчеты, а за отображение:
создание кнопок, карточек, таблиц, обработку нажатий и обновление данных на экране.
"""

from __future__ import annotations

import ctypes
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from tkinter import font as tkfont
from typing import Any

from app.core.knowledge_graph import KnowledgeGraph
from app.core.models import Competence, EmployeeProfile, LearningResource, Level, TrajectoryStep
from app.core.trajectory_builder import TrajectoryBuilder
from app.storage.database import ProfileRepository
from app.storage.loaders import load_competences, load_default_profiles, save_competences
from app.utils.exporter import export_csv, export_docx, export_json, export_markdown


LEVEL_HINTS = {
    0: "0 — не владею: компетенция пока не освоена",
    1: "1 — начальный: знаю отдельные понятия",
    2: "2 — базовый: выполняю простые действия",
    3: "3 — уверенный: работаю самостоятельно",
    4: "4 — продвинутый: решаю сложные задачи",
    5: "5 — экспертный: могу обучать других",
}
LEVEL_VALUES = tuple(str(value) for value in range(6))

CATEGORY_COLORS = {
    "базовая": "#6366F1",
    "поиск": "#6366F1",
    "анализ": "#14B8A6",
    "безопасность": "#F97316",
    "коммуникации": "#A855F7",
    "командная": "#A855F7",
    "автоматизация": "#4F46E5",
    "проект": "#4F46E5",
    "документооборот": "#14B8A6",
    "программирование": "#1E1B4B",
    "базы": "#14B8A6",
    "ии": "#A855F7",
    "правовые": "#EF4444",
    "трансформация": "#14B8A6",
    "интеграция": "#4F46E5",
}


class MainWindow:


    # Создаем главное окно, загружаем данные и подготавливаем первый экран приложения.
    def __init__(self) -> None:

        self._enable_high_dpi()
        self.root = tk.Tk()
        self.root.tk.call("tk", "scaling", 1.0)
        self.root.title("Цифровая траектория")
        self.root.geometry("1440x920")
        self.root.minsize(1240, 780)
        self.logo_image: tk.PhotoImage | None = None
        self.logo_small: tk.PhotoImage | None = None
        self._load_app_logo()

        self.colors = {
            "primary": "#4F46E5",
            "primary_dark": "#4338CA",
            "success": "#14B8A6",
            "success_dark": "#0D9488",
            "danger": "#EF4444",
            "workspace": "#F4F6FF",
            "side": "#FFFFFF",
            "card": "#FFFFFF",
            "text": "#1E1B4B",
            "muted": "#64748B",
            "line": "#E2E8F0",
            "hover": "#EEF2FF",
            "warning": "#F97316",
            "graph_line": "#C7D2FE",
            "graph_bg": "#F8FAFF",
            "shadow": "#DDE3F7",
        }
        self.root.configure(bg=self.colors["workspace"])

        self.competences = load_competences()
        self.graph = KnowledgeGraph(self.competences)
        self.builder = TrajectoryBuilder(self.graph)
        self.repository = ProfileRepository()
        user_record = self.repository.authenticate_user_with_role("user", "user")
        if user_record is None:
            user_record = self.repository.authenticate_user_with_role("admin", "admin")
        if user_record is None:
            self.current_profile = load_default_profiles()[0]
            self.current_user_role = "user"
        else:
            self.current_profile, self.current_user_role = user_record
        self.steps: list[TrajectoryStep] = []
        self.results_ready = False

        self.full_name_var = tk.StringVar()
        self.position_var = tk.StringVar()
        self.department_var = tk.StringVar()
        self.direction_var = tk.StringVar(value="Все направления")
        self.status_var = tk.StringVar(value="Готов к работе")
        self.level_vars: dict[str, tk.StringVar] = {}
        self.level_hint_vars: dict[str, tk.StringVar] = {}
        self.node_positions: dict[str, tuple[float, float]] = {}
        self.dragged_node: str | None = None
        self.assessment_index = 0
        self.assessment_title_var = tk.StringVar()
        self.assessment_description_var = tk.StringVar()
        self.assessment_direction_var = tk.StringVar()
        self.assessment_progress_var = tk.StringVar()
        self.assessment_selected_var = tk.StringVar()
        self.assessment_hint_var = tk.StringVar()
        self.explanation_index = 0
        self.explanation_title_var = tk.StringVar()
        self.explanation_description_var = tk.StringVar()
        self.explanation_direction_var = tk.StringVar()
        self.explanation_progress_var = tk.StringVar()
        self.admin_code_var = tk.StringVar()
        self.admin_title_var = tk.StringVar()
        self.admin_direction_var = tk.StringVar()
        self.admin_category_var = tk.StringVar()
        self.admin_difficulty_var = tk.StringVar(value="3")
        self.admin_description_var = tk.StringVar()
        self.admin_target_var = tk.StringVar(value="3")
        self.admin_weight_var = tk.StringVar(value="3")
        self.admin_prerequisites_var = tk.StringVar()
        self.admin_resource_title_var = tk.StringVar()
        self.admin_resource_kind_var = tk.StringVar(value="Курс")
        self.admin_resource_hours_var = tk.StringVar(value="8")
        self.admin_parent_var = tk.StringVar()
        self.admin_child_var = tk.StringVar()

        self.full_name_var.set(self.current_profile.full_name)
        self.position_var.set(self.current_profile.position or ("Администратор" if self.current_user_role == "admin" else "Пользователь"))
        self.department_var.set(self.current_profile.department or ("Администрирование" if self.current_user_role == "admin" else "Пользовательский режим"))

        self._configure_theme()
        self.apply_styles()
        self._build_main_layout()

    def _enable_high_dpi(self) -> None:

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def _load_app_logo(self) -> None:

        logo_path = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
        if not logo_path.exists():
            return
        try:
            self.logo_image = tk.PhotoImage(file=str(logo_path))

            self.logo_small = self.logo_image.subsample(9, 9)
            icon = self.logo_image.subsample(18, 18)
            self.root.iconphoto(True, icon)
            self._icon_ref = icon
        except tk.TclError:
            self.logo_image = None
            self.logo_small = None

    def run(self) -> None:

        self.root.mainloop()




    def _configure_theme(self) -> None:

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

    def apply_styles(self) -> None:

        style = self.style

        self.fonts = {
            "base": ("Segoe UI Variable Text", 15),
            "small": ("Segoe UI Variable Text", 13),
            "section": ("Segoe UI Variable Display Semibold", 20),
            "card": ("Segoe UI Variable Text Semibold", 16),
            "hero": ("Segoe UI Variable Display Semibold", 26),
            "stat": ("Segoe UI Variable Display", 34, "bold"),
            "graph": ("Segoe UI Variable Text Semibold", 13),
        }
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI Variable Text", size=15)
        self.root.option_add("*Font", default_font)
        self.root.option_add("*Menu.background", "#FFFFFF")
        self.root.option_add("*Menu.foreground", self.colors["text"])
        self.root.option_add("*Menu.activeBackground", self.colors["hover"])
        self.root.option_add("*Menu.activeForeground", self.colors["primary"])

        style.configure("TFrame", background=self.colors["workspace"])
        style.configure("Shell.TFrame", background=self.colors["workspace"])
        style.configure("Side.TFrame", background=self.colors["side"])
        style.configure("Card.TFrame", background=self.colors["card"], relief="flat")
        style.configure("Soft.TFrame", background="#F8FAFF", relief="flat")
        style.configure("StatCard.TFrame", background=self.colors["card"], relief="flat")
        style.configure("Top.TFrame", background=self.colors["workspace"])

        style.configure("TLabel", background=self.colors["workspace"], foreground=self.colors["text"], font=self.fonts["base"])
        style.configure("Side.TLabel", background=self.colors["side"], foreground=self.colors["text"], font=self.fonts["base"])
        style.configure("Title.TLabel", background=self.colors["side"], foreground=self.colors["text"], font=("Segoe UI Variable Display Semibold", 25))
        style.configure("Hero.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=self.fonts["hero"])
        style.configure("HeroSub.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=self.fonts["base"])
        style.configure("Section.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=self.fonts["section"])
        style.configure("CardTitle.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=self.fonts["card"])
        style.configure("Muted.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=self.fonts["small"])
        style.configure("SoftMuted.TLabel", background="#F8FAFF", foreground=self.colors["muted"], font=self.fonts["small"])
        style.configure("Status.TLabel", background="#FFFFFF", foreground=self.colors["muted"], font=self.fonts["small"])

        style.configure("TEntry", padding=10, fieldbackground="#FFFFFF", foreground=self.colors["text"], bordercolor=self.colors["line"], lightcolor=self.colors["primary"], darkcolor=self.colors["line"], relief="solid")
        style.map("TEntry", bordercolor=[("focus", self.colors["primary"]), ("active", self.colors["primary"])], lightcolor=[("focus", self.colors["primary"])])
        style.configure("TCombobox", padding=10, fieldbackground="#FFFFFF", foreground=self.colors["text"], bordercolor=self.colors["line"], arrowcolor=self.colors["primary"], relief="solid")
        style.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")], bordercolor=[("focus", self.colors["primary"])])
        style.configure("TSpinbox", padding=10, fieldbackground="#FFFFFF", foreground=self.colors["text"], bordercolor=self.colors["line"], relief="solid")

        style.configure("TButton", padding=(18, 12), font=("Segoe UI Variable Text Semibold", 14), borderwidth=0, focusthickness=0, relief="flat", background="#EEF2FF", foreground=self.colors["text"])
        style.map("TButton", background=[("active", "#E0E7FF"), ("pressed", "#C7D2FE")])
        style.configure("Primary.TButton", background=self.colors["primary"], foreground="#FFFFFF", font=("Segoe UI Variable Text Semibold", 14))
        style.map("Primary.TButton", background=[("active", self.colors["primary_dark"]), ("pressed", "#3730A3")])
        style.configure("Success.TButton", background=self.colors["success"], foreground="#FFFFFF", font=("Segoe UI Variable Text Semibold", 15))
        style.map("Success.TButton", background=[("active", self.colors["success_dark"]), ("pressed", "#0F766E")])
        style.configure("Danger.TButton", background=self.colors["danger"], foreground="#FFFFFF", font=("Segoe UI Variable Text Semibold", 14))
        style.map("Danger.TButton", background=[("active", "#DC2626"), ("pressed", "#B91C1C")])
        style.configure("Nav.TButton", padding=(18, 14), font=("Segoe UI Variable Text Semibold", 15), background="#FFFFFF", foreground=self.colors["text"], anchor="w", relief="flat")
        style.map("Nav.TButton", background=[("active", "#EEF2FF")], foreground=[("active", self.colors["primary"])])
        style.configure("ActiveNav.TButton", padding=(18, 14), font=("Segoe UI Variable Text Semibold", 15), background=self.colors["primary"], foreground="#FFFFFF", anchor="w", relief="flat")
        style.map("ActiveNav.TButton", background=[("active", self.colors["primary_dark"])])

        style.configure("TNotebook", background=self.colors["workspace"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", padding=(0, 0), borderwidth=0)
        style.layout("Hidden.TNotebook.Tab", [])
        style.configure("Hidden.TNotebook", background=self.colors["workspace"], borderwidth=0)

        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", foreground=self.colors["text"], rowheight=48, font=self.fonts["small"], bordercolor=self.colors["line"], relief="flat")
        style.configure("Treeview.Heading", background="#F8FAFF", foreground=self.colors["text"], font=("Segoe UI Variable Text Semibold", 13), padding=10, relief="flat")
        style.map("Treeview", background=[("selected", self.colors["primary"])], foreground=[("selected", "#FFFFFF")])

        style.configure("TLabelframe", background=self.colors["card"], bordercolor=self.colors["line"], relief="solid")
        style.configure("TLabelframe.Label", background=self.colors["card"], foreground=self.colors["primary"], font=("Segoe UI Variable Text Semibold", 14))
        style.configure("Vertical.TScrollbar", background="#FFFFFF", troughcolor=self.colors["workspace"], bordercolor=self.colors["workspace"], arrowcolor=self.colors["primary"])

    def _clear_root(self) -> None:

        for widget in self.root.winfo_children():
            widget.destroy()

    def _card(self, parent: tk.Widget, padding: int | tuple[int, ...] = 16) -> ttk.Frame:

        frame = ttk.Frame(parent, style="Card.TFrame", padding=padding)
        return frame




    def _build_main_layout(self) -> None:

        self._clear_root()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_menu()
        shell = ttk.Frame(self.root, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=0)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        main_area = ttk.Frame(shell, style="Shell.TFrame", padding=(24, 18, 24, 18))
        main_area.grid(row=0, column=1, sticky="nsew")
        main_area.columnconfigure(0, weight=1)
        main_area.rowconfigure(1, weight=1)

        self._build_topbar(main_area)

        self.tabs = ttk.Notebook(main_area, style="Hidden.TNotebook")
        self.tabs.grid(row=1, column=0, sticky="nsew", pady=(18, 0))

        self.home_tab = ttk.Frame(self.tabs, padding=0)
        self.employee_tab = ttk.Frame(self.tabs, padding=0)
        self.competence_tab = ttk.Frame(self.tabs, padding=0)
        self.graph_tab = ttk.Frame(self.tabs, padding=0)
        self.trajectory_tab = ttk.Frame(self.tabs, padding=0)
        self.results_tab = ttk.Frame(self.tabs, padding=0)
        self.admin_tab = ttk.Frame(self.tabs, padding=0)

        self.tabs.add(self.home_tab, text="Обзор")
        self.tabs.add(self.employee_tab, text="Сотрудники")
        self.tabs.add(self.competence_tab, text="Компетенции")
        self.tabs.add(self.trajectory_tab, text="Тестирование")
        self.tabs.add(self.results_tab, text="Траектория")
        self.tabs.add(self.graph_tab, text="Граф компетенций")
        if self.current_user_role == "admin":
            self.tabs.add(self.admin_tab, text="Администрирование")



        self._build_sidebar(shell)

        self.status_bar = ttk.Frame(main_area, style="Card.TFrame", padding=(16, 10))
        self.status_bar.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        ttk.Label(self.status_bar, textvariable=self.status_var, style="Status.TLabel").pack(side="left")

        self._build_home_tab()
        self._build_employee_tab()
        self._build_competence_tab()
        self._build_graph_tab()
        self._build_trajectory_tab()
        self._build_results_tab()
        if self.current_user_role == "admin":
            self._build_admin_tab()
        self._refresh_sidebar_state(0)

    # Создаем левое боковое меню с разделами приложения.
    def _build_sidebar(self, parent: ttk.Frame) -> None:

        self.sidebar = ttk.Frame(parent, style="Side.TFrame", padding=(20, 26, 20, 20), width=340)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(10, weight=1)

        if self.logo_small is not None:
            logo = ttk.Label(self.sidebar, image=self.logo_small, style="Side.TLabel")
            logo.image = self.logo_small
            logo.grid(row=0, column=0, sticky="w", pady=(0, 12))

        ttk.Label(self.sidebar, text="Цифровая\nтраектория", style="Title.TLabel", justify="left").grid(row=1, column=0, sticky="w")
        ttk.Label(self.sidebar, text="Развитие ваших компетенций", style="SoftMuted.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 24))

        self.nav_buttons: list[tk.Frame] = []
        items = [
            ("🏠", "Обзор", self.home_tab),
            ("👥", "Сотрудники", self.employee_tab),
            ("📚", "Компетенции", self.competence_tab),
            ("📝", "Тестирование", self.trajectory_tab),
            ("🗺️", "Траектория", self.results_tab),
            ("🕸️", "Граф компетенций", self.graph_tab),
        ]
        if self.current_user_role == "admin":
            items.append(("⚙️", "Администрирование", self.admin_tab))
        for row, (icon, title, tab) in enumerate(items, start=3):
            index = row - 3
            item = tk.Frame(self.sidebar, bg="#FFFFFF", height=54, cursor="hand2")
            item.grid(row=row, column=0, sticky="ew", pady=5)
            item.grid_propagate(False)
            item.columnconfigure(0, minsize=50)
            item.columnconfigure(1, weight=1)

            icon_label = tk.Label(
                item,
                text=icon,
                bg="#FFFFFF",
                fg=self.colors["text"],
                font=("Segoe UI Emoji", 17),
                anchor="center",
                width=3,
            )
            icon_label.grid(row=0, column=0, sticky="nsew", padx=(12, 0))

            text_label = tk.Label(
                item,
                text=title,
                bg="#FFFFFF",
                fg=self.colors["text"],
                font=("Segoe UI Variable Text Semibold", 15),
                anchor="w",
            )
            text_label.grid(row=0, column=1, sticky="nsew", padx=(8, 14))

            def on_click(event=None, target=tab, active_index=index):
                self._select_sidebar_tab(target, active_index)

            item.bind("<Button-1>", on_click)
            icon_label.bind("<Button-1>", on_click)
            text_label.bind("<Button-1>", on_click)
            item.bind("<Enter>", lambda event, frame=item, i=index: self._hover_sidebar_item(frame, i, True))
            item.bind("<Leave>", lambda event, frame=item, i=index: self._hover_sidebar_item(frame, i, False))
            icon_label.bind("<Enter>", lambda event, frame=item, i=index: self._hover_sidebar_item(frame, i, True))
            icon_label.bind("<Leave>", lambda event, frame=item, i=index: self._hover_sidebar_item(frame, i, False))
            text_label.bind("<Enter>", lambda event, frame=item, i=index: self._hover_sidebar_item(frame, i, True))
            text_label.bind("<Leave>", lambda event, frame=item, i=index: self._hover_sidebar_item(frame, i, False))
            self.nav_buttons.append(item)

        version = ttk.Frame(self.sidebar, style="Soft.TFrame", padding=14)
        version.grid(row=11, column=0, sticky="ew", pady=(20, 0))
        mode_text = "Режим: администратор" if self.current_user_role == "admin" else "Режим: пользователь"
        ttk.Label(version, text=f"ⓘ  Версия 2.2.0\n{mode_text}", style="SoftMuted.TLabel").pack(anchor="w")

    def _paint_sidebar_item(self, item: tk.Frame, active: bool = False, hover: bool = False) -> None:
        bg = self.colors["primary"] if active else (self.colors["hover"] if hover else "#FFFFFF")
        fg = "#FFFFFF" if active else self.colors["text"]
        item.configure(bg=bg)
        for child in item.winfo_children():
            child.configure(bg=bg, fg=fg)

    def _hover_sidebar_item(self, item: tk.Frame, index: int, is_hover: bool) -> None:
        if getattr(self, "active_nav_index", 0) == index:
            return
        self._paint_sidebar_item(item, active=False, hover=is_hover)

    # Создаем верхнюю панель с названием, текущим режимом пользователя и служебными кнопками.
    def _build_topbar(self, parent: ttk.Frame) -> None:

        top = ttk.Frame(parent, style="Top.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        self.top_title_var = tk.StringVar(value="Обзор")
        ttk.Label(top, textvariable=self.top_title_var, font=("Segoe UI Variable Display Semibold", 22), foreground=self.colors["text"], background=self.colors["workspace"]).grid(row=0, column=0, sticky="w")

        profile = ttk.Frame(top, style="Card.TFrame", padding=(18, 10))
        profile.grid(row=0, column=1, sticky="e", padx=(12, 12))
        ttk.Label(profile, text="👤", style="CardTitle.TLabel").grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ttk.Label(profile, textvariable=self.full_name_var, style="CardTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(profile, textvariable=self.position_var, style="Muted.TLabel").grid(row=1, column=1, sticky="w")

        if self.current_user_role == "admin":
            ttk.Button(top, text="👤  Режим пользователя", command=self._switch_to_user_mode).grid(row=0, column=2, sticky="e", padx=(0, 12))
            ttk.Button(top, text="🚪  Закрыть", command=self.root.destroy).grid(row=0, column=3, sticky="e")
        else:
            ttk.Button(top, text="🔐  Администратор", style="Primary.TButton", command=self._open_admin_login_dialog).grid(row=0, column=2, sticky="e", padx=(0, 12))
            ttk.Button(top, text="🚪  Закрыть", command=self.root.destroy).grid(row=0, column=3, sticky="e")


    def _open_admin_login_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Вход администратора")
        dialog.configure(bg=self.colors["workspace"])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, style="Card.TFrame", padding=24)
        frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        frame.columnconfigure(0, weight=1)

        login_var = tk.StringVar(value="admin")
        password_var = tk.StringVar()

        ttk.Label(frame, text="Режим администратора", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Введите учетные данные администратора, чтобы открыть инструменты управления компетенциями.", style="Muted.TLabel", wraplength=420).grid(row=1, column=0, sticky="w", pady=(6, 16))

        ttk.Label(frame, text="Логин", style="CardTitle.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=login_var, font=("Segoe UI", 13)).grid(row=3, column=0, sticky="ew", pady=(5, 12))
        ttk.Label(frame, text="Пароль", style="CardTitle.TLabel").grid(row=4, column=0, sticky="w")
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", font=("Segoe UI", 13))
        password_entry.grid(row=5, column=0, sticky="ew", pady=(5, 18))

        buttons = ttk.Frame(frame, style="Card.TFrame")
        buttons.grid(row=6, column=0, sticky="e")
        ttk.Button(buttons, text="Отмена", command=dialog.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Войти", style="Primary.TButton", command=lambda: self._login_as_admin(login_var.get(), password_var.get(), dialog)).pack(side="left")

        password_entry.focus_set()
        dialog.bind("<Return>", lambda event: self._login_as_admin(login_var.get(), password_var.get(), dialog))

    def _login_as_admin(self, login: str, password: str, dialog: tk.Toplevel) -> None:
        result = self.repository.authenticate_user_with_role(login, password)
        if result is None:
            self._show_message("Ошибка входа", "Неверный логин или пароль администратора.", "error")
            return
        profile, role = result
        if role != "admin":
            self._show_message("Недостаточно прав", "Эта учетная запись не имеет прав администратора.", "warning")
            return
        dialog.destroy()
        self.current_profile = profile
        self.current_user_role = "admin"
        self.full_name_var.set(profile.full_name)
        self.position_var.set(profile.position or "Администратор")
        self.department_var.set(profile.department or "Администрирование")
        self._build_main_layout()
        self._fill_profile(profile)
        self.status_var.set("Включен режим администратора.")

    def _switch_to_user_mode(self) -> None:
        result = self.repository.authenticate_user_with_role("user", "user")
        if result is None:
            self.current_profile = EmployeeProfile("Пользователь", "Сотрудник", "Пользовательский режим", {})
            self.current_user_role = "user"
        else:
            self.current_profile, self.current_user_role = result
        self.full_name_var.set(self.current_profile.full_name)
        self.position_var.set(self.current_profile.position or "Пользователь")
        self.department_var.set(self.current_profile.department or "Пользовательский режим")
        self._build_main_layout()
        self._fill_profile(self.current_profile)
        self.status_var.set("Включен пользовательский режим.")

    def _select_sidebar_tab(self, tab: ttk.Frame, index: int) -> None:

        self.tabs.select(tab)
        self._refresh_sidebar_state(index)

    def _refresh_sidebar_state(self, active_index: int) -> None:

        self.active_nav_index = active_index
        titles = ["Обзор", "Сотрудники", "Компетенции", "Тестирование", "Траектория", "Граф компетенций"]
        if self.current_user_role == "admin":
            titles.append("Администрирование")
        for index, button in enumerate(getattr(self, "nav_buttons", [])):
            if isinstance(button, tk.Frame):
                self._paint_sidebar_item(button, active=index == active_index)
            else:
                button.configure(style="ActiveNav.TButton" if index == active_index else "Nav.TButton")
        if hasattr(self, "top_title_var") and 0 <= active_index < len(titles):
            self.top_title_var.set(titles[active_index])

    def _build_menu(self) -> None:

        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="💾 Сохранить профиль", command=self._save_profile)
        file_menu.add_command(label="📄 Экспорт в Word", command=lambda: self._export("docx"))
        file_menu.add_separator()
        file_menu.add_command(label="👤 Карточка сотрудника", command=lambda: self._select_sidebar_tab(self.employee_tab, 1))
        file_menu.add_command(label="🚪 Выход", command=self.root.destroy)
        menu.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label="🧹 Очистить результаты", command=lambda: self._reset_results("Результаты очищены."))
        edit_menu.add_command(label="0️⃣ Заполнить нулями", command=self._fill_empty_levels_with_zero)
        menu.add_cascade(label="Правка", menu=edit_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="ℹ️ О программе", command=self._show_about)
        menu.add_cascade(label="Справка", menu=help_menu)
        self.root.config(menu=menu)




    # Создает главную страницу с краткой статистикой и текущим прогрессом.
    def _build_home_tab(self) -> None:

        for widget in self.home_tab.winfo_children():
            widget.destroy()
        self.home_tab.columnconfigure(0, weight=1)
        self.home_tab.rowconfigure(2, weight=1)

        hero = self._card(self.home_tab, padding=0)
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=0)

        hero_text = ttk.Frame(hero, style="Card.TFrame", padding=(36, 28, 20, 28))
        hero_text.grid(row=0, column=0, sticky="nsew")
        ttk.Label(hero_text, text=f"Добро пожаловать,\n{self.full_name_var.get() or 'сотрудник'}!", style="Hero.TLabel", justify="left").grid(row=0, column=0, sticky="w")
        ttk.Label(
            hero_text,
            text="Здесь можно оценить цифровые компетенции, пройти тестирование и получить персональную траекторию развития.",
            style="HeroSub.TLabel",
            wraplength=610,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(18, 0))

        hero_art = tk.Canvas(hero, width=430, height=230, bg="#FFFFFF", highlightthickness=0)
        hero_art.grid(row=0, column=1, sticky="e", padx=(0, 18), pady=12)
        self._draw_dashboard_hero_art(hero_art)

        stats = ttk.Frame(self.home_tab, style="Shell.TFrame")
        stats.grid(row=1, column=0, sticky="ew", pady=18)
        for col in range(4):
            stats.columnconfigure(col, weight=1)
        avg = self._average_level_percent()
        self._stat_card(stats, 0, "📋", str(len(self.current_profile.levels) or 0), "Компетенций\nоценено")
        self._stat_card(stats, 1, "📈", f"{avg}%", "Средний уровень\nвладения")
        self._stat_card(stats, 2, "🎯", str(len(self.steps) or 0), "Рекомендаций\nдоступно")
        self._stat_card(stats, 3, "🧭", "1" if self.results_ready else "0", "Активная\nтраектория")

        content = ttk.Frame(self.home_tab, style="Shell.TFrame")
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        progress = self._card(content, padding=28)
        progress.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ttk.Label(progress, text="Ваш прогресс", style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(progress, text=f"{avg}%", bg="#FFFFFF", fg=self.colors["success"], font=("Segoe UI Variable Display", 28, "bold")).grid(row=1, column=0, sticky="w", pady=(24, 20), padx=(0, 18))
        ttk.Label(progress, text="Средний уровень\nкомпетенций", style="CardTitle.TLabel", justify="left").grid(row=1, column=1, sticky="w", pady=(24, 20))
        rows = self._category_progress_rows()
        for idx, (name, value, color) in enumerate(rows, start=2):
            ttk.Label(progress, text=name, style="CardTitle.TLabel").grid(row=idx, column=0, sticky="w", pady=6)
            bar = tk.Canvas(progress, height=12, bg="#FFFFFF", highlightthickness=0)
            bar.grid(row=idx, column=1, sticky="ew", padx=16)
            progress.columnconfigure(1, weight=1)
            self._draw_progress_bar(bar, value, color)
            ttk.Label(progress, text=f"{value}%", style="CardTitle.TLabel").grid(row=idx, column=2, sticky="e")

        next_step = self._card(content, padding=28)
        next_step.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        next_step.columnconfigure(0, weight=1)
        ttk.Label(next_step, text="Следующий шаг", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(next_step, text="🎓", style="CardTitle.TLabel", font=("Segoe UI Emoji", 46)).grid(row=1, column=0, sticky="w", pady=(30, 8))
        ttk.Label(next_step, text="Рекомендуем пройти оценку компетенций", style="CardTitle.TLabel", wraplength=460, justify="left").grid(row=2, column=0, sticky="w")
        ttk.Label(next_step, text="Заполните уровни владения, чтобы система рассчитала индивидуальный путь обучения.", style="Muted.TLabel", wraplength=460, justify="left").grid(row=3, column=0, sticky="w", pady=(12, 28))
        ttk.Button(next_step, text="Перейти к тестированию  →", style="Primary.TButton", command=self._go_to_trajectory).grid(row=4, column=0, sticky="ew")

        note = self._card(self.home_tab, padding=(26, 14))
        note.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        ttk.Label(note, text="ℹ️  Регулярно оценивайте свои компетенции и следуйте рекомендованной траектории для достижения профессиональных целей.", style="HeroSub.TLabel", wraplength=1000).pack(anchor="w")

    def _draw_dashboard_hero_art(self, canvas: tk.Canvas) -> None:

        canvas.create_oval(55, 28, 145, 118, fill="#EEF2FF", outline="#E0E7FF", width=2)
        canvas.create_rectangle(92, 84, 250, 178, fill="#E5E7EB", outline="")
        canvas.create_rectangle(122, 70, 280, 170, fill="#CBD5E1", outline="")
        canvas.create_oval(270, 38, 342, 110, fill="#4F46E5", outline="")
        canvas.create_rectangle(244, 102, 366, 188, fill="#6366F1", outline="")
        canvas.create_oval(292, 58, 316, 82, fill="#FFD7B5", outline="")
        canvas.create_arc(46, 146, 390, 300, start=18, extent=40, style="arc", outline="#14B8A6", width=10)
        canvas.create_line(324, 132, 382, 66, fill="#14B8A6", width=8, arrow="last", arrowshape=(18, 22, 8))
        for x, y, icon in [(48, 54, "▮"), (372, 66, "✓"), (352, 152, "◔")]:
            canvas.create_oval(x-28, y-28, x+28, y+28, fill="#F8FAFF", outline="#E0E7FF", width=2)
            canvas.create_text(x, y, text=icon, fill="#4F46E5", font=("Segoe UI", 20, "bold"))

    def _draw_progress_bar(self, canvas: tk.Canvas, value: int, color: str) -> None:

        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 220)
        canvas.delete("all")
        canvas.create_rectangle(0, 2, width, 10, fill="#EEF2FF", outline="")
        canvas.create_rectangle(0, 2, int(width * value / 100), 10, fill=color, outline="")

    def _average_level_percent(self) -> int:

        levels = [int(v) for v in self.current_profile.levels.values() if 0 <= int(v) <= 5] if self.current_profile.levels else []
        if not levels:
            return 0
        return round(sum(levels) / (len(levels) * 5) * 100)

    def _category_progress_rows(self) -> list[tuple[str, int, str]]:
        groups = [
            ("Базовые навыки", ("базовая", "поиск"), "#6366F1"),
            ("Безопасность", ("безопасность", "правовые"), "#F97316"),
            ("Аналитика данных", ("анализ", "документооборот", "базы", "трансформация"), "#14B8A6"),
            ("Коммуникации", ("коммуникации", "командная"), "#A855F7"),
        ]
        rows: list[tuple[str, int, str]] = []
        for name, markers, color in groups:
            competences = [item for item in self.competences if any(marker in item.direction.lower() for marker in markers)]
            values = []
            for competence in competences:
                raw_value = self.current_profile.levels.get(competence.code)
                try:
                    value = int(raw_value)
                except (TypeError, ValueError):
                    continue
                if 0 <= value <= 5:
                    values.append(value)
            percent = round(sum(values) / (len(competences) * 5) * 100) if competences and values else 0
            rows.append((name, percent, color))
        return rows

    def _refresh_home_tab(self) -> None:
        if hasattr(self, "home_tab"):
            self._build_home_tab()

    def _stat_card(self, parent: ttk.Frame, column: int, icon: str, value: str, caption: str) -> None:

        card = ttk.Frame(parent, style="StatCard.TFrame", padding=24)
        card.grid(row=0, column=column, sticky="nsew", padx=7, ipady=8)
        card.columnconfigure(1, weight=1)
        tk.Label(card, text=icon, bg="#FFFFFF", fg=self.colors["primary"], font=("Segoe UI Emoji", 32)).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 18))
        tk.Label(card, text=value, bg="#FFFFFF", fg=self.colors["text"], font=self.fonts["stat"]).grid(row=0, column=1, sticky="w")
        ttk.Label(card, text=caption, style="Muted.TLabel", justify="left").grid(row=1, column=1, sticky="w")




    def _build_employee_tab(self) -> None:

        self.employee_tab.columnconfigure(0, weight=1)
        self.employee_tab.rowconfigure(1, weight=1)

        header = self._card(self.employee_tab, padding=18)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Карточка сотрудника", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Данные нужны для персонализации отчёта и сохранения профиля в SQLite.", style="Muted.TLabel").grid(row=1, column=0, sticky="w")

        body = self._card(self.employee_tab, padding=22)
        body.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        self._form_entry(body, 0, 0, "ФИО", self.full_name_var)
        self._form_entry(body, 0, 1, "Должность", self.position_var)
        self._form_entry(body, 1, 0, "Подразделение", self.department_var)
        ttk.Button(body, text="💾  Сохранить профиль", style="Primary.TButton", command=self._save_profile).grid(row=2, column=0, sticky="w", pady=(22, 0))
        if self.current_user_role == "admin":
            ttk.Button(body, text="⚙️  Администрирование", command=lambda: self._select_sidebar_tab(self.admin_tab, 6)).grid(row=2, column=1, sticky="w", pady=(22, 0))

    def _form_entry(self, parent: ttk.Frame, row: int, column: int, label: str, variable: tk.StringVar) -> None:

        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 12, 12 if column == 0 else 0), pady=(0, 14))
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=label, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=variable, font=("Segoe UI", 13)).grid(row=1, column=0, sticky="ew", pady=(5, 0))




    def _build_competence_tab(self) -> None:

        for widget in self.competence_tab.winfo_children():
            widget.destroy()
        self.competence_tab.columnconfigure(0, weight=1)
        self.competence_tab.rowconfigure(1, weight=1)

        head = self._card(self.competence_tab, padding=18)
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="Компетенции и направления", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(head, text="Справочник содержит не менее 15 направлений цифрового развития.", style="Muted.TLabel").grid(row=1, column=0, sticky="w")

        table_card = self._card(self.competence_tab, padding=0)
        table_card.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        table_card.rowconfigure(0, weight=1)
        table_card.columnconfigure(0, weight=1)
        columns = ("code", "title", "direction", "difficulty", "target", "weight", "description")
        tree = ttk.Treeview(table_card, columns=columns, show="headings")
        for key, title, width in [
            ("code", "Код", 80),
            ("title", "Компетенция", 230),
            ("direction", "Направление", 260),
            ("difficulty", "Сложность", 110),
            ("target", "Цель", 80),
            ("weight", "Вес", 70),
            ("description", "Пояснение", 520),
        ]:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        tree.tag_configure("odd", background="#FFFFFF")
        tree.tag_configure("even", background="#F8F9FA")
        for index, item in enumerate(self.competences):
            tree.insert("", "end", values=(item.code, item.title, item.direction, item.difficulty, item.target_level, item.weight, item.description), tags=("even" if index % 2 else "odd",))
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_card, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")




    # Создает страницу визуализации графа компетенций.
    def _build_graph_tab(self) -> None:

        for widget in self.graph_tab.winfo_children():
            widget.destroy()
        self.graph_tab.columnconfigure(0, weight=1)
        self.graph_tab.rowconfigure(1, weight=1)

        head = self._card(self.graph_tab, padding=18)
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="Граф знаний", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(head, text="Вершины можно перетаскивать. После формирования траектории рекомендованный путь подсвечивается зелёным.", style="Muted.TLabel").grid(row=1, column=0, sticky="w")

        canvas_card = self._card(self.graph_tab, padding=0)
        canvas_card.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        canvas_card.rowconfigure(0, weight=1)
        canvas_card.columnconfigure(0, weight=1)
        self.graph_canvas = tk.Canvas(canvas_card, bg=self.colors["graph_bg"], highlightthickness=0)
        self.graph_canvas.grid(row=0, column=0, sticky="nsew")
        graph_y_scrollbar = ttk.Scrollbar(canvas_card, orient="vertical", command=self.graph_canvas.yview)
        graph_y_scrollbar.grid(row=0, column=1, sticky="ns")
        graph_x_scrollbar = ttk.Scrollbar(canvas_card, orient="horizontal", command=self.graph_canvas.xview)
        graph_x_scrollbar.grid(row=1, column=0, sticky="ew")
        self.graph_canvas.configure(xscrollcommand=graph_x_scrollbar.set, yscrollcommand=graph_y_scrollbar.set)
        self.graph_canvas.bind("<Configure>", lambda _event: self._draw_graph())
        self.graph_canvas.bind("<ButtonPress-1>", self._start_node_drag)
        self.graph_canvas.bind("<B1-Motion>", self._drag_node)
        self.graph_canvas.bind("<ButtonRelease-1>", lambda _event: setattr(self, "dragged_node", None))
        self.graph_canvas.bind("<ButtonPress-2>", self._start_graph_pan)
        self.graph_canvas.bind("<B2-Motion>", self._move_graph_pan)
        self.graph_canvas.bind("<ButtonPress-3>", self._start_graph_pan)
        self.graph_canvas.bind("<B3-Motion>", self._move_graph_pan)
        self.graph_canvas.bind("<MouseWheel>", self._scroll_graph_mousewheel)

    # Рисует вершины и связи графа компетенций на холсте.
    def _draw_graph(self) -> None:

        if not hasattr(self, "graph_canvas"):
            return
        canvas = self.graph_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1800)
        height = max(canvas.winfo_height(), 1050)
        canvas.configure(scrollregion=(0, 0, width, height))
        self._draw_grid(canvas, width, height)

        if not self.node_positions:
            self.node_positions = self._initial_graph_positions(width, height)

        highlighted_codes = {step.competence.code for step in self.steps} if self.results_ready else set()
        highlighted_edges = {(parent, step.competence.code) for step in self.steps for parent in step.competence.prerequisites}

        for competence in self.competences:
            x2, y2 = self.node_positions.get(competence.code, (80, 80))
            for parent in competence.prerequisites:
                x1, y1 = self.node_positions.get(parent, (80, 80))
                is_highlighted = (parent, competence.code) in highlighted_edges
                color = self.colors["success"] if is_highlighted else self.colors["graph_line"]
                width_line = 3 if is_highlighted else 2
                canvas.create_line(round(x1), round(y1), round(x2), round(y2), fill=color, width=width_line, arrow="last", arrowshape=(12, 14, 5), smooth=False)

        for competence in self.competences:
            self._draw_graph_node(canvas, competence, competence.code in highlighted_codes)

    def _draw_grid(self, canvas: tk.Canvas, width: int, height: int) -> None:

        for x in range(0, width, 32):
            canvas.create_line(x, 0, x, height, fill="#E9EEF5")
        for y in range(0, height, 32):
            canvas.create_line(0, y, width, y, fill="#E9EEF5")

    def _initial_graph_positions(self, width: int, height: int) -> dict[str, tuple[float, float]]:

        levels: dict[str, int] = {}
        for competence in self.graph.topological_sort(set(self.graph.nodes)):
            parents = self.graph.get(competence).prerequisites
            levels[competence] = max((levels.get(parent, 0) + 1 for parent in parents), default=0)
        grouped: dict[int, list[str]] = {}
        for code, level in levels.items():
            grouped.setdefault(level, []).append(code)

        positions: dict[str, tuple[float, float]] = {}
        max_level = max(grouped, default=0)
        x_gap = max(300, (width - 260) / max(max_level + 1, 1))
        for level, codes in grouped.items():
            y_gap = max(140, (height - 190) / max(len(codes), 1))
            for index, code in enumerate(codes):
                positions[code] = (160 + level * x_gap, 115 + index * y_gap)
        return positions

    # Рисует вершины и связи графа компетенций на холсте.
    def _draw_graph_node(self, canvas: tk.Canvas, competence: Competence, highlighted: bool) -> None:

        x, y = self.node_positions.get(competence.code, (80, 80))
        x, y = round(x), round(y)
        width = max(180, min(300, 24 + len(competence.title) * 8))
        height = 58
        color = self._category_color(competence)
        outline = self.colors["warning"] if highlighted else "#FFFFFF"
        outline_width = 3 if highlighted else 1
        self._rounded_rectangle(canvas, x - width / 2 + 3, y - height / 2 + 4, x + width / 2 + 3, y + height / 2 + 4, radius=12, fill="#CAD3DD", outline="", tags=("shadow",))
        node_id = self._rounded_rectangle(canvas, x - width / 2, y - height / 2, x + width / 2, y + height / 2, radius=12, fill=color, outline=outline, width=outline_width, tags=("node", competence.code))
        canvas.create_text(x, y - 11, anchor="center", text=competence.code, fill="#EAF2F8", font=("Segoe UI", 10, "bold"), tags=("node", competence.code))
        canvas.create_text(x, y + 12, anchor="center", text=competence.title[:44], fill="#FFFFFF", font=self.fonts["graph"], width=width - 22, tags=("node", competence.code))
        canvas.tag_bind(node_id, "<Enter>", lambda _event: canvas.config(cursor="hand2"))
        canvas.tag_bind(node_id, "<Leave>", lambda _event: canvas.config(cursor=""))

    def _rounded_rectangle(self, canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: int = 10, **kwargs: Any) -> int:

        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=16, **kwargs)

    def _category_color(self, competence: Competence) -> str:
        search_text = f"{competence.category} {competence.direction}".lower()
        for marker, color in CATEGORY_COLORS.items():
            if marker in search_text:
                return color
        return self.colors["primary"]

    def _start_node_drag(self, event: tk.Event[Any]) -> None:

        item = self.graph_canvas.find_closest(self.graph_canvas.canvasx(event.x), self.graph_canvas.canvasy(event.y))
        if not item:
            return
        tags = self.graph_canvas.gettags(item[0])
        for tag in tags:
            if tag in self.graph.nodes:
                self.dragged_node = tag
                return

    def _drag_node(self, event: tk.Event[Any]) -> None:

        if self.dragged_node is None:
            return
        self.node_positions[self.dragged_node] = (self.graph_canvas.canvasx(event.x), self.graph_canvas.canvasy(event.y))
        self._draw_graph()

    def _start_graph_pan(self, event: tk.Event[Any]) -> None:
        self.graph_canvas.scan_mark(event.x, event.y)

    def _move_graph_pan(self, event: tk.Event[Any]) -> None:
        self.graph_canvas.scan_dragto(event.x, event.y, gain=1)

    def _scroll_graph_mousewheel(self, event: tk.Event[Any]) -> None:
        if event.state & 0x0001:
            self.graph_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.graph_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")




    # Создает страницу формирования персональной траектории обучения.
    def _build_trajectory_tab(self) -> None:

        for widget in self.trajectory_tab.winfo_children():
            widget.destroy()
        self.trajectory_tab.columnconfigure(0, weight=0)
        self.trajectory_tab.columnconfigure(1, weight=1)
        self.trajectory_tab.rowconfigure(0, weight=1)

        left = self._card(self.trajectory_tab, padding=18)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="Формирование траектории", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Сотрудник", style="CardTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(16, 4))
        ttk.Label(left, textvariable=self.full_name_var, style="Muted.TLabel", wraplength=270).grid(row=2, column=0, sticky="w")
        ttk.Label(left, text="Направление", style="CardTitle.TLabel").grid(row=3, column=0, sticky="w", pady=(16, 4))
        directions = ["Все направления", *self.graph.directions()]
        ttk.Combobox(left, textvariable=self.direction_var, values=directions, state="readonly", width=34).grid(row=4, column=0, sticky="ew")
        ttk.Button(left, text="⚙⚡  Сформировать", style="Success.TButton", command=self._rebuild_trajectory).grid(row=5, column=0, sticky="ew", pady=(18, 8))
        ttk.Button(left, text="💾  Сохранить профиль", style="Primary.TButton", command=self._save_profile).grid(row=6, column=0, sticky="ew", pady=4)
        ttk.Button(left, text="📄  Word-отчёт", command=lambda: self._export("docx")).grid(row=7, column=0, sticky="ew", pady=4)

        scale_card = ttk.Frame(left, style="Soft.TFrame", padding=12)
        scale_card.grid(row=8, column=0, sticky="ew", pady=(18, 0))
        ttk.Label(scale_card, text="Шкала 0–5", style="Side.TLabel").pack(anchor="w")
        ttk.Label(scale_card, text="0 — не владею\n1 — начальный\n2 — базовый\n3 — самостоятельный\n4 — продвинутый\n5 — экспертный", style="SoftMuted.TLabel", justify="left").pack(anchor="w", pady=(6, 0))

        right = self._card(self.trajectory_tab, padding=16)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text="Владение компетенциями", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self._build_assessment_panel(right)

    def _build_assessment_panel(self, parent: ttk.Frame) -> None:

        self.assessment_wrapper = ttk.Frame(parent, style="Card.TFrame")
        self.assessment_wrapper.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.assessment_wrapper.rowconfigure(0, weight=1)
        self.assessment_wrapper.columnconfigure(0, weight=1)

        self.level_vars.clear()
        self.level_hint_vars.clear()
        for competence in self.competences:
            self.level_vars[competence.code] = tk.StringVar(value="")
            self.level_hint_vars[competence.code] = tk.StringVar(value="выберите уровень 0–5")

        self._show_assessment_intro()

    def _clear_assessment_wrapper(self) -> None:

        for widget in self.assessment_wrapper.winfo_children():
            widget.destroy()

    def _show_assessment_intro(self) -> None:

        self._clear_assessment_wrapper()
        self.assessment_index = 0

        intro = ttk.Frame(self.assessment_wrapper, style="Card.TFrame", padding=28)
        intro.grid(row=0, column=0, sticky="nsew")
        intro.columnconfigure(0, weight=1)

        ttk.Label(intro, text="Перед оценкой компетенций", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            intro,
            text=(
                "Сначала приложение покажет краткое пояснение по каждой компетенции. "
                "Это нужно, чтобы пользователь понимал, что именно он оценивает. "
                "После ознакомления начнётся пошаговое тестирование: для каждой компетенции нужно выбрать уровень владения от 0 до 5."
            ),
            style="Muted.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 18))

        scale = ttk.Frame(intro, style="Soft.TFrame", padding=18)
        scale.grid(row=2, column=0, sticky="ew")
        scale.columnconfigure(1, weight=1)
        for row, value in enumerate(range(6)):
            ttk.Label(scale, text=str(value), style="Side.TLabel", font=("Segoe UI", 18, "bold")).grid(row=row, column=0, sticky="n", padx=(0, 14), pady=5)
            ttk.Label(scale, text=LEVEL_HINTS[value].split(" — ", 1)[1], style="SoftMuted.TLabel", wraplength=650, justify="left").grid(row=row, column=1, sticky="w", pady=5)

        ttk.Button(intro, text="Ознакомиться с компетенциями  →", style="Success.TButton", command=self._start_competence_explanations).grid(row=3, column=0, sticky="ew", pady=(24, 0))


    def _start_competence_explanations(self) -> None:

        self.explanation_index = 0
        self._show_current_competence_explanation()

    def _show_current_competence_explanation(self) -> None:

        self._clear_assessment_wrapper()
        competence = self.competences[self.explanation_index]
        self.explanation_title_var.set(f"{competence.code} — {competence.title}")
        self.explanation_description_var.set(competence.description)
        self.explanation_direction_var.set(f"Направление: {competence.direction}")
        self.explanation_progress_var.set(f"Ознакомление: {self.explanation_index + 1} из {len(self.competences)}")

        panel = ttk.Frame(self.assessment_wrapper, style="Card.TFrame", padding=28)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)

        ttk.Label(panel, textvariable=self.explanation_progress_var, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(panel, textvariable=self.explanation_title_var, style="Section.TLabel", wraplength=820, justify="left").grid(row=1, column=0, sticky="w", pady=(8, 6))
        ttk.Label(panel, textvariable=self.explanation_direction_var, style="CardTitle.TLabel", wraplength=820).grid(row=2, column=0, sticky="w")

        info = ttk.Frame(panel, style="Soft.TFrame", padding=20)
        info.grid(row=3, column=0, sticky="nsew", pady=(18, 0))
        info.columnconfigure(0, weight=1)
        ttk.Label(info, text="Что означает эта компетенция", style="Side.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(info, textvariable=self.explanation_description_var, style="SoftMuted.TLabel", wraplength=780, justify="left").grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(
            info,
            text=(
                "Перед выставлением балла подумайте, можете ли вы применять эту компетенцию "
                "в реальной рабочей задаче без постоянной помощи коллег."
            ),
            style="SoftMuted.TLabel",
            wraplength=780,
            justify="left",
        ).grid(row=2, column=0, sticky="ew", pady=(14, 0))

        nav = ttk.Frame(panel, style="Card.TFrame")
        nav.grid(row=4, column=0, sticky="ew", pady=(24, 0))
        nav.columnconfigure(1, weight=1)
        ttk.Button(nav, text="← Назад", command=self._explanation_previous).grid(row=0, column=0, sticky="w")
        ttk.Button(nav, text="К шкале", command=self._show_assessment_intro).grid(row=0, column=1, padx=12)
        next_text = "Перейти к тестированию" if self.explanation_index == len(self.competences) - 1 else "Далее →"
        ttk.Button(nav, text=next_text, style="Primary.TButton", command=self._explanation_next).grid(row=0, column=2, sticky="e")

    def _explanation_next(self) -> None:

        if self.explanation_index < len(self.competences) - 1:
            self.explanation_index += 1
            self._show_current_competence_explanation()
        else:
            self.assessment_index = 0
            self._show_current_assessment()

    def _explanation_previous(self) -> None:

        if self.explanation_index > 0:
            self.explanation_index -= 1
            self._show_current_competence_explanation()
        else:
            self._show_assessment_intro()

    def _show_current_assessment(self) -> None:

        self._clear_assessment_wrapper()
        competence = self.competences[self.assessment_index]
        self.assessment_title_var.set(f"{competence.code} — {competence.title}")
        self.assessment_description_var.set(competence.description)
        self.assessment_direction_var.set(f"Направление: {competence.direction}")
        self.assessment_progress_var.set(f"Компетенция {self.assessment_index + 1} из {len(self.competences)}")

        current_value = self.level_vars[competence.code].get().strip()
        self.assessment_selected_var.set(current_value if current_value in LEVEL_VALUES else "")
        self.assessment_hint_var.set(LEVEL_HINTS[int(current_value)] if current_value in LEVEL_VALUES else "Выберите уровень владения по шкале 0–5")

        panel = ttk.Frame(self.assessment_wrapper, style="Card.TFrame", padding=26)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, textvariable=self.assessment_progress_var, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(panel, textvariable=self.assessment_title_var, style="Section.TLabel", wraplength=760, justify="left").grid(row=1, column=0, sticky="w", pady=(8, 6))
        ttk.Label(panel, textvariable=self.assessment_direction_var, style="CardTitle.TLabel", wraplength=760).grid(row=2, column=0, sticky="w")
        ttk.Label(panel, textvariable=self.assessment_description_var, style="Muted.TLabel", wraplength=760, justify="left").grid(row=3, column=0, sticky="ew", pady=(14, 20))

        selector = ttk.Frame(panel, style="Soft.TFrame", padding=18)
        selector.grid(row=4, column=0, sticky="ew")
        selector.columnconfigure(1, weight=1)
        ttk.Label(selector, text="Уровень владения", style="Side.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 16))
        combo = ttk.Combobox(selector, values=list(LEVEL_VALUES), width=8, textvariable=self.assessment_selected_var, state="readonly", font=("Segoe UI", 13))
        combo.grid(row=0, column=1, sticky="w")
        combo.bind("<<ComboboxSelected>>", lambda _e: self._save_current_assessment_value())
        ttk.Label(selector, textvariable=self.assessment_hint_var, style="SoftMuted.TLabel", wraplength=650, justify="left").grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))

        nav = ttk.Frame(panel, style="Card.TFrame")
        nav.grid(row=5, column=0, sticky="ew", pady=(24, 0))
        nav.columnconfigure(1, weight=1)
        ttk.Button(nav, text="← Назад", command=self._assessment_previous).grid(row=0, column=0, sticky="w")
        next_text = "Завершить оценку" if self.assessment_index == len(self.competences) - 1 else "Далее →"
        ttk.Button(nav, text=next_text, style="Primary.TButton", command=self._assessment_next).grid(row=0, column=2, sticky="e")
        ttk.Button(nav, text="Шкала / пояснения", command=self._show_assessment_intro).grid(row=0, column=1, padx=12)

        combo.focus_set()

    def _save_current_assessment_value(self) -> bool:

        competence = self.competences[self.assessment_index]
        value = self.assessment_selected_var.get().strip()
        if value not in LEVEL_VALUES:
            self.assessment_hint_var.set("Выберите уровень от 0 до 5")
            return False
        self.level_vars[competence.code].set(value)
        self.level_hint_vars[competence.code].set(LEVEL_HINTS[int(value)])
        self.assessment_hint_var.set(LEVEL_HINTS[int(value)])
        self.current_profile.levels[competence.code] = int(value)
        self._reset_results("Оценки изменены. После заполнения компетенций снова нажмите «Сформировать».")
        return True

    def _assessment_next(self) -> None:

        if not self._save_current_assessment_value():
            self._show_message("Выберите уровень", "Укажите уровень владения текущей компетенцией от 0 до 5.", "warning")
            return
        if self.assessment_index < len(self.competences) - 1:
            self.assessment_index += 1
            self._show_current_assessment()
        else:
            self.status_var.set("Оценка компетенций завершена. Теперь можно сформировать траекторию.")
            self._show_message("Оценка завершена", "Все компетенции пройдены. Нажмите «Сформировать», чтобы построить траекторию обучения.", "success")

    def _assessment_previous(self) -> None:

        self._save_current_assessment_value()
        if self.assessment_index > 0:
            self.assessment_index -= 1
            self._show_current_assessment()
        else:
            self._show_assessment_intro()





    # Создает административный раздел для добавления компетенций и связей.
    def _build_admin_tab(self) -> None:
        for widget in self.admin_tab.winfo_children():
            widget.destroy()
        self.admin_tab.columnconfigure(0, weight=1)
        self.admin_tab.columnconfigure(1, weight=1)
        self.admin_tab.rowconfigure(1, weight=1)

        header = self._card(self.admin_tab, padding=18)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(header, text="Администрирование справочника", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Здесь можно добавить новую компетенцию и связать компетенции в траекторию обучения. Раздел доступен администратору.",
            style="Muted.TLabel",
            wraplength=900,
        ).grid(row=1, column=0, sticky="w")

        competence_card = self._card(self.admin_tab, padding=18)
        competence_card.grid(row=1, column=0, sticky="nsew", pady=(14, 0), padx=(0, 7))
        competence_card.columnconfigure(0, weight=1)
        competence_card.columnconfigure(1, weight=1)
        ttk.Label(competence_card, text="Новая компетенция", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self._admin_entry(competence_card, 1, 0, "Код", self.admin_code_var, "Например: DC18")
        self._admin_entry(competence_card, 1, 1, "Название", self.admin_title_var, "Например: Основы BI")
        self._admin_entry(competence_card, 2, 0, "Направление", self.admin_direction_var, "Например: 17. BI-аналитика")
        self._admin_entry(competence_card, 2, 1, "Категория", self.admin_category_var, "Например: Аналитика")
        self._admin_combo(competence_card, 3, 0, "Сложность", self.admin_difficulty_var, LEVEL_VALUES[1:])
        self._admin_combo(competence_card, 3, 1, "Целевой уровень", self.admin_target_var, LEVEL_VALUES)
        self._admin_combo(competence_card, 4, 0, "Вес / приоритетность", self.admin_weight_var, tuple(str(value) for value in range(1, 11)))
        self._admin_entry(competence_card, 4, 1, "Предпосылки", self.admin_prerequisites_var, "Коды через запятую: DC03, DC12")
        self._admin_entry(competence_card, 5, 0, "Материал", self.admin_resource_title_var, "Например: Практикум по BI")
        self._admin_entry(competence_card, 5, 1, "Тип материала", self.admin_resource_kind_var, "Курс / Практика / Тест")
        self._admin_entry(competence_card, 6, 0, "Часы", self.admin_resource_hours_var, "Например: 8")

        ttk.Label(competence_card, text="Описание", style="CardTitle.TLabel").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 4))
        description = ttk.Entry(competence_card, textvariable=self.admin_description_var, font=("Segoe UI", 13))
        description.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Button(competence_card, text="➕  Добавить компетенцию", style="Success.TButton", command=self._add_admin_competence).grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        relation_card = self._card(self.admin_tab, padding=18)
        relation_card.grid(row=1, column=1, sticky="nsew", pady=(14, 0), padx=(7, 0))
        relation_card.columnconfigure(0, weight=1)
        ttk.Label(relation_card, text="Новая связь траектории", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            relation_card,
            text="Связь означает, что сначала нужно освоить предварительную компетенцию, а затем следующую. Это влияет на граф знаний и порядок траектории.",
            style="Muted.TLabel",
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        codes = [f"{item.code} — {item.title}" for item in self.competences]
        ttk.Label(relation_card, text="Предварительная компетенция", style="CardTitle.TLabel").grid(row=2, column=0, sticky="w")
        self.admin_parent_combo = ttk.Combobox(relation_card, textvariable=self.admin_parent_var, values=codes, state="readonly", font=("Segoe UI", 13))
        self.admin_parent_combo.grid(row=3, column=0, sticky="ew", pady=(5, 14))
        ttk.Label(relation_card, text="Следующая компетенция", style="CardTitle.TLabel").grid(row=4, column=0, sticky="w")
        self.admin_child_combo = ttk.Combobox(relation_card, textvariable=self.admin_child_var, values=codes, state="readonly", font=("Segoe UI", 13))
        self.admin_child_combo.grid(row=5, column=0, sticky="ew", pady=(5, 14))
        ttk.Button(relation_card, text="🧭  Добавить связь", style="Primary.TButton", command=self._add_admin_relation).grid(row=6, column=0, sticky="ew", pady=(8, 18))

        list_card = ttk.Frame(relation_card, style="Soft.TFrame", padding=14)
        list_card.grid(row=7, column=0, sticky="nsew")
        list_card.columnconfigure(0, weight=1)
        list_card.rowconfigure(1, weight=1)
        ttk.Label(list_card, text="Текущие связи", style="Side.TLabel").grid(row=0, column=0, sticky="w")
        self.admin_relations_list = tk.Listbox(list_card, height=14, font=("Segoe UI", 12), bg="#FFFFFF", fg=self.colors["text"], relief="flat")
        self.admin_relations_list.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        for competence in self.competences:
            for parent in competence.prerequisites:
                self.admin_relations_list.insert("end", f"{parent} → {competence.code}  ({competence.title})")

    def _admin_entry(self, parent: ttk.Frame, row: int, column: int, label: str, variable: tk.StringVar, placeholder: str = "") -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 8, 8 if column == 0 else 0), pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=label, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(frame, textvariable=variable, font=("Segoe UI", 13))
        entry.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        if placeholder and not variable.get():
            variable.set("")

    def _admin_combo(self, parent: ttk.Frame, row: int, column: int, label: str, variable: tk.StringVar, values: tuple[str, ...]) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 8, 8 if column == 0 else 0), pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=label, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=variable, values=list(values), state="readonly", font=("Segoe UI", 13)).grid(row=1, column=0, sticky="ew", pady=(5, 0))

    def _extract_code_from_combo(self, value: str) -> str:
        return value.split(" — ", 1)[0].strip()

    # Добавляет новую компетенцию из формы администратора.
    def _add_admin_competence(self) -> None:
        code = self.admin_code_var.get().strip().upper()
        title = self.admin_title_var.get().strip()
        direction = self.admin_direction_var.get().strip()
        category = self.admin_category_var.get().strip()
        description = self.admin_description_var.get().strip()
        try:
            difficulty = int(self.admin_difficulty_var.get())
            target_level = int(self.admin_target_var.get())
            weight = int(self.admin_weight_var.get())
            hours = int(self.admin_resource_hours_var.get() or "0")
        except ValueError:
            self._show_message("Ошибка", "Целевой уровень, вес и часы должны быть числами.", "error")
            return
        if not code or not title or not direction or not description:
            self._show_message("Не заполнены поля", "Заполните код, название, направление и описание компетенции.", "warning")
            return
        if any(item.code == code for item in self.competences):
            self._show_message("Дубликат", "Компетенция с таким кодом уже существует.", "warning")
            return
        prerequisites = tuple(item.strip().upper() for item in self.admin_prerequisites_var.get().split(",") if item.strip())
        existing_codes = {item.code for item in self.competences}
        missing = [item for item in prerequisites if item not in existing_codes]
        if missing:
            self._show_message("Не найдены предпосылки", "Таких компетенций нет в справочнике: " + ", ".join(missing), "warning")
            return
        resource_title = self.admin_resource_title_var.get().strip() or f"Материал по теме: {title}"
        resource_kind = self.admin_resource_kind_var.get().strip() or "Курс"
        new_competence = Competence(
            code=code,
            title=title,
            direction=direction,
            description=description,
            target_level=max(0, min(5, target_level)),
            weight=max(1, min(10, weight)),
            difficulty=max(1, min(5, difficulty)),
            category=category,
            prerequisites=prerequisites,
            resources=(LearningResource(resource_title, resource_kind, max(1, hours)),),
        )
        try:
            KnowledgeGraph([*self.competences, new_competence])
        except ValueError as error:
            self._show_message("Ошибка графа", str(error), "error")
            return
        self.competences.append(new_competence)
        self._save_competences_to_file()
        self._clear_admin_competence_form()
        self._refresh_after_knowledge_change("Компетенция добавлена.")

    def _add_admin_relation(self) -> None:
        parent = self._extract_code_from_combo(self.admin_parent_var.get())
        child = self._extract_code_from_combo(self.admin_child_var.get())
        if not parent or not child:
            self._show_message("Не выбраны компетенции", "Выберите предварительную и следующую компетенции.", "warning")
            return
        if parent == child:
            self._show_message("Нельзя создать связь", "Компетенция не может зависеть сама от себя.", "warning")
            return
        updated: list[Competence] = []
        changed = False
        for competence in self.competences:
            if competence.code == child:
                if parent in competence.prerequisites:
                    self._show_message("Связь уже есть", "Такая связь траектории уже существует.", "warning")
                    return
                competence = Competence(
                    code=competence.code,
                    title=competence.title,
                    direction=competence.direction,
                    description=competence.description,
                    target_level=competence.target_level,
                    weight=competence.weight,
                    difficulty=competence.difficulty,
                    category=competence.category,
                    prerequisites=tuple([*competence.prerequisites, parent]),
                    resources=competence.resources,
                )
                changed = True
            updated.append(competence)
        if not changed:
            self._show_message("Ошибка", "Не удалось найти выбранную компетенцию.", "error")
            return
        try:
            KnowledgeGraph(updated)
        except ValueError as error:
            self._show_message("Ошибка графа", str(error), "error")
            return
        self.competences = updated
        self._save_competences_to_file()
        self._refresh_after_knowledge_change("Связь траектории добавлена.")

    def _save_competences_to_file(self) -> None:
        save_competences(self.competences)

    def _clear_admin_competence_form(self) -> None:
        self.admin_code_var.set("")
        self.admin_title_var.set("")
        self.admin_direction_var.set("")
        self.admin_category_var.set("")
        self.admin_difficulty_var.set("3")
        self.admin_description_var.set("")
        self.admin_target_var.set("3")
        self.admin_weight_var.set("3")
        self.admin_prerequisites_var.set("")
        self.admin_resource_title_var.set("")
        self.admin_resource_kind_var.set("Курс")
        self.admin_resource_hours_var.set("8")

    def _refresh_after_knowledge_change(self, message: str) -> None:
        self.graph = KnowledgeGraph(self.competences)
        self.builder = TrajectoryBuilder(self.graph)
        self.node_positions = {}
        self.results_ready = False
        self.steps = []
        for competence in self.competences:
            if competence.code not in self.current_profile.levels:
                self.current_profile.levels[competence.code] = 0
        self._build_home_tab()
        self._build_competence_tab()
        self._build_graph_tab()
        self._build_trajectory_tab()
        self._build_results_tab()
        self._build_admin_tab()
        self.status_var.set(message)
        self._show_message("Готово", message, "success")

    def _build_results_tab(self) -> None:

        for widget in self.results_tab.winfo_children():
            widget.destroy()
        self.results_tab.columnconfigure(0, weight=1)
        self.results_tab.rowconfigure(1, weight=1)

        header = self._card(self.results_tab, padding=18)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Результаты траектории", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Результаты появляются только после заполнения всех уровней владения и расчёта траектории.", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Button(header, text="📄  Word-отчёт", style="Success.TButton", command=lambda: self._export("docx")).grid(row=0, column=1, rowspan=2, padx=(20, 0))

        result_frame = self._card(self.results_tab, padding=0)
        result_frame.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        columns = ("code", "title", "direction", "current", "target", "priority")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        headings = {"code": "Код", "title": "Компетенция", "direction": "Направление", "current": "Текущий", "target": "Целевой", "priority": "Приоритет /10"}
        widths = {"code": 80, "title": 250, "direction": 310, "current": 150, "target": 150, "priority": 120}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")
        self.tree.tag_configure("odd", background="#FFFFFF")
        self.tree.tag_configure("even", background="#F8F9FA")
        self.tree.grid(row=0, column=0, sticky="nsew")
        result_scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=result_scrollbar.set)
        result_scrollbar.grid(row=0, column=1, sticky="ns")

        self.details = tk.Text(result_frame, height=9, wrap="word", font=("Segoe UI", 12), bg="#FFFFFF", fg=self.colors["text"], relief="solid", bd=1, padx=10, pady=10)
        self.details.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.tree.bind("<<TreeviewSelect>>", self._show_selected_details)




    def _update_level_hint(self, variable: tk.StringVar, hint_variable: tk.StringVar) -> None:

        try:
            value = int(variable.get())
        except ValueError:
            variable.set("")
            hint_variable.set("выберите уровень 0–5")
            return
        if value not in range(6):
            variable.set("")
            hint_variable.set("выберите уровень 0–5")
            return
        hint_variable.set(LEVEL_HINTS[value])
        self._reset_results("Оценки изменены. Для актуального результата снова нажмите «Сформировать».")

    def _validate_profile_form(self) -> bool:

        if not self.full_name_var.get().strip():
            self._show_message("Не заполнено ФИО", "Укажите ФИО сотрудника.", "warning")
            return False
        missing = []
        for competence in self.competences:
            value = self.level_vars.get(competence.code, tk.StringVar()).get().strip()
            if value not in LEVEL_VALUES:
                missing.append(f"{competence.code} — {competence.title}")
        if missing:
            preview = "\n".join(missing[:8])
            if len(missing) > 8:
                preview += f"\n...и ещё {len(missing) - 8}"
            self._show_message(
                "Заполните оценки",
                "Перед формированием траектории необходимо указать владение каждой компетенцией от 0 до 5.\n\n"
                f"Не заполнено:\n{preview}",
                "warning",
            )
            return False
        return True

    def _collect_profile(self, validate: bool = True) -> EmployeeProfile | None:

        if validate and not self._validate_profile_form():
            return None
        levels: dict[str, int] = {}
        for competence in self.competences:
            raw = self.level_vars.get(competence.code, tk.StringVar()).get().strip()
            levels[competence.code] = int(raw) if raw in LEVEL_VALUES else 0
        return EmployeeProfile(
            full_name=self.full_name_var.get().strip() or "Без имени",
            position=self.position_var.get().strip() or "Не указано",
            department=self.department_var.get().strip() or "Не указано",
            levels=levels,
        )

    def _fill_profile(self, profile: EmployeeProfile) -> None:

        self.full_name_var.set(profile.full_name)
        self.position_var.set(profile.position)
        self.department_var.set(profile.department)
        for code, variable in self.level_vars.items():
            level = int(profile.levels.get(code, -1))
            if 0 <= level <= 5:
                variable.set(str(level))
                self.level_hint_vars[code].set(LEVEL_HINTS[level])
            else:
                variable.set("")
                self.level_hint_vars[code].set("выберите уровень 0–5")

    def _fill_empty_levels_with_zero(self) -> None:

        for code, variable in self.level_vars.items():
            if not variable.get().strip():
                variable.set("0")
                self.level_hint_vars[code].set(LEVEL_HINTS[0])
            if variable.get().strip() in LEVEL_VALUES:
                self.current_profile.levels[code] = int(variable.get().strip())
        self._reset_results("Пустые оценки заполнены нулём. Нажмите «Сформировать».")

    def _reset_results(self, message: str) -> None:

        self.results_ready = False
        self.steps = []
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
        if hasattr(self, "details"):
            self.details.delete("1.0", "end")
            self.details.insert("end", "Результаты пока не сформированы. Заполните компетенции и нажмите «Сформировать».\n")
        self.status_var.set(message)
        self._refresh_home_tab()
        self._draw_graph()

    def _rebuild_trajectory(self) -> None:

        profile = self._collect_profile(validate=True)
        if profile is None:
            self._reset_results("Не все оценки заполнены. Траектория не сформирована.")
            return
        self.current_profile = profile
        self.steps = self.builder.build(profile, self.direction_var.get())
        self.results_ready = True
        self._render_result_table()
        self._show_summary()
        self._draw_graph()
        self._refresh_home_tab()
        self.tabs.select(self.results_tab)
        self._refresh_sidebar_state(4)
        self.status_var.set("Траектория сформирована. Путь подсвечен на графе, доступен экспорт в Word.")

    def _render_result_table(self) -> None:

        self.tree.delete(*self.tree.get_children())
        for index, step in enumerate(self.steps):
            tag = "even" if index % 2 else "odd"
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    step.competence.code,
                    step.competence.title,
                    step.competence.direction,
                    Level.from_score(step.current_level).value,
                    Level.from_score(step.target_level).value,
                    f"{step.priority:.1f}",
                ),
                tags=(tag,),
            )

    def _show_summary(self) -> None:

        self.details.delete("1.0", "end")
        if not self.steps:
            self.details.insert("end", "Все выбранные компетенции соответствуют целевому уровню. Дополнительная траектория не требуется.\n")
            return
        total_hours = sum(resource.duration_hours for step in self.steps for resource in step.competence.resources)
        self.details.insert("end", f"Найдено шагов: {len(self.steps)}. Ориентировочная трудоёмкость: {total_hours} ч.\n")
        self.details.insert("end", "Приоритет ограничен шкалой 1–10. Выберите строку таблицы, чтобы увидеть причины рекомендации и материалы обучения.\n")

    def _show_selected_details(self, _event: object | None = None) -> None:

        if not self.results_ready:
            return
        selected = self.tree.selection()
        if not selected:
            return
        step = self.steps[int(selected[0])]
        self.details.delete("1.0", "end")
        self.details.insert("end", f"{step.competence.title}\n\n")
        self.details.insert("end", f"Описание: {step.competence.description}\n")
        self.details.insert("end", f"Текущий уровень: {Level.from_score(step.current_level).value}\n")
        self.details.insert("end", f"Целевой уровень: {Level.from_score(step.target_level).value}\n")
        self.details.insert("end", f"Причина рекомендации: {step.reason}\n")
        self.details.insert("end", f"Приоритет: {step.priority:.1f}/10\n\n")
        self.details.insert("end", "Рекомендуемые материалы:\n")
        for resource in step.competence.resources:
            self.details.insert("end", f"• {resource.title} — {resource.kind}, {resource.duration_hours} ч.\n")

    def _save_profile(self) -> None:

        profile = self._collect_profile(validate=True)
        if profile is None:
            return
        self.current_profile = profile
        self.repository.save(profile)
        self._show_message("Сохранено", "Профиль сотрудника сохранён в локальную базу SQLite.", "success")
        self.status_var.set("Профиль сохранён.")

    def _export(self, file_type: str) -> None:

        if not self.results_ready:
            self._show_message("Нет результатов", "Сначала заполните оценки компетенций и сформируйте траекторию.", "warning")
            return
        profile = self._collect_profile(validate=True)
        if profile is None:
            return
        extension = {"docx": "docx", "md": "md", "csv": "csv", "json": "json"}[file_type]
        path = filedialog.asksaveasfilename(
            defaultextension=f".{extension}",
            filetypes=[(extension.upper(), f"*.{extension}")],
            initialfile=f"trajectory_{profile.full_name.replace(' ', '_')}.{extension}",
        )
        if not path:
            return
        output_path = Path(path)
        try:
            if file_type == "docx":
                export_docx(profile, self.steps, output_path)
            elif file_type == "md":
                export_markdown(profile, self.steps, output_path)
            elif file_type == "csv":
                export_csv(self.steps, output_path)
            else:
                export_json(profile, self.steps, output_path)
        except RuntimeError as error:
            self._show_message("Ошибка экспорта", str(error), "error")
            return
        self._show_message("Экспорт выполнен", f"Файл сохранён:\n{output_path}", "success")
        self.status_var.set(f"Экспорт выполнен: {output_path.name}")

    def _go_to_trajectory(self) -> None:

        self.tabs.select(self.trajectory_tab)
        self._refresh_sidebar_state(3)

    def _show_message(self, title: str, text: str, kind: str = "info") -> None:

        palette = {
            "info": ("ℹ️", self.colors["primary"]),
            "success": ("✅", self.colors["success"]),
            "warning": ("⚠️", "#F97316"),
            "error": ("❗", self.colors["danger"]),
        }
        icon, color = palette.get(kind, palette["info"])
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg="#FFFFFF")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        box = ttk.Frame(dialog, style="Card.TFrame", padding=22)
        box.grid(row=0, column=0, sticky="nsew")
        icon_label = tk.Label(box, text=icon, bg="#FFFFFF", fg=color, font=("Segoe UI", 30, "bold"))
        icon_label.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 16))
        ttk.Label(box, text=title, style="CardTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(box, text=text, style="Muted.TLabel", wraplength=440, justify="left").grid(row=1, column=1, sticky="w", pady=(6, 18))
        ttk.Button(box, text="ОК", style="Primary.TButton", command=dialog.destroy).grid(row=2, column=1, sticky="e")

        dialog.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dialog.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")
        self.root.wait_window(dialog)

    def _show_about(self) -> None:

        self._show_message(
            "О программе",
            "Цифровая траектория\n\n"
            "Desktop-приложение для формирования персональных образовательных траекторий "
            "на основе графовой модели знаний.\n\n"
            "Версия UI: soft corporate / material desktop.",
            "info",
        )
