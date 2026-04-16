import pyautogui
import time


from PIL import ImageGrab
import numpy as np

def _check_phase1_running(self, threshold: float = 128) -> bool:
    screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    pixels = np.array(screenshot)

    brightness = (
        0.33 * pixels[:, :, 0] +
        0.33 * pixels[:, :, 1] +
        0.33 * pixels[:, :, 2]
    )

    return int(np.sum(brightness >= threshold)) > 2000

x1= 1161
y1= 1117
x2= 1469
y2= 1231

def _check_attack_finished(x1, y1, x2, y2,threshold = 128) -> bool:
    screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    pixels = np.array(screenshot)

    brightness = (
        0.33 * pixels[:, :, 0] +
        0.33 * pixels[:, :, 1] +
        0.33 * pixels[:, :, 2]
    )
    p = np.array(ImageGrab.grab(bbox=(x1, y1, x2, y2))).astype(float)

    r, g, b = p[:, :, 0], p[:, :, 1], p[:, :, 2]

    is_green = (
        (g >= r * 1.4) &
        (g >= b * 1.4) &
        (g >= 80)
    )

    print(int(np.sum(is_green)))
    print(int(np.sum(brightness >= threshold)))

if __name__ == "__main__":
    while True:
        print(_check_attack_finished(x1, y1, x2, y2))
        time.sleep(1)