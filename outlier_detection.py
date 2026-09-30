import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os

print("=== 3. PHAT HIEN VA XU LY OUTLIER ===")
print("\n[PHASE 1] BEFORE OUTLIER PROCESSING")

# ==============================
# 1. Đọc dữ liệu
# ==============================
df = pd.read_csv(
    'results/cleaned_weather_data.csv',
    index_col='Date',
    parse_dates=True
)

cols = [
    'MinTemp',
    'MaxTemp',
    'AvgTemp',
    'Rainfall',
    'Humidity9am',
    'Humidity3pm'
]

# ==============================
# 2. Phát hiện outlier trước xử lý
# ==============================

def analyze_iqr(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    low_mask = series < lower
    high_mask = series > upper
    total = int((low_mask | high_mask).sum())
    low_count = int(low_mask.sum())
    high_count = int(high_mask.sum())

    return {
        'lower': lower,
        'upper': upper,
        'total': total,
        'low_count': low_count,
        'high_count': high_count,
    }


print("\n--- PHÂN TÍCH OUTLIER TRƯỚC KHI XỬ LÝ ---")
print("=> GIAI ĐOẠN BEFORE: Chưa xử lý dữ liệu bất thường")
outlier_bounds_before = {}
outlier_count_before = {}

for col in cols:
    stats = analyze_iqr(df[col])
    outlier_bounds_before[col] = (stats['lower'], stats['upper'])
    outlier_count_before[col] = stats['total']
    print(
        f"{col:<12}: {stats['total']:>5} outliers "
        f"(thấp={stats['low_count']}, cao={stats['high_count']})"
    )

# ==============================
# 3. Xử lý outlier
# ==============================
print("\n--- XỬ LÝ OUTLIER ---")
print("=> Đang áp dụng IQR + log transform + capping...")

df_processed = df.copy()

# Rainfall -> log transform trước khi capping
if 'Rainfall' in df_processed.columns:
    df_processed['Rainfall_log'] = np.log1p(df_processed['Rainfall'])

# Temp và humidity: capping theo IQR
for col in ['MinTemp', 'MaxTemp', 'AvgTemp']:
    lower, upper = outlier_bounds_before[col]
    df_processed[col] = df_processed[col].clip(lower, upper)

for col in ['Humidity9am', 'Humidity3pm']:
    lower, upper = outlier_bounds_before[col]
    df_processed[col] = df_processed[col].clip(lower, upper)

# Rainfall_log: áp dụng capping sau khi log transform
Q1_log = df_processed['Rainfall_log'].quantile(0.25)
Q3_log = df_processed['Rainfall_log'].quantile(0.75)
IQR_log = Q3_log - Q1_log

rain_log_lower = Q1_log - 1.5 * IQR_log
rain_log_upper = Q3_log + 1.5 * IQR_log

df_processed['Rainfall_log'] = df_processed['Rainfall_log'].clip(rain_log_lower, rain_log_upper)

print("Da xu ly outlier thanh cong!")

# ==============================
# 4. Đếm lại outlier sau xử lý
# ==============================
print("\n--- PHÂN TÍCH OUTLIER SAU KHI XỬ LÝ ---")
print("=> GIAI ĐOẠN AFTER: Sau khi xử lý dữ liệu bất thường")

cols_after = [
    'MinTemp',
    'MaxTemp',
    'AvgTemp',
    'Rainfall_log',
    'Humidity9am',
    'Humidity3pm'
]

outlier_bounds_after = {
    'MinTemp': outlier_bounds_before['MinTemp'],
    'MaxTemp': outlier_bounds_before['MaxTemp'],
    'AvgTemp': outlier_bounds_before['AvgTemp'],
    'Rainfall_log': (rain_log_lower, rain_log_upper),
    'Humidity9am': outlier_bounds_before['Humidity9am'],
    'Humidity3pm': outlier_bounds_before['Humidity3pm'],
}

outlier_count_after = {}
for col in cols_after:
    lower, upper = outlier_bounds_after[col]
    series = df_processed[col]
    low_mask = series < lower
    high_mask = series > upper
    total = int((low_mask | high_mask).sum())
    low_count = int(low_mask.sum())
    high_count = int(high_mask.sum())
    outlier_count_after[col] = total
    print(
        f"{col:<12}: {total:>5} outliers "
        f"(thấp={low_count}, cao={high_count})"
    )

# ==============================
# 5. Vẽ biểu đồ trước và sau khi xử lý
# ==============================
os.makedirs('results', exist_ok=True)

# 5.1 Boxplot trước xử lý
plt.figure(figsize=(12, 8))
sns.boxplot(data=df[cols])
plt.title('Boxplot BEFORE OUTLIER - Trước khi xử lý outlier')
plt.xlabel('Biến (các chỉ số thời tiết)')
plt.ylabel('Giá trị')
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.figtext(
    0.5,
    0.02,
    "Chu thich bien: MinTemp = nhiet do thap nhat, MaxTemp = nhiet do cao nhat, AvgTemp = nhiet do trung binh, "
    "Rainfall = luong mua goc, Humidity9am = do am luc 9h sang, Humidity3pm = do am luc 3h chieu.\n"
    "Danh gia: Bieu do cho thay mot so diem nam ngoai whisker la outlier theo IQR. Rainfall co so luong outlier cao nhat "
    "do phan phoi lech phai, nhieu ngay mua it va mot so ngay mua rat lon.",
    ha='center',
    fontsize=9,
    wrap=True,
)
plt.tight_layout(rect=[0, 0.20, 1, 1])
plt.savefig('results/boxplot_before_outlier.png', dpi=300)
plt.close()

# 5.2 Boxplot sau xử lý
plt.figure(figsize=(12, 8))
sns.boxplot(data=df_processed[cols_after])
plt.title('Boxplot AFTER OUTLIER - Sau khi xử lý outlier')
plt.xlabel('Biến (các chỉ số thời tiết)')
plt.ylabel('Giá trị')
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.figtext(
    0.5,
    0.02,
    "Chu thich bien: MinTemp = nhiet do thap nhat, MaxTemp = nhiet do cao nhat, AvgTemp = nhiet do trung binh, "
    "Rainfall_log = luong mua sau log1p va capping, Humidity9am = do am luc 9h sang, Humidity3pm = do am luc 3h chieu.\n"
    "Danh gia: Sau khi xu ly, nhiet do va do am duoc capping theo ngưong IQR. Rainfall duoc bien doi log1p va ap dung capping "
    "de giam anh huong cua gia tri cuc dai, giu lai xu huong tong the.",
    ha='center',
    fontsize=9,
    wrap=True,
)
plt.tight_layout(rect=[0, 0.22, 1, 1])
plt.savefig('results/boxplot_after_outlier.png', dpi=300)
plt.close()

# 5.3 Histogram Rainfall_log sau xử lý
plt.figure(figsize=(10, 8))
sns.histplot(df_processed['Rainfall_log'], bins=100, kde=True)
plt.title('Phân phối Rainfall_log sau log transform và capping')
plt.xlabel('Lượng mưa sau log1p và capping')
plt.ylabel('Tần suất')
plt.grid(True, alpha=0.3)
plt.figtext(
    0.5,
    0.02,
    "Chu thich bien: Rainfall_log = log1p(Rainfall), sau do duoc capping theo IQR.\n"
    "Danh gia: Log transform giup giam do lech phai cua Rainfall, trong khi capping giup loai bo cac gia tri cuc tri con lai.",
    ha='center',
    fontsize=9,
    wrap=True,
)
plt.tight_layout(rect=[0, 0.22, 1, 1])
plt.savefig('results/rainfall_log_distribution.png', dpi=300)
plt.close()

# ==============================
# 6. Lưu dữ liệu xử lý
# ==============================
output_path = 'results/processed_weather_data.csv'
df_processed.to_csv(output_path)
print("\nDa luu file xu ly:", output_path)

# ==============================
# 7. Kết luận
# ==============================
print("\n--- KET LUAN ---")
print("- Rainfall co nhieu outlier do pha tan lech phai va so ngay khong mua.")
print("- Rainfall duoc xu ly bang log transform va capping de giam anh huong cua gia tri cực lớn.")
print("- Nhiệt độ va độ ẩm duoc xu ly bang capping theo IQR.")
print("- Sau khi xu ly, bieu do sau khi chuyen hoa cho thay phan bo giau duoc on dinh hon.")
print("\n=== HOAN THANH FILE 3 ===")

# Ghi chú tham khảo:
# Dữ liệu lượng mưa có phân phối lệch phải, nên sử dụng log transform để giảm ảnh hưởng của các giá trị cực lớn,
# trong khi nhiệt độ và độ ẩm được xử lý bằng IQR capping để giữ lại xu hướng tổng thể của dữ liệu.
