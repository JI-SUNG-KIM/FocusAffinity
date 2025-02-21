import keyboard, win32gui, win32process, psutil, subprocess, os, tkinter as tk
from threading import Thread, enumerate

# 프로그램 별 CCD Affinity를 저장하는 딕셔너리
current_affinity_dict = dict()

def change_affinity(process):
    # 프로세스가 딕셔너리에 없으면 추가하고 2로 초기화
    if process not in current_affinity_dict:
        current_affinity_dict[process] = 2
    # 프로세스가 2보다 작으면 1을 더하고 아니면 -2를 더함(== 2를 뺌)
    current_affinity_dict[process] += 1 if current_affinity_dict[process] < 2 else -2

    # CCD Affinity 리스트 (CCD0, CCD1, all CCD)
    affinty_list = [65535, 4294901760, 4294967295]

    # 프로세스의 CCD Affinity를 변경하는 파워쉘 명령어
    command = f"""
    Get-Process {process[:-4:]} | ForEach-Object {{
    $_.ProcessorAffinity={affinty_list[current_affinity_dict[process]]}
    }}
    """

    # 여기 shell=True가 없으면 pythonw로 돌릴 때 0.1초 정도 검은 창이 떴다가 사라지면서 포커스를 explore.exe가 가져감.
    subprocess.run(["powershell", "-Command", command], shell=True)
    overlay_text(f'"{process}" is now on CCD"{current_affinity_dict[process]}"', 1000)
    print(f'"{process}" is now on CCD"{current_affinity_dict[process]}"')

def get_process_name():
    handle = win32gui.GetForegroundWindow()
    tid, pid = win32process.GetWindowThreadProcessId(handle)
    process_name = psutil.Process(pid).name()

    return process_name

def kill(events):
    overlay_text('pause key detected. ending program', 1500).join()
    print('pause key detected. ending program')
    os._exit(0)


def overlay_text(text, timeout=2000):
    def make_overlay(text, timeout):
        root = tk.Tk()

        root.overrideredirect(True)  # 창 프레임 제거 (타이틀 바 없음)
        root.attributes("-topmost", True)  # 항상 위에 표시
        root.attributes("-alpha", 0.7)  # 창 투명도 설정 (0.0 = 완전 투명, 1.0 = 불투명)

        # 라벨 생성 (패딩 포함)
        label = tk.Label(root, text=text, font=("Arial", 20), fg="white", bg="gray")
        label.pack()  # 패딩 추가 (여백 설정)

        root.update_idletasks()  # UI 업데이트 후 크기 반영

        # 창 크기 업데이트 후 실제 텍스트 크기 가져오기
        text_width = label.winfo_reqwidth()  # 라벨이 필요한 최소 너비

        # 창 크기를 텍스트 크기에 맞게 조정 (여백 포함)
        window_width = text_width + 20  # 좌우 여백 추가

        # 화면 크기 가져오기
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # 화면 아래쪽 7/8 지점에 배치
        x_pos = (screen_width - window_width) // 2  # 가로 중앙 정렬
        y_pos = (screen_height * 7) // 8  # 세로 위치 (하단 7/8)
        root.geometry(f"+{x_pos}+{y_pos}")

        root.after(timeout, root.destroy)
        root.mainloop()

    # th로 쓰레드를 만들어 반환함. 호출한 곳에서 필요시 .join()으로 timeout 시간동안 오버래이를 유지할 수 있음.
    th = Thread(target=make_overlay, args=(text, timeout), daemon=True)
    th.start()
    return th

if __name__ == '__main__':
    # welcome message
    overlay_text('Change Core Affinity of focused program with "Scroll Lock".\nTerminate with "Pause" key', 4000)
    print('Change Core Affinity of focused program with "Scroll Lock".\nTerminate with "Pause" key')

    # pause 키 후킹. kill 함수 호출
    keyboard.hook_key('pause', callback=kill)

    while True:
        keyboard.wait('scroll lock')

        current_process_name =  get_process_name()

        # 뮤뮤 플레이어의 경우 뮤뮤 플레이어 헤드리스도 함께 변경. 이 싸가지 없는 새끼는 대가리스가 메인임.
        if current_process_name == 'MuMuPlayer.exe':
            change_affinity('MuMuVMMHeadless.exe')

        change_affinity(current_process_name)
