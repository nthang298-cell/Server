import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

print("=== 4. TRUC QUAN HOA BANG LINE CHART (BAN CHUAN) ===")

# =========================
# 1. LOAD DATA
# =========================
df = pd.read_csv(
    'results/cleaned_weather_data.csv',
    index_col='Date',
    parse_dates=True
)

# =========================
# 2. RESAMPLE THEO THANG
# =========================
monthly = df.resample('ME').mean()

# =========================
# 3. SMOOTHING (ROLLING)
# =========================
monthly['Temp_MA3'] = monthly['AvgTemp'].rolling(3).mean()
monthly['Rain_MA3'] = monthly['Rainfall'].rolling(3).mean()

# =========================
# 4. TINH TOAN NHAN XET TU DONG
# =========================
temp_start = monthly['Temp_MA3'].dropna().iloc[0]
temp_end = monthly['Temp_MA3'].dropna().iloc[-1]
temp_diff = temp_end - temp_start

rain_start = monthly['Rain_MA3'].dropna().iloc[0]
rain_end = monthly['Rain_MA3'].dropna().iloc[-1]
rain_diff = rain_end - rain_start

humidity9_mean = monthly['Humidity9am'].mean()
humidity3_mean = monthly['Humidity3pm'].mean()
humidity_diff = humidity9_mean - humidity3_mean

temp_threshold = 0.5
rain_threshold = 1.0
humidity_threshold = 2.0

if temp_diff > temp_threshold:
    temp_comment = (
        f"Nhiet do co xu huong tang ({temp_start:.2f} C -> {temp_end:.2f} C). "
        "Dieu nay cho thay giai doan cuoi co muc nhiet cao hon giai doan dau."
    )
elif temp_diff < -temp_threshold:
    temp_comment = (
        f"Nhiet do co xu huong giam ({temp_start:.2f} C -> {temp_end:.2f} C). "
        "Dieu nay cho thay giai doan cuoi mat hon giai doan dau."
    )
else:
    temp_comment = (
        f"Nhiet do tuong doi on dinh ({temp_start:.2f} C -> {temp_end:.2f} C). "
        "Bien dong tong the khong qua lon."
    )

if rain_diff > rain_threshold:
    rain_comment = (
        f"Luong mua co xu huong tang ({rain_start:.2f} mm -> {rain_end:.2f} mm). "
        "Cac thang ve sau co muc mua trung binh cao hon."
    )
elif rain_diff < -rain_threshold:
    rain_comment = (
        f"Luong mua co xu huong giam ({rain_start:.2f} mm -> {rain_end:.2f} mm). "
        "Cac thang ve sau co muc mua trung binh thap hon."
    )
else:
    rain_comment = (
        f"Luong mua khong co xu huong tang/giam ro rang ({rain_start:.2f} mm -> {rain_end:.2f} mm). "
        "Du lieu mua bien dong khong deu theo tung thang."
    )

if humidity_diff > humidity_threshold:
    humidity_comment = (
        f"Do am buoi sang cao hon buoi chieu trung binh {humidity_diff:.2f}%. "
        "Day la hien tuong hop ly vi buoi sang thuong mat hon va hoi nuoc chua bay hoi manh."
    )
elif humidity_diff < -humidity_threshold:
    humidity_comment = (
        f"Do am buoi chieu cao hon buoi sang trung binh {abs(humidity_diff):.2f}%. "
        "Truong hop nay co the xay ra khi khu vuc co mua hoac hoi am tang vao buoi chieu."
    )
else:
    humidity_comment = (
        f"Do am buoi sang va buoi chieu gan tuong duong nhau, chenh lech khoang {abs(humidity_diff):.2f}%. "
        "Muc do am trong ngay kha on dinh."
    )

summary_text = (
    "Danh gia: "
    + temp_comment
    + " "
    + rain_comment
    + " "
    + humidity_comment
)

# =========================
# 5. VẼ BIỂU ĐỒ
# =========================
plt.figure(figsize=(15, 12))

