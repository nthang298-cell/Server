import pandas as pd
import numpy as np
import os

print("=== XU LY DU LIEU THOI GIAN ===")

# 1. Đọc dữ liệu

df = pd.read_csv('Rainfall dataset.csv')

print("\nSo dong ban dau:", len(df))


# 2. Chuyển đổi Date

df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# Xóa dữ liệu lỗi Date
df = df.dropna(subset=['Date'])

# Sắp xếp theo thời gian
df = df.sort_values('Date')


# 3. Xóa dữ liệu trùng

before = len(df)
df = df.drop_duplicates(subset='Date')
after = len(df)

print(f"Da xoa {before - after} dong trung lap")

# 4. Kiểm tra logic dữ liệu

# Xóa dòng có MinTemp > MaxTemp
df = df[df['MinTemp'] <= df['MaxTemp']]

# Giới hạn độ ẩm hợp lệ (0 - 100)
df = df[(df['Humidity9am'] >= 0) & (df['Humidity9am'] <= 100)]
df = df[(df['Humidity3pm'] >= 0) & (df['Humidity3pm'] <= 100)]

# 5. Feature Engineering
df['AvgTemp'] = (df['MinTemp'] + df['MaxTemp']) / 2.0

# 6. Set index thời gian
df = df.set_index('Date')

# Đảm bảo dữ liệu liên tục theo ngày
df = df.asfreq('D')

# 7. Xử lý giá trị thiếu
main_cols = ['MinTemp', 'MaxTemp', 'AvgTemp', 'Rainfall', 'Humidity9am', 'Humidity3pm']

df_clean = df[main_cols].copy()

print("\nSo gia tri thieu truoc khi xu ly:")
print(df_clean.isnull().sum())

# Nội suy theo thời gian (chuẩn cho time series)
df_clean = df_clean.interpolate(method='time')

# Fill giá trị còn lại bằng trung bình
df_clean = df_clean.fillna(df_clean.mean())

print("\nSo gia tri thieu sau khi xu ly:")
print(df_clean.isnull().sum())

# 8. Phát hiện outlier
Q1 = df_clean.quantile(0.25)
Q3 = df_clean.quantile(0.75)
IQR = Q3 - Q1

outliers = ((df_clean < (Q1 - 1.5 * IQR)) | (df_clean > (Q3 + 1.5 * IQR)))
outlier_count = outliers.sum()

print("\nSo luong outlier (de tham khao):")
print(outlier_count)

# 9. Lưu file
os.makedirs('results', exist_ok=True)
output_path = os.path.join('results', 'cleaned_weather_data.csv')

df_clean.to_csv(output_path)

# 10. Thống kê cuối
print("\nTong so ngay du lieu:", len(df_clean))

print("\nThong ke sau khi lam sach:")
print(df_clean.describe())

print("\n=== HOAN THANH FILE 1 (BAN CHUAN) ===")