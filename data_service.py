import os
from datetime import datetime

import numpy as np
import pandas as pd


class WeatherDataService:
    """Load, filter, summarize, validate, and export weather observations."""

    REQUIRED_COLUMNS = [
        "Date",
        "MinTemp",
        "MaxTemp",
        "Rainfall",
        "Humidity9am",
        "Humidity3pm",
    ]
    DISPLAY_COLUMNS = [
        "Date",
        "MinTemp",
        "MaxTemp",
        "AvgTemp",
        "Rainfall",
        "Humidity9am",
        "Humidity3pm",
    ]

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.raw_path = os.path.join(base_dir, "Rainfall dataset.csv")
        self.cleaned_path = os.path.join(base_dir, "results", "cleaned_weather_data.csv")
        self.results_dir = os.path.join(base_dir, "results")
        self.data = pd.DataFrame()
        self.load()

    def load(self, source_path=None):
        path = source_path or (self.cleaned_path if os.path.exists(self.cleaned_path) else self.raw_path)
        frame = pd.read_csv(path)
        missing = [column for column in self.REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise ValueError("Thiếu cột bắt buộc: " + ", ".join(missing))
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        frame = frame.dropna(subset=["Date"]).copy()
        for column in self.REQUIRED_COLUMNS[1:]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = frame.drop_duplicates(subset="Date").sort_values("Date")
        frame = frame[frame["MinTemp"].isna() | frame["MaxTemp"].isna() | (frame["MinTemp"] <= frame["MaxTemp"])]
        frame["AvgTemp"] = (frame["MinTemp"] + frame["MaxTemp"]) / 2
        frame = frame.set_index("Date")
        numeric = ["MinTemp", "MaxTemp", "AvgTemp", "Rainfall", "Humidity9am", "Humidity3pm"]
        frame[numeric] = frame[numeric].interpolate(method="time").ffill().bfill()
        self.data = frame
        return self.data

    @property
    def date_min(self):
        return self.data.index.min()

    @property
    def date_max(self):
        return self.data.index.max()

    def filter(self, start_date=None, end_date=None):
        frame = self.data
        if start_date:
            frame = frame[frame.index >= pd.Timestamp(start_date)]
        if end_date:
            frame = frame[frame.index <= pd.Timestamp(end_date)]
        return frame

    def summary(self, frame=None):
        frame = self.data if frame is None else frame
        if frame.empty:
            return {"days": 0, "avg_temp": np.nan, "max_temp": np.nan, "min_temp": np.nan, "rainfall": np.nan, "humidity": np.nan}
        return {
            "days": len(frame),
            "avg_temp": frame["AvgTemp"].mean(),
            "max_temp": frame["MaxTemp"].max(),
            "min_temp": frame["MinTemp"].min(),
            "rainfall": frame["Rainfall"].sum(),
            "humidity": frame[["Humidity9am", "Humidity3pm"]].mean().mean(),
        }

    def alerts(self, frame=None):
        frame = self.data if frame is None else frame
        alerts = []
        if frame.empty:
            return alerts
        hot_days = int((frame["MaxTemp"] >= 35).sum())
        wet_days = int((frame["Rainfall"] >= 50).sum())
        humid_days = int((frame["Humidity3pm"] >= 90).sum())
        extreme_rain = float(frame["Rainfall"].max()) if not frame["Rainfall"].empty else 0
        avg_temp = float(frame["AvgTemp"].mean()) if not frame["AvgTemp"].empty else 0

        if hot_days:
            alerts.append(("Nắng nóng", f"{hot_days} ngày có nhiệt độ tối đa từ 35°C", "warning"))
        if wet_days:
            alerts.append(("Mưa lớn", f"{wet_days} ngày có lượng mưa từ 50 mm", "danger"))
        if humid_days:
            alerts.append(("Độ ẩm cao", f"{humid_days} ngày có độ ẩm chiều từ 90%", "info"))
        if avg_temp > 30:
            alerts.append(("Nhiệt độ cao bất thường", f"Nhiệt độ trung bình là {avg_temp:.1f}°C, trên ngưỡng cảnh báo", "warning"))
        if extreme_rain > 100:
            alerts.append(("Có mưa cực đoan", f"Lượng mưa tối đa là {extreme_rain:.1f} mm trong khoảng dữ liệu", "danger"))
        if not alerts:
            alerts.append(("Ổn định", "Không phát hiện cảnh báo theo ngưỡng hiện tại", "success"))
        return alerts

    def outlier_summary(self, frame=None):
        frame = self.data if frame is None else frame
        if frame.empty:
            return {"before": {}, "after": {}}

        columns = [
            "MinTemp",
            "MaxTemp",
            "AvgTemp",
            "Rainfall",
            "Humidity9am",
            "Humidity3pm",
        ]

        def iqr_stats(series):
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            low = int((series < lower).sum())
            high = int((series > upper).sum())
            return {
                "lower": lower,
                "upper": upper,
                "total": low + high,
                "low": low,
                "high": high,
            }

        before = {}
        after = {}

        for col in columns:
            stats = iqr_stats(frame[col].copy())
            before[col] = stats
            if col == "Rainfall":
                rainfall_log = np.log1p(frame[col].copy())
                log_stats = iqr_stats(rainfall_log)
                after[col] = log_stats
            else:
                processed = frame[col].copy()
                if col in ["MinTemp", "MaxTemp", "AvgTemp"]:
                    processed = processed.clip(stats["lower"], stats["upper"])
                else:
                    processed = processed.clip(stats["lower"], stats["upper"])
                after[col] = iqr_stats(processed)

        return {"before": before, "after": after}

    def table_rows(self, frame=None, limit=300):
        frame = self.data if frame is None else frame
        rows = frame.reset_index().sort_values("Date", ascending=False).head(limit)
        result = []
        for _, row in rows.iterrows():
            result.append(tuple(
                row[column].strftime("%Y-%m-%d") if column == "Date" else f"{row[column]:.1f}"
                for column in self.DISPLAY_COLUMNS
            ))
        return result

    def export_csv(self, frame=None):
        os.makedirs(self.results_dir, exist_ok=True)
        path = os.path.join(self.results_dir, "filtered_weather_data.csv")
        (self.data if frame is None else frame).reset_index().to_csv(path, index=False)
        return path

    def export_report(self, frame=None):
        frame = self.data if frame is None else frame
        summary = self.summary(frame)
        path = os.path.join(self.results_dir, "weather_report.html")
        rows = "".join(f"<tr><td>{key}</td><td>{value:.2f}</td></tr>" if isinstance(value, float) else f"<tr><td>{key}</td><td>{value}</td></tr>" for key, value in summary.items())
        frame.reset_index().tail(100).to_html(path, index=False)
        with open(path, "r", encoding="utf-8") as existing:
            table = existing.read()
        html = f"<html><head><meta charset='utf-8'><title>Weather report</title></head><body><h1>Weather Analyst report</h1><table>{rows}</table>{table}</body></html>"
        with open(path, "w", encoding="utf-8") as report:
            report.write(html)
        return path
