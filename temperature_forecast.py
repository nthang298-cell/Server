import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import warnings

from sklearn.metrics import mean_absolute_error, mean_squared_error
from pmdarima import auto_arima
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

warnings.filterwarnings("ignore")

print("=== 5. DU BAO NHIET DO (FINAL) ===")

# =========================
# 1. LOAD DATA
# =========================
df = pd.read_csv('results/cleaned_weather_data.csv',
                 index_col='Date', parse_dates=True)

df = df[~df.index.duplicated()]
df = df.sort_index()

series = df['AvgTemp'].dropna()

# =========================
# 2. ADF TEST
# =========================
print("\n--- ADF TEST ---")
result = adfuller(series)

print("ADF Statistic:", result[0])
print("p-value:", result[1])

if result[1] < 0.05:
    print("→ Chuoi dung (stationary)")
else:
    print("→ Chuoi KHONG dung → ARIMA se sai phan (d)")

# =========================
# 3. ACF / PACF
# =========================
print("\n--- ACF & PACF ---")

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plot_acf(series, ax=plt.gca(), lags=40)
plt.title("ACF")
plt.xlabel('Do tre (Lag)')
plt.ylabel('Tuong quan')

plt.subplot(1, 2, 2)
plot_pacf(series, ax=plt.gca(), lags=40)
plt.title("PACF")
plt.xlabel('Do tre (Lag)')
plt.ylabel('Tuong quan')

plt.tight_layout()

os.makedirs('results', exist_ok=True)
plt.savefig('results/acf_pacf.png', dpi=300)
plt.close()

# =========================
# 4. TRAIN / TEST
# =========================
train = series[:-30]
test = series[-30:]

# =========================
# 5. AUTO ARIMA
# =========================
print("\n--- TRAIN ARIMA ---")

model = auto_arima(
    train,
    seasonal=True,
    m=7,  # chu kỳ tuần
    trace=True,
    error_action='ignore',
    suppress_warnings=True,
    stepwise=True
)

model.fit(train)

print("\nModel:", model.order, model.seasonal_order)

# =========================
# 6. FORECAST
# =========================
forecast, conf_int = model.predict(n_periods=30, return_conf_int=True)

# =========================
# 7. EVALUATION
# =========================
mae = mean_absolute_error(test, forecast)
rmse = np.sqrt(mean_squared_error(test, forecast))

# =========================
# 8. NAIVE MODEL
# =========================
naive_forecast = test.shift(1)
naive_mae = mean_absolute_error(test[1:], naive_forecast[1:])

print("\nMAE ARIMA:", round(mae, 2))
print("MAE Naive:", round(naive_mae, 2))

# =========================
# 9. TREND ANALYSIS
# =========================
def analyze_trend(series):
    diff = series.diff().mean()
    if diff > 0.1:
        return "tăng"
    elif diff < -0.1:
        return "giảm"
    else:
        return "ổn định"

real_trend = analyze_trend(test)
forecast_trend = analyze_trend(pd.Series(forecast, index=test.index))

# =========================
# 10. COMMENT
# =========================
comment = f"""
KET LUAN:

- Xu huong thuc te: {real_trend}
- Xu huong du bao: {forecast_trend}
- MAE (ARIMA): {mae:.2f}
- MAE (Naive): {naive_mae:.2f}
- RMSE: {rmse:.2f}

Danh gia:
- Model {'TOT' if mae < naive_mae else 'CHUA TOT'}
"""

# =========================
# 11. PLOT MAIN
# =========================
plt.figure(figsize=(15, 8))

plt.plot(train.index[-200:], train[-200:], label='Train', alpha=0.5)
plt.plot(test.index, test, label='Thuc te', linewidth=2)
plt.plot(test.index, forecast, '--', label='Du bao', linewidth=2)

plt.fill_between(test.index, conf_int[:, 0], conf_int[:, 1], alpha=0.2)

plt.title('Du bao nhiet do bang ARIMA')
plt.xlabel('Thoi gian')
plt.ylabel('Nhiet do (°C)')
plt.legend()
plt.grid(alpha=0.3)

plt.figtext(0.1, -0.2, comment, fontsize=11)

save_path = os.path.join('results', 'temperature_forecast.png')
plt.savefig(save_path, dpi=300, bbox_inches='tight')

plt.close()

# =========================
# 12. ZOOM FORECAST
# =========================
plt.figure(figsize=(10, 5))
plt.plot(test.index, test, label='Thuc te')
plt.plot(test.index, forecast, label='Du bao')

plt.title('Zoom 30 ngay du bao')
plt.legend()
plt.grid()

plt.savefig('results/forecast_zoom.png', dpi=300)
plt.close()

# =========================
# 13. INSIGHT
# =========================
print("\n--- INSIGHT ---")

# 🌡️ Xu hướng nhiệt độ
if real_trend == "tăng":
    print("Nhiet do co xu huong tang theo thoi gian.")
elif real_trend == "giảm":
    print("Nhiet do co xu huong giam theo thoi gian.")
else:
    print("Nhiet do tuong doi on dinh.")

# 🌧️ Rainfall skewness
skew = df['Rainfall'].skew()

if skew > 1:
    print("Luong mua co phan phoi lech phai ro rang (nhieu ngay khong mua, mot so ngay mua lon).")
else:
    print("Luong mua phan bo tuong doi deu.")

# 🤖 Đánh giá model
if mae < naive_mae:
    print("ARIMA tot hon mo hinh naive trong du bao ngan han.")
else:
    print("ARIMA chua tot hon mo hinh naive.")

# 📉 Độ chính xác
if mae < 2:
    print("Do chinh xac cao.")
elif mae < 4:
    print("Do chinh xac trung binh.")
else:
    print("Do chinh xac thap.")

print(comment)

print("\n=== HOAN THANH FILE 5 (FINAL) ===")











#“Mô hình ARIMA dự báo được xu hướng ổn định của nhiệt độ, tuy nhiên chưa bắt được các biến động mạnh trong dữ liệu thực tế.”
