import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")

if os.path.exists(VENV_PYTHON) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(VENV_PYTHON)):
    result = subprocess.run([VENV_PYTHON, os.path.abspath(__file__), *sys.argv[1:]], cwd=BASE_DIR)
    raise SystemExit(result.returncode)

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from data_service import WeatherDataService
from forecast_service import ForecastService


class WeatherDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Analyst | Dashboard")
        self.root.geometry("1420x900")
        self.root.minsize(1120, 720)
        self.base_dir = BASE_DIR
        self.data_service = WeatherDataService(self.base_dir)
        self.forecast_service = ForecastService(self.base_dir)
        self.dark_mode = True
        self.selected_key = "temperature"
        self.figure = None
        self.canvas = None
        self.toolbar = None
        self.animation_job = None
        self.forecast_result = None
        self.before_after_data = None
        self.set_colors()
        self.setup_ui()

    def set_colors(self):
        if self.dark_mode:
            self.colors = {
                "background": "#071722",
                "sidebar": "#0d1f2f",
                "panel": "#10293b",
                "panel_light": "#15344a",
                "panel_alt": "#0b1f2c",
                "border": "#214766",
                "text": "#edf8ff",
                "muted": "#9db8ca",
                "accent": "#6ee7ff",
                "accent_dark": "#1b8fbc",
                "accent_soft": "#163d52",
                "warning": "#ffb454",
                "danger": "#ff6b7d",
                "success": "#5ee8a0",
                "purple": "#9e8cff"
            }
        else:
            self.colors = {
                "background": "#edf4f8",
                "sidebar": "#f9fbfd",
                "panel": "#ffffff",
                "panel_light": "#edf6fb",
                "panel_alt": "#f2f8fc",
                "border": "#d4e1ea",
                "text": "#173142",
                "muted": "#6a7f8d",
                "accent": "#0c7bb6",
                "accent_dark": "#d9f4ff",
                "accent_soft": "#ebf8ff",
                "warning": "#d88a1f",
                "danger": "#dc4f6b",
                "success": "#2ca86b",
                "purple": "#7257d8"
            }
        self.root.configure(bg=self.colors["background"])

    def setup_ui(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.figure = None
        self.canvas = None
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.configure_styles()
        self.build_header()
        self.build_controls()
        self.build_tabs()
        self.refresh_dashboard()

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Weather.TNotebook", background=self.colors["background"], borderwidth=0)
        style.configure("Weather.TNotebook.Tab", background=self.colors["sidebar"], foreground=self.colors["muted"], padding=(18, 10), font=("Segoe UI", 10, "bold"))
        style.map("Weather.TNotebook.Tab", background=[("selected", self.colors["accent_dark"])], foreground=[("selected", self.colors["text"])])
        style.configure("Weather.Treeview", background=self.colors["panel"], fieldbackground=self.colors["panel"], foreground=self.colors["text"], rowheight=29, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Weather.Treeview.Heading", background=self.colors["panel_light"], foreground=self.colors["text"], font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Weather.Treeview", background=[("selected", self.colors["accent_dark"])], foreground=[("selected", self.colors["text"])])
        style.configure("Weather.TCombobox", fieldbackground=self.colors["panel"], background=self.colors["panel"], foreground=self.colors["text"])

    def build_header(self):
        header = tk.Frame(self.root, bg=self.colors["background"], height=92)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(18, 12))
        header.grid_propagate(False)

        brand = tk.Frame(header, bg=self.colors["background"])
        brand.pack(side="left", fill="y", padx=(8, 0))
        tk.Label(brand, text="WEATHER ANALYST", font=("Segoe UI", 10, "bold"), fg=self.colors["accent"], bg=self.colors["background"]).pack(anchor="w")
        tk.Label(brand, text="Trung tâm phân tích và dự báo thời tiết", font=("Segoe UI", 25, "bold"), fg=self.colors["text"], bg=self.colors["background"]).pack(anchor="w", pady=(4, 0))

        actions = tk.Frame(header, bg=self.colors["background"])
        actions.pack(side="right", fill="y")

        theme_btn = tk.Button(
            actions, text="☾  Dark / Light", command=self.toggle_theme,
            relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"),
            bg=self.colors["panel"], fg=self.colors["text"],
            activebackground=self.colors["accent_soft"], activeforeground=self.colors["text"],
            padx=16, pady=10, highlightthickness=1, highlightbackground=self.colors["border"]
        )
        theme_btn.pack(side="left", pady=18, padx=(0, 10))

        self.live_label = tk.Label(
            actions, text="●  DỮ LIỆU SẴN SÀNG", font=("Segoe UI", 9, "bold"),
            fg=self.colors["success"], bg=self.colors["panel"],
            padx=16, pady=10, highlightthickness=1, highlightbackground=self.colors["border"]
        )
        self.live_label.pack(side="left", pady=18)

    def build_controls(self):
        controls = tk.Frame(self.root, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
        controls.grid(row=0, column=0, sticky="e", padx=30, pady=(94, 12))

        pad = tk.Frame(controls, bg=self.colors["panel"])
        pad.pack(side="left", padx=(14, 0), pady=8)

        tk.Label(controls, text="TỪ", bg=self.colors["panel"], fg=self.colors["muted"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=(14, 5), pady=8)
        self.start_entry = tk.Entry(controls, width=12, relief="flat", bg=self.colors["panel_light"], fg=self.colors["text"], insertbackground=self.colors["text"], font=("Segoe UI", 9))
        self.start_entry.insert(0, self.data_service.date_min.strftime("%Y-%m-%d"))
        self.start_entry.pack(side="left", padx=3, pady=8)

        tk.Label(controls, text="ĐẾN", bg=self.colors["panel"], fg=self.colors["muted"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=(12, 5), pady=8)
        self.end_entry = tk.Entry(controls, width=12, relief="flat", bg=self.colors["panel_light"], fg=self.colors["text"], insertbackground=self.colors["text"], font=("Segoe UI", 9))
        self.end_entry.insert(0, self.data_service.date_max.strftime("%Y-%m-%d"))
        self.end_entry.pack(side="left", padx=3, pady=8)

        self.action_button(controls, "Chọn CSV", self.choose_csv, self.colors["panel_light"]).pack(side="left", padx=(10, 4), pady=8)
        self.action_button(controls, "Lọc dữ liệu", self.refresh_dashboard, self.colors["accent"]).pack(side="left", padx=(4, 4), pady=8)
        self.action_button(controls, "Xuất CSV", self.export_csv, self.colors["panel_light"]).pack(side="left", padx=(4, 4), pady=8)
        self.action_button(controls, "Báo cáo HTML", self.export_report, self.colors["panel_light"]).pack(side="left", padx=(4, 12), pady=8)

    def action_button(self, parent, text, command, background):
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), bg=background, fg=self.colors["text"], activebackground=self.colors["accent_dark"], activeforeground=self.colors["text"], padx=10, pady=6)

    def build_tabs(self):
        self.notebook = ttk.Notebook(self.root, style="Weather.TNotebook")
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 25))
        self.overview_tab = tk.Frame(self.notebook, bg=self.colors["background"])
        self.outlier_tab = tk.Frame(self.notebook, bg=self.colors["background"])
        self.data_tab = tk.Frame(self.notebook, bg=self.colors["background"])
        self.forecast_tab = tk.Frame(self.notebook, bg=self.colors["background"])
        self.alert_tab = tk.Frame(self.notebook, bg=self.colors["background"])
        self.notebook.add(self.overview_tab, text="  Tổng quan  ")
        self.notebook.add(self.outlier_tab, text="  Outlier  ")
        self.notebook.add(self.data_tab, text="  Dữ liệu  ")
        self.notebook.add(self.forecast_tab, text="  Dự báo  ")
        self.notebook.add(self.alert_tab, text="  Cảnh báo  ")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.build_overview()
        self.build_outlier_tab()
        self.build_data_tab()
        self.build_forecast_tab()
        self.build_alert_tab()

    def on_tab_changed(self, event=None):
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 3:
            self.selected_key = "forecast"
            self.render_chart(animate=True)
        elif self.selected_key == "forecast":
            self.selected_key = "temperature"
            self.render_chart(animate=True)

    def build_overview(self):
        self.overview_tab.grid_columnconfigure(0, weight=1)
        self.overview_tab.grid_rowconfigure(1, weight=1)

        self.kpi_frame = tk.Frame(self.overview_tab, bg=self.colors["background"])
        self.kpi_frame.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        for index in range(5):
            self.kpi_frame.grid_columnconfigure(index, weight=1)

        self.kpi_labels = {}
        cards = [("days", "Số ngày", "▣"), ("avg_temp", "Nhiệt độ TB", "☀"), ("max_temp", "Cao nhất", "↑"), ("rainfall", "Tổng mưa", "☂"), ("humidity", "Độ ẩm TB", "%")]
        for index, (key, title, icon) in enumerate(cards):
            card = tk.Frame(self.kpi_frame, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 8, 0))
            tk.Label(card, text=icon, font=("Segoe UI Symbol", 18), fg=self.colors["accent"], bg=self.colors["panel"]).pack(anchor="w", padx=16, pady=(14, 0))
            value = tk.Label(card, text="--", font=("Segoe UI", 23, "bold"), fg=self.colors["text"], bg=self.colors["panel"])
            value.pack(anchor="w", padx=16)
            tk.Label(card, text=title, font=("Segoe UI", 9), fg=self.colors["muted"], bg=self.colors["panel"]).pack(anchor="w", padx=16, pady=(0, 14))
            self.kpi_labels[key] = value

        body = tk.Frame(self.overview_tab, bg=self.colors["background"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.chart_nav = tk.Frame(body, bg=self.colors["sidebar"], width=270)
        self.chart_nav.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.chart_nav.grid_propagate(False)
        tk.Label(self.chart_nav, text="BIỂU ĐỒ PHÂN TÍCH", font=("Segoe UI", 9, "bold"), fg=self.colors["muted"], bg=self.colors["sidebar"]).pack(anchor="w", padx=18, pady=(18, 12))
        self.images = {"temperature": ("Nhiệt độ", "Xu hướng nhiệt độ", "temperature_trend.png", "°C", "☀"), "outlier": ("Ngoại lệ", "Kiểm tra IQR", "boxplot_after_outlier.png", "IQR", "◈"), "rainfall": ("Lượng mưa", "Phân phối log", "rainfall_log_distribution.png", "mm", "☂"), "charts": ("Tổng quan", "Các chỉ số thời tiết", "weather_line_charts.png", "LIVE", "▥"), "forecast": ("Dự báo", "Mô hình hiện tại", "temperature_forecast.png", "ARIMA", "↗")}
        self.chart_buttons = {}
        for key, (title, subtitle, _, badge, icon) in self.images.items():
            self.create_chart_button(key, title, subtitle, badge, icon)
        viewer = tk.Frame(body, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
        viewer.grid(row=0, column=1, sticky="nsew")
        viewer.grid_columnconfigure(0, weight=1)
        viewer.grid_rowconfigure(0, weight=1)
        self.chart_frame = tk.Frame(viewer, bg=self.colors["panel"])
        self.chart_frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.chart_frame.grid_columnconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(0, weight=1)
        viewer.bind("<Configure>", lambda _: self.render_chart())

    def create_chart_button(self, key, title, subtitle, badge, icon):
        button = tk.Frame(self.chart_nav, bg=self.colors["sidebar"], cursor="hand2")
        button.pack(fill="x", padx=10, pady=3)
        icon_label = tk.Label(button, text=icon, width=3, font=("Segoe UI Symbol", 16), fg=self.colors["accent"], bg=self.colors["sidebar"])
        icon_label.pack(side="left", padx=(5, 0), pady=9)
        text = tk.Frame(button, bg=self.colors["sidebar"])
        text.pack(side="left", fill="x", expand=True, pady=7)
        tk.Label(text, text=title, anchor="w", font=("Segoe UI", 10, "bold"), fg=self.colors["text"], bg=self.colors["sidebar"]).pack(fill="x")
        tk.Label(text, text=subtitle, anchor="w", font=("Segoe UI", 8), fg=self.colors["muted"], bg=self.colors["sidebar"]).pack(fill="x", pady=(2, 0))
        badge_label = tk.Label(button, text=badge, font=("Segoe UI", 8, "bold"), fg=self.colors["muted"], bg=self.colors["sidebar"])
        badge_label.pack(side="right", padx=8)
        widgets = (button, icon_label, text, badge_label)
        self.chart_buttons[key] = widgets
        for widget in (button, icon_label, text, badge_label, *text.winfo_children()):
            widget.bind("<Button-1>", lambda _, selected=key: self.show_image(selected))

    def build_outlier_tab(self):
        self.outlier_tab.grid_columnconfigure(0, weight=1)
        self.outlier_tab.grid_rowconfigure(1, weight=1)

        heading = tk.Label(self.outlier_tab, text="So sánh Before vs After Outlier", font=("Segoe UI", 18, "bold"), fg=self.colors["text"], bg=self.colors["background"])
        heading.grid(row=0, column=0, sticky="w", padx=18, pady=(12, 8))

        summary_frame = tk.Frame(self.outlier_tab, bg=self.colors["background"])
        summary_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.outlier_kpis = {}
        for idx, key in enumerate(["before_total", "after_total", "rainfall_before", "rainfall_after"]):
            card = tk.Frame(summary_frame, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
            card.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 8, 0))
            card.grid_columnconfigure(0, weight=1)
            value = tk.Label(card, text="0", font=("Segoe UI", 16, "bold"), fg=self.colors["text"], bg=self.colors["panel"])
            value.pack(anchor="w", padx=12, pady=(12, 0))
            label = tk.Label(card, text="", font=("Segoe UI", 9), fg=self.colors["muted"], bg=self.colors["panel"])
            label.pack(anchor="w", padx=12, pady=(0, 12))
            self.outlier_kpis[key] = (value, label)

        self.outlier_kpis["before_total"][1].config(text="Tổng outlier trước xử lý")
        self.outlier_kpis["after_total"][1].config(text="Tổng outlier sau xử lý")
        self.outlier_kpis["rainfall_before"][1].config(text="Rainfall trước xử lý")
        self.outlier_kpis["rainfall_after"][1].config(text="Rainfall sau xử lý")

        plot_frame = tk.Frame(self.outlier_tab, bg=self.colors["background"])
        plot_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 10))
        plot_frame.grid_columnconfigure(0, weight=1)
        plot_frame.grid_rowconfigure(0, weight=1)

        self.before_after_figure = plt.Figure(figsize=(11, 5), dpi=100, facecolor=self.colors["panel"])
        self.before_after_canvas = FigureCanvasTkAgg(self.before_after_figure, master=plot_frame)
        self.before_after_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.before_after_toolbar = NavigationToolbar2Tk(self.before_after_canvas, plot_frame)
        self.before_after_toolbar.update()
        self.before_after_toolbar.pack(fill="x")

    def build_data_tab(self):
        self.data_tab.grid_columnconfigure(0, weight=1)
        self.data_tab.grid_rowconfigure(1, weight=1)
        tk.Label(self.data_tab, text="Bảng dữ liệu đã làm sạch", font=("Segoe UI", 16, "bold"), fg=self.colors["text"], bg=self.colors["background"]).grid(row=0, column=0, sticky="w", pady=(8, 12))
        frame = tk.Frame(self.data_tab, bg=self.colors["panel"])
        frame.grid(row=1, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        columns = ("Date", "MinTemp", "MaxTemp", "AvgTemp", "Rainfall", "Humidity9am", "Humidity3pm")
        self.data_table = ttk.Treeview(frame, columns=columns, show="headings", style="Weather.Treeview")
        headings = {"Date": "Ngày", "MinTemp": "Min °C", "MaxTemp": "Max °C", "AvgTemp": "TB °C", "Rainfall": "Mưa mm", "Humidity9am": "Ẩm 9h %", "Humidity3pm": "Ẩm 15h %"}
        for column in columns:
            self.data_table.heading(column, text=headings[column])
            self.data_table.column(column, width=125, anchor="center")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.data_table.yview)
        self.data_table.configure(yscrollcommand=scrollbar.set)
        self.data_table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        tk.Label(self.data_tab, text="Hiển thị tối đa 300 dòng mới nhất trong khoảng thời gian đã lọc.", font=("Segoe UI", 9), fg=self.colors["muted"], bg=self.colors["background"]).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def build_forecast_tab(self):
        self.forecast_tab.grid_columnconfigure(0, weight=1)
        self.forecast_tab.grid_rowconfigure(3, weight=1)
        top = tk.Frame(self.forecast_tab, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
        top.grid(row=0, column=0, sticky="ew", pady=(8, 10), padx=0)
        tk.Label(top, text="So sánh mô hình dự báo", font=("Segoe UI", 16, "bold"), fg=self.colors["text"], bg=self.colors["panel"]).pack(side="left", padx=14, pady=10)
        tk.Label(top, text="Số ngày:", font=("Segoe UI", 9), fg=self.colors["muted"], bg=self.colors["panel"]).pack(side="left", padx=(16, 5), pady=10)
        self.horizon_var = tk.StringVar(value="30")
        ttk.Combobox(top, textvariable=self.horizon_var, values=("7", "14", "30", "60"), width=5, state="readonly", style="Weather.TCombobox").pack(side="left", pady=10)
        self.action_button(top, "Chạy so sánh", self.run_forecast, self.colors["accent"]).pack(side="left", padx=10, pady=10)
        self.best_model_label = tk.Label(self.forecast_tab, text="Chưa chạy dự báo trong phiên này", font=("Segoe UI", 11, "bold"), fg=self.colors["accent"], bg=self.colors["panel"], padx=14, pady=8, highlightthickness=1, highlightbackground=self.colors["border"])
        self.best_model_label.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        summary = tk.Frame(self.forecast_tab, bg=self.colors["background"])
        summary.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for index in range(4):
            summary.grid_columnconfigure(index, weight=1)
        self.forecast_summary_labels = {}
        summary_items = (
            ("avg", "Nhiệt độ dự kiến", "-- °C"),
            ("low", "Mức thấp nhất", "-- °C"),
            ("high", "Mức cao nhất", "-- °C"),
            ("trend", "Xu hướng", "--"),
        )
        for index, (key, title, value) in enumerate(summary_items):
            card = tk.Frame(summary, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 5, 5 if index < 3 else 0))
            tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), fg=self.colors["muted"], bg=self.colors["panel"]).pack(anchor="w", padx=12, pady=(10, 2))
            label = tk.Label(card, text=value, font=("Segoe UI", 15, "bold"), fg=self.colors["accent"], bg=self.colors["panel"])
            label.pack(anchor="w", padx=12, pady=(0, 10))
            self.forecast_summary_labels[key] = label
        body = tk.Frame(self.forecast_tab, bg=self.colors["background"])
        body.grid(row=3, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        metrics_frame = tk.Frame(body, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
        metrics_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        future_frame = tk.Frame(body, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
        future_frame.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(metrics_frame, text="Đánh giá lỗi trên 30 ngày cuối", font=("Segoe UI", 11, "bold"), fg=self.colors["text"], bg=self.colors["panel"]).pack(anchor="w", padx=14, pady=14)
        self.metrics_table = ttk.Treeview(metrics_frame, columns=("Model", "MAE", "RMSE"), show="headings", height=9, style="Weather.Treeview")
        for column, title in (("Model", "Mô hình"), ("MAE", "MAE"), ("RMSE", "RMSE")):
            self.metrics_table.heading(column, text=title)
            self.metrics_table.column(column, width=140, anchor="center")
        self.metrics_table.pack(fill="x", padx=12, pady=(0, 12))
        tk.Label(future_frame, text="Dự báo sắp tới", font=("Segoe UI", 11, "bold"), fg=self.colors["text"], bg=self.colors["panel"]).pack(anchor="w", padx=14, pady=14)
        self.future_table = ttk.Treeview(future_frame, columns=("Date", "Forecast", "Model"), show="headings", height=9, style="Weather.Treeview")
        for column, title in (("Date", "Ngày"), ("Forecast", "Nhiệt độ °C"), ("Model", "Mô hình")):
            self.future_table.heading(column, text=title)
            self.future_table.column(column, width=135, anchor="center")
        self.future_table.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def build_alert_tab(self):
        self.alert_tab.grid_columnconfigure(0, weight=1)
        tk.Label(self.alert_tab, text="Trung tâm cảnh báo", font=("Segoe UI", 16, "bold"), fg=self.colors["text"], bg=self.colors["background"]).grid(row=0, column=0, sticky="w", pady=(8, 4))
        tk.Label(self.alert_tab, text="Ngưỡng cảnh báo có thể mở rộng theo nhu cầu vận hành.", font=("Segoe UI", 10), fg=self.colors["muted"], bg=self.colors["background"]).grid(row=1, column=0, sticky="w", pady=(0, 16))
        self.alert_list = tk.Frame(self.alert_tab, bg=self.colors["background"])
        self.alert_list.grid(row=2, column=0, sticky="ew")

    def refresh_dashboard(self):
        try:
            frame = self.data_service.filter(self.start_entry.get().strip(), self.end_entry.get().strip())
        except (ValueError, TypeError):
            messagebox.showerror("Khoảng thời gian không hợp lệ", "Hãy nhập ngày theo định dạng YYYY-MM-DD.")
            return
        if frame.empty:
            messagebox.showwarning("Không có dữ liệu", "Khoảng thời gian này không có bản ghi thời tiết.")
            return
        self.filtered_frame = frame
        summary = self.data_service.summary(frame)
        self.kpi_labels["days"].config(text=f"{summary['days']:,}")
        self.kpi_labels["avg_temp"].config(text=f"{summary['avg_temp']:.1f} °C")
        self.kpi_labels["max_temp"].config(text=f"{summary['max_temp']:.1f} °C")
        self.kpi_labels["rainfall"].config(text=f"{summary['rainfall']:.1f} mm")
        self.kpi_labels["humidity"].config(text=f"{summary['humidity']:.1f} %")

        self.before_after_data = self.data_service.outlier_summary(frame)
        self.refresh_outlier_summary()
        self.refresh_table()
        self.refresh_alerts()
        self.show_image(self.selected_key)

    def refresh_outlier_summary(self):
        if not hasattr(self, "before_after_data") or not self.before_after_data:
            return

        before = self.before_after_data["before"]
        after = self.before_after_data["after"]
        before_total = sum(item["total"] for item in before.values())
        after_total = sum(item["total"] for item in after.values())
        rainfall_before = before.get("Rainfall", {}).get("total", 0)
        rainfall_after = after.get("Rainfall", {}).get("total", 0)

        self.outlier_kpis["before_total"][0].config(text=f"{before_total}")
        self.outlier_kpis["after_total"][0].config(text=f"{after_total}")
        self.outlier_kpis["rainfall_before"][0].config(text=f"{rainfall_before}")
        self.outlier_kpis["rainfall_after"][0].config(text=f"{rainfall_after}")

        self.before_after_figure.clear()
        axes = self.before_after_figure.add_subplot(111)
        categories = ["MinTemp", "MaxTemp", "AvgTemp", "Rainfall", "Humidity9am", "Humidity3pm"]
        before_vals = [before.get(col, {}).get("total", 0) for col in categories]
        after_vals = [after.get(col, {}).get("total", 0) for col in categories]
        x = range(len(categories))
        axes.bar([i - 0.18 for i in x], before_vals, width=0.36, color="#f2b84b", label="Before")
        axes.bar([i + 0.18 for i in x], after_vals, width=0.36, color="#42c2d8", label="After")
        axes.set_xticks(list(x))
        axes.set_xticklabels(categories, rotation=20)
        axes.set_title("So sánh số outlier trước/sau xử lý")
        axes.set_ylabel("Số lượng outlier")
        axes.grid(True, axis="y", alpha=0.25)
        axes.legend(frameon=False)
        self.before_after_figure.tight_layout()
        self.before_after_canvas.draw_idle()

    def refresh_table(self):
        for item in self.data_table.get_children():
            self.data_table.delete(item)
        for row in self.data_service.table_rows(self.filtered_frame):
            self.data_table.insert("", "end", values=row)

    def refresh_alerts(self):
        for child in self.alert_list.winfo_children():
            child.destroy()
        for title, detail, level in self.data_service.alerts(self.filtered_frame):
            color = self.colors["danger"] if level == "danger" else self.colors["warning"] if level == "warning" else self.colors["success"] if level == "success" else self.colors["accent"]
            card = tk.Frame(self.alert_list, bg=self.colors["panel"], highlightthickness=1, highlightbackground=self.colors["border"])
            card.pack(fill="x", pady=5)
            tk.Label(card, text="●", font=("Segoe UI", 16), fg=color, bg=self.colors["panel"]).pack(side="left", padx=16, pady=13)
            text = tk.Frame(card, bg=self.colors["panel"])
            text.pack(side="left", pady=10)
            tk.Label(text, text=title, font=("Segoe UI", 11, "bold"), fg=self.colors["text"], bg=self.colors["panel"]).pack(anchor="w")
            tk.Label(text, text=detail, font=("Segoe UI", 9), fg=self.colors["muted"], bg=self.colors["panel"]).pack(anchor="w", pady=(3, 0))

    def show_image(self, key):
        if not hasattr(self, "chart_frame"):
            return
        self.selected_key = key
        for selected, widgets in self.chart_buttons.items():
            background = self.colors["accent_dark"] if selected == key else self.colors["sidebar"]
            for widget in widgets + tuple(widgets[2].winfo_children()):
                widget.configure(bg=background)
            widgets[1].configure(fg=self.colors["text"] if selected == key else self.colors["accent"])
        self.render_chart(animate=True)

    def render_chart(self, animate=False, progress=1.0):
        if not hasattr(self, "chart_frame") or not hasattr(self, "filtered_frame"):
            return
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        if animate and progress >= 1.0:
            self.draw_dynamic_chart(0.0)
            self.animation_job = self.root.after(45, lambda: self.animate_chart(0.2))
            return
        self.draw_dynamic_chart(progress)

    def animate_chart(self, progress):
        if progress >= 1.0:
            self.animation_job = None
            self.draw_dynamic_chart(1.0)
            return
        self.draw_dynamic_chart(progress)
        self.animation_job = self.root.after(45, lambda: self.animate_chart(min(progress + 0.2, 1.0)))

    def draw_dynamic_chart(self, progress=1.0):
        frame = self.filtered_frame
        if self.figure is None:
            self.figure = plt.Figure(figsize=(10, 6), dpi=100, facecolor=self.colors["panel"])
        else:
            self.figure.clear()
        if self.selected_key == "temperature":
            self.draw_temperature_chart(frame, progress)
        elif self.selected_key == "outlier":
            self.draw_outlier_chart(frame)
        elif self.selected_key == "rainfall":
            self.draw_rainfall_chart(frame, progress)
        elif self.selected_key == "charts":
            self.draw_overview_chart(frame, progress)
        else:
            self.draw_forecast_chart(frame, progress)
        self.figure.tight_layout(pad=2.0)
        if self.canvas is None:
            self.canvas = FigureCanvasTkAgg(self.figure, master=self.chart_frame)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.chart_frame)
            self.toolbar.update()
            self.toolbar.pack(fill="x")
        self.canvas.draw_idle()

    def style_axes(self, axes, title, ylabel=None):
        axes.set_facecolor(self.colors["panel"])
        axes.set_title(title, color=self.colors["text"], fontsize=13, fontweight="bold", pad=12)
        axes.tick_params(colors=self.colors["muted"], labelsize=8)
        for spine in axes.spines.values():
            spine.set_color(self.colors["border"])
        axes.grid(True, color=self.colors["border"], alpha=0.45, linewidth=0.7)
        if ylabel:
            axes.set_ylabel(ylabel, color=self.colors["muted"])

    def draw_temperature_chart(self, frame, progress):
        axes = self.figure.add_subplot(111)
        visible = frame.iloc[:max(1, int(len(frame) * progress))]
        axes.plot(visible.index, visible["MinTemp"], color="#70a9d8", linewidth=1, label="Thấp nhất")
        axes.plot(visible.index, visible["MaxTemp"], color="#f2b84b", linewidth=1, label="Cao nhất")
        axes.plot(visible.index, visible["AvgTemp"].rolling(7, min_periods=1).mean(), color=self.colors["accent"], linewidth=2, label="TB trượt 7 ngày")
        self.style_axes(axes, "Nhiệt độ theo ngày đang lọc", "°C")
        axes.legend(facecolor=self.colors["panel_light"], labelcolor=self.colors["text"], frameon=False)
        self.format_dates(axes)

    def draw_rainfall_chart(self, frame, progress):
        axes = self.figure.add_subplot(111)
        visible = frame.iloc[:max(1, int(len(frame) * progress))]
        axes.bar(visible.index, visible["Rainfall"], color=self.colors["accent"], alpha=0.55, width=1.0, label="Lượng mưa ngày")
        axes.plot(visible.index, visible["Rainfall"].rolling(7, min_periods=1).mean(), color=self.colors["warning"], linewidth=2, label="Trung bình 7 ngày")
        self.style_axes(axes, "Lượng mưa theo ngày đang lọc", "mm")
        axes.legend(facecolor=self.colors["panel_light"], labelcolor=self.colors["text"], frameon=False)
        self.format_dates(axes)

    def draw_outlier_chart(self, frame):
        axes = self.figure.add_subplot(111)
        columns = ["MinTemp", "MaxTemp", "AvgTemp", "Rainfall", "Humidity9am", "Humidity3pm"]
        axes.boxplot([frame[column].dropna() for column in columns], tick_labels=columns, patch_artist=True,
                     boxprops={"facecolor": self.colors["accent_dark"], "color": self.colors["accent"]},
                     medianprops={"color": self.colors["warning"], "linewidth": 2},
                     whiskerprops={"color": self.colors["muted"]}, capprops={"color": self.colors["muted"]})
        self.style_axes(axes, "Kiểm tra ngoại lệ theo khoảng ngày", "Giá trị")
        axes.tick_params(axis="x", rotation=25)

    def draw_overview_chart(self, frame, progress):
        visible = frame.iloc[:max(1, int(len(frame) * progress))]
        axes = self.figure.subplots(2, 2)
        self.plot_small_series(axes[0, 0], visible, "AvgTemp", "Nhiệt độ TB", "°C", self.colors["accent"])
        self.plot_small_series(axes[0, 1], visible, "Rainfall", "Lượng mưa", "mm", self.colors["warning"])
        self.plot_small_series(axes[1, 0], visible, "Humidity9am", "Độ ẩm 9h", "%", "#70a9d8")
        self.plot_small_series(axes[1, 1], visible, "Humidity3pm", "Độ ẩm 15h", "%", "#b38de0")

    def plot_small_series(self, axes, frame, column, title, ylabel, color):
        axes.plot(frame.index, frame[column].rolling(7, min_periods=1).mean(), color=color, linewidth=1.8)
        self.style_axes(axes, title, ylabel)
        axes.tick_params(axis="x", labelrotation=25)

    def draw_forecast_chart(self, frame, progress):
        axes = self.figure.add_subplot(111)
        visible = frame.iloc[:max(1, int(len(frame) * progress))]
        axes.plot(visible.index, visible["AvgTemp"], color=self.colors["muted"], linewidth=2.0, label="Thực tế", zorder=2)
        if self.forecast_result is not None:
            future = self.forecast_result["future"].copy()
            future["Date"] = pd.to_datetime(future["Date"])
            last_real_date = visible.index[-1]
            last_real_value = float(visible["AvgTemp"].iloc[-1])
            axes.axvline(last_real_date, color=self.colors["border"], linestyle="--", linewidth=1.0, alpha=0.9, zorder=1)
            axes.scatter([last_real_date], [last_real_value], color=self.colors["warning"], s=30, zorder=4, label="Điểm cuối thực tế")
            axes.plot(future["Date"], future["Forecast"], color=self.colors["accent"], linewidth=2.8, linestyle="--",
                      marker="o", markersize=4, label=f"Dự báo: {self.forecast_result['best_model']}", zorder=3)
            axes.scatter(future["Date"].iloc[[0]], future["Forecast"].iloc[[0]], color=self.colors["accent"], s=24, zorder=4)
            axes.scatter(future["Date"].iloc[[-1]], future["Forecast"].iloc[[-1]], color=self.colors["success"], s=26, zorder=4)
            min_date = min(visible.index.min(), future["Date"].min()) - pd.Timedelta(days=3)
            max_date = max(visible.index.max(), future["Date"].max()) + pd.Timedelta(days=3)
            axes.set_xlim(min_date, max_date)
        self.style_axes(axes, "Nhiệt độ thực tế và dự báo", "°C")
        axes.legend(facecolor=self.colors["panel_light"], labelcolor=self.colors["text"], frameon=False, loc="upper left", fontsize=9)
        self.format_dates(axes)

    @staticmethod
    def format_dates(axes):
        axes.xaxis.set_major_locator(mdates.AutoDateLocator())
        axes.xaxis.set_major_formatter(mdates.ConciseDateFormatter(axes.xaxis.get_major_locator()))

    def run_forecast(self):
        try:
            horizon = int(self.horizon_var.get())
            if not hasattr(self, "filtered_frame") or self.filtered_frame.empty:
                raise ValueError("Chưa có dữ liệu trong khoảng ngày đã chọn.")
            if len(self.filtered_frame) < horizon + 14:
                raise ValueError(f"Khoảng dữ liệu hiện tại chỉ có {len(self.filtered_frame)} ngày; cần ít nhất {horizon + 14} ngày để dự báo {horizon} ngày.")
            self.best_model_label.config(text="Đang huấn luyện và so sánh mô hình...", fg=self.colors["warning"])
            self.root.update_idletasks()
            self.forecast_result = self.forecast_service.run(self.filtered_frame["AvgTemp"], horizon)
        except (ValueError, TypeError, KeyError, OSError) as error:
            self.best_model_label.config(text="Chưa chạy được dự báo", fg=self.colors["danger"])
            messagebox.showerror("Không thể dự báo", str(error))
            return
        except Exception as error:
            self.best_model_label.config(text="Lỗi trong quá trình dự báo", fg=self.colors["danger"])
            messagebox.showerror("Lỗi chạy dự báo", f"{type(error).__name__}: {error}")
            return
        for table in (self.metrics_table, self.future_table):
            for item in table.get_children():
                table.delete(item)
        for _, row in self.forecast_result["metrics"].iterrows():
            self.metrics_table.insert("", "end", values=(row["Model"], f"{row['MAE']:.3f}", f"{row['RMSE']:.3f}"))
        future = self.forecast_result["future"]
        for _, row in future.iterrows():
            self.future_table.insert("", "end", values=(row["Date"].strftime("%Y-%m-%d"), f"{row['Forecast']:.2f}", row["Model"]))
        forecast_values = future["Forecast"]
        first_value = float(forecast_values.iloc[0])
        last_value = float(forecast_values.iloc[-1])
        change = last_value - first_value
        if change > 0.3:
            trend = "Tăng"
        elif change < -0.3:
            trend = "Giảm"
        else:
            trend = "Ổn định"
        self.forecast_summary_labels["avg"].config(text=f"{forecast_values.mean():.1f} °C")
        self.forecast_summary_labels["low"].config(text=f"{forecast_values.min():.1f} °C")
        self.forecast_summary_labels["high"].config(text=f"{forecast_values.max():.1f} °C")
        self.forecast_summary_labels["trend"].config(text=trend)
        self.best_model_label.config(
            text=f"Mô hình tốt nhất: {self.forecast_result['best_model']}  •  Đã lưu forecast_results.csv và forecast_metrics.csv",
            fg=self.colors["text"],
            bg=self.colors["success"],
            pady=8,
            padx=14,
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )
        self.selected_key = "forecast"
        self.notebook.select(self.forecast_tab)
        self.render_chart(animate=True)

    def export_csv(self):
        path = self.data_service.export_csv(self.filtered_frame)
        messagebox.showinfo("Đã xuất dữ liệu", f"Đã lưu:\n{path}")

    def choose_csv(self):
        path = filedialog.askopenfilename(title="Chọn dữ liệu thời tiết", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.data_service.load(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Không thể đọc dữ liệu", str(error))
            return
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, self.data_service.date_min.strftime("%Y-%m-%d"))
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, self.data_service.date_max.strftime("%Y-%m-%d"))
        self.refresh_dashboard()
        self.live_label.config(text="●  CSV ĐÃ NẠP", fg=self.colors["success"])

    def export_report(self):
        path = self.data_service.export_report(self.filtered_frame)
        webbrowser.open("file:///" + path.replace("\\", "/"))
        messagebox.showinfo("Đã tạo báo cáo", f"Đã lưu:\n{path}")

    def toggle_theme(self):
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        self.dark_mode = not self.dark_mode
        self.set_colors()
        self.setup_ui()


if __name__ == "__main__":
    root = tk.Tk()
    WeatherDashboard(root)
    root.mainloop()
