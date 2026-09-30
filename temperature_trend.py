import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

print("=== 2. PHAN TICH XU HUONG NHIET DO ===")

# =========================
# 1. Đọc dữ liệu
# =========================
df = pd.read_csv('results/cleaned_weather_data.csv', index_col='Date', parse_dates=True)

# =========================
# 2. Tạo đường xu hướng (smoothing)
# =========================
df['Temp_MA7'] = df['AvgTemp'].rolling(window=7).mean()
df['Temp_MA30'] = df['AvgTemp'].rolling(window=30).mean()

# =========================
# 3. Resample theo tháng và năm
# =========================
monthly = df.resample('ME').mean()
yearly = df.resample('YE').mean()

# =========================
# 4. Tính toán đánh giá xu hướng
# =========================
avg_temp_mean = round(df['AvgTemp'].mean(), 2)
min_temp_mean = round(df['MinTemp'].mean(), 2)
max_temp_mean = round(df['MaxTemp'].mean(), 2)

daily_start = df['AvgTemp'].dropna().iloc[0]
daily_end = df['AvgTemp'].dropna().iloc[-1]

ma7_start = df['Temp_MA7'].dropna().iloc[0]
ma7_end = df['Temp_MA7'].dropna().iloc[-1]

ma30_start = df['Temp_MA30'].dropna().iloc[0]
ma30_end = df['Temp_MA30'].dropna().iloc[-1]

monthly_start = monthly['AvgTemp'].dropna().iloc[0]
monthly_end = monthly['AvgTemp'].dropna().iloc[-1]

yearly_start = yearly['AvgTemp'].dropna().iloc[0]
yearly_end = yearly['AvgTemp'].dropna().iloc[-1]

yearly_diff = round(yearly_end - yearly_start, 2)
monthly_diff = round(monthly_end - monthly_start, 2)
ma30_diff = round(ma30_end - ma30_start, 2)

if yearly_diff > 0:
    yearly_trend = "TANG"
else:
    yearly_trend = "GIAM"

if monthly_diff > 0:
    monthly_trend = "TANG"
else:
    monthly_trend = "GIAM"

if ma30_diff > 0:
    smooth_trend = "TANG"
else:
    smooth_trend = "GIAM"

analysis_text = (
    f"Danh gia: Nhiet do trung binh toan bo la {avg_temp_mean} C. "
    f"MinTemp trung binh {min_temp_mean} C, MaxTemp trung binh {max_temp_mean} C. "
    f"Theo duong MA30, nhiet do co xu huong {smooth_trend} "
    f"({round(ma30_start, 2)} C -> {round(ma30_end, 2)} C). "
    f"Theo thang, xu huong {monthly_trend} ({round(monthly_start, 2)} C -> {round(monthly_end, 2)} C). "
    f"Theo nam, xu huong {yearly_trend} ({round(yearly_start, 2)} C -> {round(yearly_end, 2)} C, chenhlech {yearly_diff} C)."
)

# =========================
# 5. Vẽ biểu đồ
# =========================
plt.figure(figsize=(14, 12))

# ---- Biểu đồ 1: Xu hướng theo ngày + smoothing ----
plt.subplot(3, 1, 1)
plt.plot(df.index, df['AvgTemp'], label='Nhiet do trung binh (raw)', alpha=0.3)
plt.plot(df.index, df['Temp_MA7'], label='Trung binh 7 ngay', linewidth=2)
plt.plot(df.index, df['Temp_MA30'], label='Trung binh 30 ngay', linewidth=2)
plt.title('Xu huong Nhiet do theo ngay (co smoothing)')
plt.xlabel('Thoi gian')
plt.ylabel('Nhiet do (C)')
plt.legend()
plt.grid(True, alpha=0.3)

