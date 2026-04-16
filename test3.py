import pyautogui
import time


def slide_up():
    pyautogui.moveTo(1571, 205)
    pyautogui.dragTo(1167, 1235, duration=0.5)

time.sleep(1)
slide_up()