# ---- Nhiệt độ ----
plt.subplot(3, 1, 1)
plt.plot(monthly.index, monthly['MinTemp'], label='MinTemp', alpha=0.5)
plt.plot(monthly.index, monthly['MaxTemp'], label='MaxTemp', alpha=0.5)
plt.plot(monthly.index, monthly['AvgTemp'], label='AvgTemp', linewidth=2)
plt.plot(
    monthly.index,
    monthly['Temp_MA3'],
    '--',
    label='AvgTemp (MA3)',
    linewidth=2
)
plt.title('Xu huong Nhiet do theo thoi gian')
plt.xlabel('Thoi gian')
plt.ylabel('Nhiet do (°C)')
plt.legend()
plt.grid(True, alpha=0.3)

# ---- Lượng mưa ----
plt.subplot(3, 1, 2)
plt.plot(monthly.index, monthly['Rainfall'], label='Rainfall', alpha=0.4)
plt.plot(monthly.index, monthly['Rain_MA3'], label='Rainfall (MA3)', linewidth=2)
plt.title('Xu huong Luong mua')
plt.xlabel('Thoi gian')
plt.ylabel('Luong mua (mm)')
plt.legend()
plt.grid(True, alpha=0.3)

# ---- Độ ẩm ----
plt.subplot(3, 1, 3)
plt.plot(monthly.index, monthly['Humidity9am'], label='Humidity 9am')
plt.plot(monthly.index, monthly['Humidity3pm'], label='Humidity 3pm')
plt.title('Xu huong Do am')
plt.xlabel('Thoi gian')
plt.ylabel('Do am (%)')
plt.legend()
plt.grid(True, alpha=0.3)

plt.figtext(
    0.5,
    0.02,
    summary_text,
    ha='center',
    fontsize=9,
    wrap=True
)

plt.tight_layout(rect=[0, 0.10, 1, 1])

# =========================
# 6. SAVE
# =========================
os.makedirs('results', exist_ok=True)
save_path = os.path.join('results', 'weather_line_charts.png')

plt.savefig(save_path, dpi=300, bbox_inches='tight')
plt.close()

print("Da luu bieu do:", save_path)

# =========================
# 7. NHẬN XÉT CHI TIẾT
# =========================
print("\n--- NHAN XET CHI TIET ---")

print("\n1. Phan tich xu huong nhiet do:")
print(temp_comment)
print("- Duong AvgTemp the hien nhiet do trung binh theo thang.")
print("- Duong AvgTemp (MA3) la trung binh truot 3 thang, giup lam muot du lieu va de nhin xu huong hon.")
print("- MinTemp va MaxTemp cho thay khoang dao dong nhiet do trong tung thang.")

print("\n2. Phan tich xu huong luong mua:")
print(rain_comment)
print("- Rainfall theo thang co the dao dong manh do mua thuong khong phan bo deu.")
print("- Rainfall (MA3) giup giam nhieu bien dong dot ngot va the hien xu huong mua ro hon.")

print("\n3. Phan tich xu huong do am:")
print(humidity_comment)
print("- Humidity9am va Humidity3pm duoc dung de so sanh do am giua buoi sang va buoi chieu.")
print("- Neu do am buoi sang cao hon, dieu nay thuong hop ly vi nhiet do sang som thap hon.")
print("- Neu do am buoi chieu cao hon, co the do mua, may am hoac dieu kien thoi tiet dac biet.")

print("\n4. Y nghia rolling mean 3 thang:")
print("- Rolling mean 3 thang giup lam muot du lieu.")
print("- Cach nay giup giam anh huong cua cac bien dong ngan han.")
print("- Nho do, xu huong theo mua hoac xu huong dai hon duoc the hien ro hon.")







#sử dụng rolling mean 3 tháng để làm mượt dữ liệu,
# giúp dễ quan sát xu hướng theo mùa thay vì các biến động ngắn hạn
