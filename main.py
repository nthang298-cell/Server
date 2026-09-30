# main.py
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

if PYTHON == VENV_PYTHON and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(VENV_PYTHON)):
    print("Se dung Python trong .venv cho cac buoc phan tich...")

os.chdir(BASE_DIR)
os.makedirs(RESULTS_DIR, exist_ok=True)


def run_script(script_name, description):
    print("=" * 80)
    print("DANG CHAY: " + script_name)
    print("Mo ta: " + description)
    print("=" * 80)

    try:
        script_path = os.path.join(BASE_DIR, script_name)
        subprocess.run([PYTHON, script_path], check=True, cwd=BASE_DIR)
        print("HOAN THANH: " + script_name + "\n")
        return True
    except subprocess.CalledProcessError:
        print("LOI khi chay " + script_name)
        return False
    except FileNotFoundError:
        print("Khong tim thay file: " + script_name)
        return False


def main():
    print("BAT DAU DU AN PHAN TICH DU LIEU THOI TIET")
    print("Yeu cau: Xu ly du lieu thoi gian - Xu huong - Outlier - Truc quan - Du bao\n")

    scripts = [
        ("data_preprocessing.py", "Xu ly du lieu thoi gian va lam sach du lieu"),
        ("temperature_trend.py", "Phan tich xu huong nhiet do"),
        ("outlier_detection.py", "Phat hien bat thuong (Outlier)"),
        ("visualization_linechart.py", "Truc quan hoa bang Line Chart"),
        ("temperature_forecast.py", "Du bao nhiet do bang Time Series")
    ]

    success = True
    for script, desc in scripts:
        script_path = os.path.join(BASE_DIR, script)
        if os.path.exists(script_path):
            if not run_script(script, desc):
                success = False
                break
        else:
            print("Canh bao: File " + script + " khong ton tai!")
            success = False
            break

    print("=" * 80)
    if success:
        print("HOAN THANH TOAN BO PHAN TICH!")
        print("Tat ca ket qua da duoc luu trong thu muc: results/")

        if "--no-dashboard" in sys.argv:
            print("Da bo qua Dashboard theo tuy chon --no-dashboard.")
            print("=" * 80)
            return

        print("\nDang mo Dashboard...")

        # Tự động mở Dashboard Tkinter sau khi phân tích xong
        time.sleep(1)  # Đợi 1 giây cho gọn
        try:
            dashboard_path = os.path.join(BASE_DIR, "dashboard_tkinter.py")
            subprocess.run([PYTHON, dashboard_path], cwd=BASE_DIR)
        except Exception as e:
            print("Khong the mo Dashboard: " + str(e))
            print("Ban co the chay thu cong bang lenh: python dashboard_tkinter.py")
    else:
        print("CO LOI XAY RA trong qua trinh phan tich!")

    print("=" * 80)


if __name__ == "__main__":
    main()
