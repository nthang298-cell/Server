import os

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.holtwinters import ExponentialSmoothing


class ForecastService:
    """Compare lightweight forecasting models and persist their results."""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.results_dir = os.path.join(base_dir, "results")

    def run(self, series, horizon=30):
        series = pd.Series(series).dropna().astype(float).sort_index()
        if isinstance(series.index, pd.DatetimeIndex):
            series = series.asfreq("D").interpolate().ffill().bfill()
        if len(series) < horizon + 14:
            raise ValueError("Cần ít nhất 44 ngày dữ liệu để đánh giá dự báo.")
        train = series.iloc[:-horizon]
        test = series.iloc[-horizon:]
        forecasts = {
            "Naive": self._naive(train, horizon),
            "Moving average": self._moving_average(train, horizon),
            "Exponential smoothing": self._exponential_smoothing(train, horizon),
        }
        metrics = []
        for name, values in forecasts.items():
            metrics.append({
                "Model": name,
                "MAE": mean_absolute_error(test, values),
                "RMSE": np.sqrt(mean_squared_error(test, values)),
            })
        metrics_frame = pd.DataFrame(metrics).sort_values("RMSE").reset_index(drop=True)
        best_name = metrics_frame.iloc[0]["Model"]
        future_index = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")
        best_future = self._forecast_model(best_name, series, horizon)
        result = pd.DataFrame({"Date": future_index, "Forecast": best_future})
        result["Model"] = best_name
        os.makedirs(self.results_dir, exist_ok=True)
        result.to_csv(os.path.join(self.results_dir, "forecast_results.csv"), index=False)
        metrics_frame.to_csv(os.path.join(self.results_dir, "forecast_metrics.csv"), index=False)
        return {
            "metrics": metrics_frame,
            "future": result,
            "best_model": best_name,
            "test": test,
            "forecasts": forecasts,
        }

    def _forecast_model(self, name, series, horizon):
        if name == "Naive":
            return self._naive(series, horizon)
        if name == "Moving average":
            return self._moving_average(series, horizon)
        return self._exponential_smoothing(series, horizon)

    @staticmethod
    def _naive(series, horizon):
        return np.repeat(series.iloc[-1], horizon)

    @staticmethod
    def _moving_average(series, horizon, window=7):
        return np.repeat(series.iloc[-window:].mean(), horizon)

    @staticmethod
    def _exponential_smoothing(series, horizon):
        try:
            model = ExponentialSmoothing(series, trend="add", seasonal=None, initialization_method="estimated").fit(optimized=True)
            return model.forecast(horizon).to_numpy()
        except (ValueError, np.linalg.LinAlgError):
            return ForecastService._naive(series, horizon)
