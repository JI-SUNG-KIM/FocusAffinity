import keyboard, win32gui, win32process, psutil, subprocess, os

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

    subprocess.run(["powershell", "-Command", command])
    print(f"{process} is now on CCD{current_affinity_dict[process]}")

def get_process_name():
    handle = win32gui.GetForegroundWindow()
    tid, pid = win32process.GetWindowThreadProcessId(handle)
    process_name = psutil.Process(pid).name()

    return process_name

def kill(events):
    print('pause key detected. ending program')
    os._exit(0)

keyboard.hook_key('pause', callback=kill)

while True:
    keyboard.wait('scroll lock')

    current_process_name =  get_process_name()

    change_affinity(current_process_name)
