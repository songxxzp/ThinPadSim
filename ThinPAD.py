import pyautogui
import pynput.mouse as pm
import time
import random
import os
import json


CLICK_INTERVAL = 0.15


button_map = {
    "CLK": None,
    "RST": None,
    "LeftUp": None,
    "RightDown": None,
    "D1": None,
    "D16": None,
}

OPMAP = {
    "ADD": 1,
    "SUB": 2,
    "AND": 3,
    "OR": 4,
    "XOR": 5,
    "NOT": 6,
    "SLL": 7,
    "SRL": 8,
    "SRA": 9,
    "ROL": 10
}

button_map.update(dict([(str(i), None)for i in range(32)]))

ctr = pm.Controller()
pressed_cnt = 0
button_to_be_click = ["0", "7", "31", "RST", "CLK", "LeftUp", "RightDown"]

def calibrate():
    def calibration(x, y, button, pressed):
        global pressed_cnt, button_to_be_click
        if pressed:
            button_name = button_to_be_click[pressed_cnt]
            print(f"{button_name} at postion {x}, {y}.")
            button_map[button_name] = (x, y)
            pressed_cnt += 1
            if pressed_cnt >= len(button_to_be_click):
                print("Calibration completed.")
                return False
            button_name = button_to_be_click[pressed_cnt]
            print(f"Please press: {button_name}")

    button_name = button_to_be_click[pressed_cnt]
    print(f"Please press: {button_name}")
    with pm.Listener(on_click=calibration) as calibration_listener:
        calibration_listener.join()

    button_distance = (button_map['7'][0] - button_map['0'][0]) / 7
    button_group_distance = (button_map['31'][0] - button_map['7'][0]) / 3

    for i in range(1, 7):
        button_map[str(i)] = (button_map['0'][0] + i * button_distance, button_map['0'][1])

    for j in range(1, 4):
        for i in range(8):
            button_map[str(8 * j + i)] = (button_map[str(i)][0] + j * button_group_distance, button_map['0'][1])

    with open("button_map.json", 'w', encoding='utf-8') as f:
        json.dump(button_map, f)

    print("Automatic reset in progress, don't click.")
    time.sleep(0.5)
    click_button('0')
    click_button('7')
    click_button('31')
    click_button('CLK')
    click_button('RST')


def click_button(button_name: str, sleep=CLICK_INTERVAL / 2):
    global button_map, ctr
    ctr.move(button_map[button_name][0] - ctr.position[0], button_map[button_name][1] - ctr.position[1])
    time.sleep(sleep)
    ctr.press(pm.Button.left)
    time.sleep(sleep)
    ctr.release(pm.Button.left)


def reset():
    click_button('RST')


def step():
    click_button('CLK')


def convert_to_bit(num: int, bit=16):
    b16 = bin(num)[2:]
    b16 = '0' * (bit - len(b16)) + b16
    if not len(b16) == bit:
        print(num, b16)
    assert len(b16) == bit
    return b16


def poke(reg, num):
    return convert_to_bit(num, 16) + "0000" + convert_to_bit(reg, bit=5) + "0001" + "010"


def peek(reg, num):
    return convert_to_bit(num, 16) + "0000" + convert_to_bit(reg, bit=5) + "0010" + "010"


def set_inst(inst: str):
    assert len(inst) == 32
    for idx, i in enumerate(inst):
        if i == '1':
            click_button(str(31 - idx))


def unset_inst(inst: str):
    set_inst(inst)


def set_reg(reg, num, screen_shot=None):
    print(f"Setting Reg_{reg} to {convert_to_bit(num)}.")
    inst_poke = poke(reg, num)
    set_inst(inst_poke)
    step()
    if screen_shot is not None:
        im = pyautogui.screenshot().crop(button_map["LeftUp"] + button_map["RightDown"])
        im.save(screen_shot + f'_Set_Reg_{reg}_to_{num}.png')
    unset_inst(inst_poke)


def show_reg(reg, screen_shot=None):
    print(f"Showing Reg_{reg}.")
    inst_peek = peek(reg, 0)
    set_inst(inst_peek)
    step()
    if screen_shot is not None:
        im = pyautogui.screenshot().crop(button_map["LeftUp"] + button_map["RightDown"])
        im.save(screen_shot + f'_Show_Reg_{reg}.png')
    unset_inst(inst_peek)


def test_reg(reg, num, screen_shot=None):
    # write num to reg and then read it.
    set_reg(reg, num, screen_shot)
    show_reg(reg, screen_shot)


def run_op(rd, rs1, rs2, op, screen_shot=None):
    if isinstance(op, int):
        opcode = op
    elif isinstance(op, str):
        opcode = OPMAP[op]
    else:
        raise NotImplementedError(f"Not implemented: {op}")
    print(f"Reg_{rd} = Reg_{rs1} {op} Reg_{rs2}.")
    inst_r = '0' * 7 + convert_to_bit(rs2, 5) + convert_to_bit(rs1, 5) + "000" + convert_to_bit(rd, 5) + convert_to_bit(opcode, 4) + "001"
    set_inst(inst_r)
    step()
    if screen_shot is not None:
        im = pyautogui.screenshot().crop(button_map["LeftUp"] + button_map["RightDown"])
        im.save(screen_shot + f'_Reg_{rd}=Reg_{rs1}_{op}_Reg_{rs2}.png')
    unset_inst(inst_r)


def test_op(rd, rs1, rs2, op, screen_shot=None):
    show_reg(rs1, screen_shot)
    show_reg(rs2, screen_shot)
    run_op(rd, rs1, rs2, op, screen_shot)
    show_reg(rd, screen_shot)

if __name__ == "__main__":
    save_path = "lab3"  # input("Save path : ")
    print(f"save_path: {save_path}")
    os.makedirs(os.path.join(save_path), exist_ok=True)
    print(f"CLICK_INTERVAL: {CLICK_INTERVAL}")
    if os.path.exists("button_map.json"):
        def confirm(x, y, button, pressed):
            if pressed:
                return False
        print("Find button_map.json, left click to load.")
        with pm.Listener(on_click=confirm) as confirm_listener:
            confirm_listener.join()
        time.sleep(1.0)
        with open("button_map.json", 'r', encoding='utf-8') as f:
            button_map = json.load(f)
    else:
        calibrate()

    time.sleep(0.5)

    reset()
    # test_reg(0, random.randint(0, 65535), screen_shot=os.path.join(save_path, "OP0"))
    test_reg(1, random.randint(0, 65535), screen_shot=os.path.join(save_path, "OP1"))
    
    # Before conducting a complete test, ensure that the program is correct.
    
    # test_reg(2, random.randint(0, 65535), screen_shot=os.path.join(save_path, "OP2"))
    # for idx, op in enumerate(OPMAP):
    #     run_op(3 + idx, 1 + idx, 2 + idx, op, screen_shot=os.path.join(save_path, f"OP{3 + idx}"))
    #     show_reg(3 + idx, screen_shot=os.path.join(save_path, f"OP{3 + idx}"))

