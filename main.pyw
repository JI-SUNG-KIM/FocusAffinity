import keyboard

import psutil
import subprocess, tkinter as tk
from threading import Thread
import os
import ctypes

from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

import re


# 프로그램 별 CCD Affinity를 저장하는 딕셔너리
# process_name: 0 or 1 or 2
current_affinity_dict = dict()

# 부스트 클럭 플래그
BOOST = False
POWER_PLAN = ("9c78821f-7b0b-42d5-b670-55f60d15be8d", "98edfa27-f7b3-44a1-8eb8-67634e2dcc52")

# Affinity Masks (Ryzen 9 5950X/7950X setup: 16 cores, 32 threads)
CCD0_MASK = 0xFFFF          # 0-15
CCD1_MASK = 0xFFFF0000      # 16-31
ALL_MASK = 0xFFFFFFFF       # 0-31
AFFINITY_LIST = (CCD0_MASK, CCD1_MASK, ALL_MASK)

def mask_to_cpus(mask):
    return [i for i in range(32) if (mask >> i) & 1]

# 현재 포커스된 프로세스의 이름 반환
def get_focused_name():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        return psutil.Process(pid.value).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

# 프로세스 이름으로 현재 Affinity Bitmask 반환
def get_affinity_mask(process_name):
    for p in psutil.process_iter(['name', 'cpu_affinity']):
        if p.info['name'] == process_name:
            mask = 0
            for core in p.info['cpu_affinity']:
                mask |= (1 << core)
            return mask
    return ALL_MASK

# return guid of current power plan
def get_current_power_plan():
    result = subprocess.check_output(["powercfg", "/getactivescheme"], text=True, encoding="cp949")
    guid = re.search(r'GUID:\s*([a-f0-9\-]+)', result, re.I).group(1)
    return guid

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

########################################################################################################

# called by 'scroll lock'
def show_current_affinity(process):
    if process not in current_affinity_dict:
        overlay_text(f"{process} is not in the list", 1000)
    else:
        overlay_text(f'"{process}" is on CCD{current_affinity_dict[process]}', 1000)

# called by 'shift+scroll lock'
# 프로세스의 CCD Affinity를 변경
def switch_affinity(process, show_overlay=True):
    if not process:
        return

    # 프로세스가 딕셔너리에 없으면 기존 affinity로 추가. affinity가 좀 특이하면 걍 2로 취급.
    if process not in current_affinity_dict:
        cur_aff = get_affinity_mask(process)
        if cur_aff in AFFINITY_LIST:
            current_affinity_dict[process] = AFFINITY_LIST.index(cur_aff)
        else:
            current_affinity_dict[process] = 2

    # Cycle index: 0 -> 1 -> 2 -> 0
    current_affinity_dict[process] = (current_affinity_dict[process] + 1) % 3
    
    target_mask = AFFINITY_LIST[current_affinity_dict[process]]
    target_cpus = mask_to_cpus(target_mask)

    # psutil을 사용하여 Affinity 변경 (PowerShell 제거)
    count = 0
    for p in psutil.process_iter(['name']):
        if p.info['name'] == process:
            try:
                p.cpu_affinity(target_cpus)
                count += 1
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

    if AFFINITY_LIST.index(get_affinity_mask(process)) == current_affinity_dict[process]:
        print(f"Set {process} to mask {target_mask} (Count: {count})")
    else:
        print(f"Failed to set {process} to mask {target_mask} (Count: {count})")
        current_affinity_dict[process] = (current_affinity_dict[process] + 2) % 3

    if show_overlay:
        overlay_text(f'"{process}" is now on CCD"{current_affinity_dict[process]}"', 1000)

# called by 'ctrl+shift+scroll lock'
# power plan을 변경하여 CPU 부스트 클럭을 토글하는 함수
def toggle_boost():
    global BOOST

    command = f"powercfg -S {POWER_PLAN[not BOOST]}"
    print(command)
    subprocess.run(["powershell", command], shell=True)
    overlay_text(f'Boost Clock {"Off" if BOOST else "On"}', 1000)

    BOOST = not BOOST


########################################################################################################

# for Tray Icon Image
def create_image():
    # 아이콘 이미지 생성 (64x64)
    image = Image.new('RGB', (64, 64), color='white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill='black')
    return image

# CCD Affinity 딕셔너리 오버레이 출력
# Tray menu "Show Affinity List"
def tray_show_affinity_list():
    msg = "--------------------------------\nCurrent Power Plan\n"
    msg += "Base" if POWER_PLAN.index(get_current_power_plan()) == 0 else "Boost"
    msg += "\n"
    
    msg += "--------------------------------\nCurrent Affinity List\n"
    for key, value in current_affinity_dict.items():
        # if value == 2:
        #     continue
        msg += f'{key}: {value}\n'
    msg += '--------------------------------'
    overlay_text(msg, 5000, 1/30, 1/2)

# Tray menu "Reset All Affinity Settings"
def tray_menu_reset():
    for key, value in list(current_affinity_dict.items()):
        if value == 2:
            current_affinity_dict.pop(key)
            continue
        current_affinity_dict[key] = 1
        switch_affinity(key, False)
    overlay_text('All Affinity Reset', 1000).join()
    current_affinity_dict.clear()

# Tray menu "Keys"
def tray_munu_keys():
    overlay_text('scroll lock: switch affinity\n' \
    'shift+scroll lock: toggle boost\n' \
    'ctrl+shift+scroll lock: show affinity list' 
    , 4000)

# Tray menu "Exit"
def tray_menu_quit(icon):
    icon.stop()
    overlay_text('Terminating this program...', 1500).join()
    os._exit(0)

########################################################################################################

def main():
    # welcome message
    BOOST = POWER_PLAN.index(get_current_power_plan())
    overlay_text('Focus Affinity\nStarting Program...', 2000).join()
    
    keyboard.add_hotkey('scroll lock', callback=lambda: show_current_affinity(get_focused_name()))
    keyboard.add_hotkey('shift+scroll lock', callback=lambda: switch_affinity(get_focused_name()))
    keyboard.add_hotkey('ctrl+shift+scroll lock', callback=toggle_boost)

    icon = Icon(
        "Focus_Affinity_JS",
        create_image(),
        "Focus Affinity",
        menu=Menu(
            MenuItem("Show Affinity List", lambda icon, item: Thread(target=tray_show_affinity_list).start()),
            MenuItem("Reset All Affinity Settings", lambda icon, item: Thread(target=tray_menu_reset).start()),
            MenuItem("Keys", lambda icon, item: Thread(target=tray_munu_keys).start()),
            MenuItem("Exit", lambda icon, item: Thread(target=tray_menu_quit, args=(icon,)).start())
        )
    )

    icon.run()

if __name__ == '__main__':
    main()