import keyboard, win32gui, win32process, psutil, subprocess, os, tkinter as tk
from threading import Thread

# 프로그램 별 CCD Affinity를 저장하는 딕셔너리
current_affinity_dict = dict()
# 부스트 클럭 플래그
boost = False

# 현재 포커스된 프로세스의 이름을 가져오는 함수
def get_process_name():
    handle = win32gui.GetForegroundWindow()
    tid, pid = win32process.GetWindowThreadProcessId(handle)
    process_name = psutil.Process(pid).name()

    return process_name

# 프로세스의 CCD Affinity를 변경하는 함수
def change_affinity(process):
    # 프로세스가 딕셔너리에 없으면 추가하고 2로 초기화
    if process not in current_affinity_dict:
        current_affinity_dict[process] = 2
    # 프로세스가 2보다 작으면 1을 더하고 아니면 -2를 더함(== 2를 뺌)
    current_affinity_dict[process] += 1 if current_affinity_dict[process] < 2 else -2

    # CCD Affinity 리스트 (CCD0, CCD1, all CCD)
    affinty_list = [65535, 4294901760, 4294967295]

    # 프로세스의 CCD Affinity를 변경하는 파워쉘 명령어
    command = f"Get-Process {process[:-4:]} | ForEach-Object {{$_.ProcessorAffinity={affinty_list[current_affinity_dict[process]]}}}"

    print(command)

    # 여기 shell=True가 없으면 pythonw로 돌릴 때 0.1초 정도 검은 창이 떴다가 사라지면서 포커스를 explore.exe가 가져감.
    subprocess.run(["powershell", command], shell=True)
    overlay_text(f'"{process}" is now on CCD"{current_affinity_dict[process]}"', 1000)

def toggle_boost(events = None):
    global boost
    # 99% = 9c78821f-7b0b-42d5-b670-55f60d15be8d, 100% = 98edfa27-f7b3-44a1-8eb8-67634e2dcc52
    command = "powercfg -S 9c78821f-7b0b-42d5-b670-55f60d15be8d" if boost else "powercfg -S 98edfa27-f7b3-44a1-8eb8-67634e2dcc52"
    print(command)
    subprocess.run(["powershell", command], shell=True)
    overlay_text(f'Boost Clock {"Off" if boost else "On"}', 1000)

    boost = not boost

# pause 키 후킹 시 호출되는 함수. 프로그램 종료
def terminate(events = None):
    overlay_text('pause key detected. ending program', 1500).join()
    os._exit(0)

# 오버레이 텍스트를 띄우는 함수
def overlay_text(text, timeout=2000):
    def make_overlay(text, timeout):
        root = tk.Tk()

        root.overrideredirect(True)  # 창 프레임 제거 (타이틀 바 없음)
        root.attributes("-topmost", True)  # 항상 위에 표시
        root.attributes("-alpha", 0.7)  # 창 투명도 설정 (0.0 = 완전 투명, 1.0 = 불투명)

        # 라벨 생성 (패딩 포함)
        label = tk.Label(root, text=text, font=("Arial", 20), fg="white", bg="gray")
        label.pack()  # 패킹

        # 창 크기 업데이트 후 실제 텍스트 크기 가져오기
        text_width = label.winfo_reqwidth()  # 라벨이 필요한 최소 너비

        # 화면 크기 가져오기
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # 화면 아래쪽 7/8 지점에 배치
        x_pos = (screen_width - text_width) // 2  # 가로 중앙 정렬
        y_pos = (screen_height * 7) // 8  # 세로 위치 (하단 7/8)
        root.geometry(f"+{x_pos}+{y_pos}")

        root.after(timeout, root.destroy)
        root.mainloop()

    # 내부적으로 쓰레드를 통해 오버레이를 띄움. timeout 시간동안 프로그램이 멈추던 것을 해결. 이제 오버레이가 떠있는 중간에도 프로그램이 동작함.
    # th로 쓰레드를 만들어 반환함. 호출한 곳에서 필요시 .join()으로 timeout 시간동안 오버레이를 유지할 수 있음.
    th = Thread(target=make_overlay, args=(text, timeout), daemon=True)
    th.start()
    print(text) # 매번 overlay_text랑 print랑 같이 써야하는게 귀찮아서 여기서 print도 같이 해줌.
    return th

if __name__ == '__main__':
    # welcome message
    overlay_text('Change Core Affinity of focused program with "Scroll Lock"\nTerminate with "Pause" key', 4000)

    # pause 키 후킹. terminate 함수 호출
    keyboard.hook_key('pause', callback=terminate)
    # ctrl + scroll lock 후킹. toggle_boost 함수 호출
    keyboard.add_hotkey('ctrl+scroll lock', callback=toggle_boost)

    while True:
        keyboard.wait('scroll lock')

        current_process_name =  get_process_name()

        # 뮤뮤 플레이어의 경우 뮤뮤 플레이어 헤드리스도 함께 변경. 이 싸가지 없는 새끼는 대가리스가 메인임.
        if current_process_name == 'MuMuPlayer.exe':
            change_affinity('MuMuVMMHeadless.exe')

        change_affinity(current_process_name)