# ---- Biểu đồ 2: Theo tháng ----
plt.subplot(3, 1, 2)
plt.plot(monthly.index, monthly['MinTemp'], label='MinTemp')
plt.plot(monthly.index, monthly['MaxTemp'], label='MaxTemp')
plt.plot(monthly.index, monthly['AvgTemp'], label='AvgTemp', linewidth=2)
plt.title('Xu huong Nhiet do theo thang')
plt.xlabel('Thoi gian (Thang)')
plt.ylabel('Nhiet do (C)')
plt.legend()
plt.grid(True, alpha=0.3)

# ---- Biểu đồ 3: Theo năm ----
plt.subplot(3, 1, 3)
plt.plot(yearly.index, yearly['AvgTemp'], marker='o', linewidth=2)
plt.title('Xu huong Nhiet do trung binh theo nam')
plt.xlabel('Thoi gian (Nam)')
plt.ylabel('Nhiet do (C)')
plt.grid(True, alpha=0.3)

plt.figtext(
    0.5,
    0.02,
    analysis_text,
    ha='center',
    fontsize=10,
    wrap=True
)

plt.tight_layout(rect=[0, 0.08, 1, 1])

# =========================
# 6. Lưu file
# =========================
os.makedirs('results', exist_ok=True)
save_path = os.path.join('results', 'temperature_trend.png')

plt.savefig(save_path, dpi=300, bbox_inches='tight')
plt.close()

print("Da luu bieu do:", save_path)

# =========================
# 7. Nhận xét chi tiết
# =========================
print("\n--- NHAN XET CHI TIET ---")

print("\n1. Danh gia theo ngay:")
print("- Du lieu nhiet do theo ngay co the dao dong manh do anh huong cua thoi tiet ngan han.")
print("- Duong raw the hien bien dong truc tiep cua AvgTemp theo tung ngay.")
print("- Duong trung binh 7 ngay giup lam muot bien dong ngan han.")
print("- Duong trung binh 30 ngay the hien xu huong dai hon va on dinh hon.")
print(f"- Theo MA30, nhiet do co xu huong {smooth_trend}: {round(ma30_start, 2)} C -> {round(ma30_end, 2)} C.")

print("\n2. Danh gia theo thang:")
print("- Bieu do theo thang giup quan sat ro hon tinh mua vu va thay doi nhiet do trong nam.")
print("- MaxTemp thuong nam cao nhat, MinTemp thap nhat, AvgTemp nam o giua hai duong nay.")
print(f"- Nhiet do trung binh theo thang co xu huong {monthly_trend}: {round(monthly_start, 2)} C -> {round(monthly_end, 2)} C.")

print("\n3. Danh gia theo nam:")
print("- Bieu do theo nam giup danh gia xu huong dai han cua nhiet do trung binh.")
print(f"- Nam dau tien co AvgTemp trung binh khoang {round(yearly_start, 2)} C.")
print(f"- Nam cuoi cung co AvgTemp trung binh khoang {round(yearly_end, 2)} C.")
print(f"- Chenh lech giua nam cuoi va nam dau la {yearly_diff} C.")
print(f"- Ket luan: Nhiet do co xu huong {yearly_trend} theo nam.")

print("\n4. Danh gia theo tung bien nhiet do:")
print(f"- MinTemp trung binh: {min_temp_mean} C, dai dien cho muc nhiet thap nhat trong ngay.")
print(f"- MaxTemp trung binh: {max_temp_mean} C, dai dien cho muc nhiet cao nhat trong ngay.")
print(f"- AvgTemp trung binh: {avg_temp_mean} C, phan anh dieu kien nhiet do chung.")
print("- Khoang cach giua MinTemp va MaxTemp cho thay bien do dao dong nhiet trong ngay.")

print("\n=== HOAN THANH FILE 2 (BAN CHUAN) ===")







#sử dụng rolling mean 7 ngày và 30 ngày để làm mượt dữ liệu,
# giúp quan sát xu hướng nhiệt độ rõ ràng hơn thay vì bị nhiễu bởi biến động ngắn hạn
