import keyboard, win32gui, win32process, psutil, subprocess
from prompt_toolkit.key_binding.bindings.named_commands import end_of_line

current_affinity = 2

def change_affinity(process):
    global current_affinity
    current_affinity += 1 if current_affinity < 2 else -2

    affinty_list = [65535, 4294901760, 4294967295]

    command = f"""
    Get-Process {process[:-4:]} | ForEach-Object {{
    $_.ProcessorAffinity={affinty_list[current_affinity]}
    }}
    """

    subprocess.run(["powershell", "-Command", command])
    print(f"{process}'s CCD Affinity changed to CCD{current_affinity}")

def get_process_name():
    handle = win32gui.GetForegroundWindow()
    tid, pid = win32process.GetWindowThreadProcessId(handle)
    process_name = psutil.Process(pid).name()

    return process_name

while True:
    keyboard.wait('scroll lock')
    print('key detected')

    current_process_name =  get_process_name()
    print(current_process_name)
    print(current_process_name[:-4:])

    change_affinity(current_process_name)
