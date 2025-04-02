import tkinter as tk
from tkinter import ttk
import traceback
import sys

try:
    # 가장 기본적인 창 생성
    root = tk.Tk()
    root.title("냉각 시스템 입력창")
    root.geometry("400x300")

    # 간단한 레이블 추가
    label = ttk.Label(root, text="F.W. Inlet Temp (T4):")
    label.pack(pady=20)

    # 입력 필드 추가
    entry = ttk.Entry(root, width=15)
    entry.pack(pady=10)
    entry.insert(0, "38.0")

    # 버튼 추가
    button = ttk.Button(root, text="적용")
    button.pack(pady=20)

    # 메인 루프 실행
    root.mainloop()
except Exception as e:
    # 오류 발생 시 로그 파일에 기록
    with open("error_log.txt", "w") as f:
        f.write(f"오류 발생: {str(e)}\n")
        f.write(traceback.format_exc())
    
    # 콘솔에 오류 출력
    print(f"오류 발생: {str(e)}")
    print(traceback.format_exc())
    
    # 사용자가 오류를 볼 수 있도록 대기
    input("Enter 키를 눌러 종료하세요...")