import keyboard, time

print(keyboard.parse_hotkey('ctrl+scroll lock'))
print(keyboard.parse_hotkey_combinations('ctrl+scroll lock'))

print(keyboard.key_to_scan_codes('space'))
print(keyboard.key_to_scan_codes('ctrl'))
print(keyboard.key_to_scan_codes('scroll lock'))
print(keyboard.key_to_scan_codes('break'))
print(keyboard.key_to_scan_codes('pause'))
# print(keyboard.key_to_scan_codes("ctrl+space"))
print(keyboard.version)

keyboard.add_hotkey('ctrl+scroll lock', lambda: print('ctrl+scroll lock detected'))

while True:
    print(keyboard.is_pressed('ctrl+scroll lock'))
    time.sleep(0.5)