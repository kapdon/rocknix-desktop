#!/usr/bin/python3
"""Type a test URL into the focused RP6 browser through InputPlumber."""
import subprocess
import sys
import time

url = sys.argv[1]
assert url.startswith(('https://', 'file:///storage/Desktop/'))
plain = {c: 'KEY_' + c.upper() for c in 'abcdefghijklmnopqrstuvwxyz0123456789'}
plain.update({'/': 'KEY_SLASH', '.': 'KEY_DOT', '-': 'KEY_MINUS'})
shifted = {':': 'KEY_SEMICOLON', '_': 'KEY_MINUS'}
assert all(c in plain or c in shifted or (c.isascii() and c.isupper()) for c in url)

def event(key, down):
    subprocess.run(['busctl', 'call', 'org.shadowblip.InputPlumber',
        '/org/shadowblip/InputPlumber/devices/target/keyboard0',
        'org.shadowblip.Input.Keyboard', 'SendKey', 'sb', key,
        'true' if down else 'false'], check=True, stdout=subprocess.DEVNULL)
    time.sleep(0.04)

def press(key):
    try:
        event(key, True)
    finally:
        event(key, False)

try:
    event('KEY_LEFTCTRL', True)
    press('KEY_L')
finally:
    event('KEY_LEFTCTRL', False)
for char in url:
    needs_shift = char in shifted or char.isupper()
    try:
        if needs_shift:
            event('KEY_LEFTSHIFT', True)
        press(shifted.get(char) or plain[char.lower()])
    finally:
        if needs_shift:
            event('KEY_LEFTSHIFT', False)
press('KEY_ENTER')
