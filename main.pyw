import keyboard
import win32gui, win32process, psutil
import subprocess, tkinter as tk
from threading import Thread
import os

# 프로그램 별 CCD Affinity를 저장하는 딕셔너리
current_affinity_dict = dict()
# 부스트 클럭 플래그
boost = False

# 현재 포커스된 프로세스의 PID 반환
def get_focused_pid():
    handle = win32gui.GetForegroundWindow()
    tid, pid = win32process.GetWindowThreadProcessId(handle)
    return pid

# PID로 프로세스 이름 반환
def get_process_name(pid):
    return psutil.Process(pid).name()

# PID로 프로세스의 CCD Affinity를 반환
def get_affinity(pid):
    bitmask = 0
    for core in psutil.Process(pid).cpu_affinity():
        bitmask |= (1 << core)  # 2^core를 더함
    print('bitmask : ', bitmask)
    return bitmask

# called by 'scroll lock'
# 프로세스의 CCD Affinity를 변경
def switch_affinity(pid, show_overlay=True):
    process = get_process_name(pid)
    # CCD Affinity 리스트 (CCD0, CCD1, all CCD)
    affinty_list = [65535, 4294901760, 4294967295]

    # print('affinty_list.index(get_affinity(pid)) : ', affinty_list.index(get_affinity(pid)))
    # 프로세스가 딕셔너리에 없으면 기존 affinity로 추가. affinity가 좀 특이하면 걍 2로 취급.
    if process not in current_affinity_dict:
        cur_aff = get_affinity(pid)
        if cur_aff in affinty_list:
            current_affinity_dict[process] = affinty_list.index(cur_aff)
        else:
            current_affinity_dict[process] = 2
    # 프로세스가 2보다 작으면 1을 더하고 아니면 -2를 더함(== 2를 뺌)
    current_affinity_dict[process] += 1 if current_affinity_dict[process] < 2 else -2

    # 프로세스의 CCD Affinity를 변경하는 파워쉘 명령어
    command = f"Get-Process {process[:-4:]} | ForEach-Object {{$_.ProcessorAffinity={affinty_list[current_affinity_dict[process]]}}}"

    print(command)

    # 여기 shell=True가 없으면 pythonw로 돌릴 때 0.1초 정도 검은 창이 떴다가 사라지면서 포커스를 explore.exe가 가져감.
    subprocess.run(["powershell", command], shell=True)
    if show_overlay:
        overlay_text(f'"{process}" is now on CCD"{current_affinity_dict[process]}"', 1000)

# called by 'shift+scroll lock'
# power plan을 변경하여 CPU 부스트 클럭을 토글하는 함수
def toggle_boost(events = None):
    global boost
    # 99% = 9c78821f-7b0b-42d5-b670-55f60d15be8d, 100% = 98edfa27-f7b3-44a1-8eb8-67634e2dcc52
    command = "powercfg -S 9c78821f-7b0b-42d5-b670-55f60d15be8d" if boost else "powercfg -S 98edfa27-f7b3-44a1-8eb8-67634e2dcc52"
    print(command)
    subprocess.run(["powershell", command], shell=True)
    overlay_text(f'Boost Clock {"Off" if boost else "On"}', 1000)

    boost = not boost

# called by 'ctrl+shift+scroll lock'
# CCD Affinity 딕셔너리 오버레이 출력
def show_affinity_list(events = None):
    msg = "--------------------------------\nCurrent Affinity List\n"
    for key, value in current_affinity_dict.items():
        # if value == 2:
        #     continue
        msg += f'{key}: {value}\n'
    msg += '--------------------------------'
    overlay_text(msg, 5000, 1/30, 1/2)

# called by 'shift+pause'
# 모든 프로세스의 CCD Affinity를 초기화
def reset_affinity(events = None):
    for key, value in current_affinity_dict.items():
        if value == 2:
            current_affinity_dict.pop(key)
            continue
        current_affinity_dict[key] = 1
        switch_affinity(key, False)
    overlay_text('All Affinity Reset', 1000).join()
    current_affinity_dict.clear()

# called by 'pause'
# 프로그램 종료
def terminate(events = None):
    overlay_text('pause key detected. ending program', 1500).join()
    os._exit(0)

# 오버레이 텍스트를 띄우는 함수
def overlay_text(text, timeout=2000, x_ratio=1/2, y_ratio=7/8):
    def make_overlay():
        root = tk.Tk()

        root.overrideredirect(True)  # 창 프레임 제거 (타이틀 바 없음)
        root.attributes("-topmost", True)  # 항상 위에 표시
        root.attributes("-alpha", 0.8)  # 창 투명도 설정 (0.0 = 완전 투명, 1.0 = 불투명)

        # 라벨 생성 (패딩 포함)
        label = tk.Label(root, text=text, font=("Arial", 20), fg="white", bg="gray")
        label.pack()  # 패킹

        # 창 크기 업데이트 후 실제 텍스트 크기 가져오기
        text_width = label.winfo_reqwidth()  # 라벨이 필요한 최소 너비

        # 화면 크기 가져오기
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # 화면 아래쪽 7/8 지점에 배치
        x_pos = int((screen_width - text_width) * x_ratio)  # 가로 중앙 정렬
        y_pos = int(screen_height * y_ratio)  # 세로 위치 (하단 7/8)
        root.geometry(f"+{x_pos}+{y_pos}")

        root.after(timeout, root.destroy)
        root.mainloop()

    # 내부적으로 쓰레드를 통해 오버레이를 띄움. timeout 시간동안 프로그램이 멈추던 것을 해결. 이제 오버레이가 떠있는 중간에도 프로그램이 동작함.
    # th로 쓰레드를 만들어 반환함. 호출한 곳에서 필요시 .join()으로 timeout 시간동안 오버레이를 유지할 수 있음.
    th = Thread(target=make_overlay, daemon=True)
    th.start()
    print(text) # 매번 overlay_text랑 print랑 같이 써야하는게 귀찮아서 여기서 print도 같이 해줌.
    return th

if __name__ == '__main__':
    # welcome message
    overlay_text('Change Core Affinity of focused program with "Scroll Lock"\nTerminate with "Pause" key', 4000).join()

    keyboard.add_hotkey('shift+scroll lock', callback=toggle_boost)
    keyboard.add_hotkey('ctrl+shift+scroll lock', callback=show_affinity_list)
    keyboard.add_hotkey('pause', callback=terminate)
    keyboard.add_hotkey('shift+pause', callback=reset_affinity)

    while True:
        keyboard.wait('scroll lock')

        current_process_pid = get_focused_pid()
        switch_affinity(current_process_pid)
        # 뮤뮤 플레이어의 경우 뮤뮤 플레이어 헤드리스도 함께 변경. 이 싸가지 없는 새끼는 대가리스가 메인임.
        if get_process_name(current_process_pid) == 'MuMuPlayer.exe':
            switch_affinity('MuMuVMMHeadless.exe', False)
            switch_affinity('MuMuVMMSVC.exe', False)