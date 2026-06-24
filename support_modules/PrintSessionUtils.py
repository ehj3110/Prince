"""Utilities for creating and reusing print-session folders.

Session layout:
<main_image_dir>/Printing_Logs/YYYY-MM-DD/Print N
"""

import datetime
import os
import re


PRINT_FOLDER_RE = re.compile(r"^Print\s+(\d+)(?:\s+-\s+.*)?$")


def get_today_str():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def get_print_log_paths(main_image_dir, date_str=None):
    date_token = date_str or get_today_str()
    base_dir = os.path.join(main_image_dir, "Printing_Logs")
    date_dir = os.path.join(base_dir, date_token)
    return base_dir, date_dir, date_token


def parse_print_number(print_dir_name):
    if not print_dir_name:
        return None
    match = PRINT_FOLDER_RE.match(print_dir_name.strip())
    if not match:
        return None
    return int(match.group(1))


def get_next_print_number(date_dir):
    next_num = 1
    if not os.path.isdir(date_dir):
        return next_num

    nums = []
    for entry in os.listdir(date_dir):
        full = os.path.join(date_dir, entry)
        if not os.path.isdir(full):
            continue
        parsed = parse_print_number(entry)
        if parsed is not None:
            nums.append(parsed)
    if nums:
        next_num = max(nums) + 1
    return next_num


def ensure_print_session(main_image_dir, date_str=None, preferred_print_dir=None):
    base_dir, date_dir, date_token = get_print_log_paths(main_image_dir, date_str=date_str)
    os.makedirs(date_dir, exist_ok=True)

    print_number = None
    print_dir = None
    reused_preferred = False

    if preferred_print_dir:
        preferred_abs = os.path.abspath(preferred_print_dir)
        preferred_parent = os.path.dirname(preferred_abs)
        if os.path.abspath(preferred_parent) == os.path.abspath(date_dir):
            parsed = parse_print_number(os.path.basename(preferred_abs))
            if parsed is not None:
                print_number = parsed
                print_dir = preferred_abs
                reused_preferred = True

    if print_dir is None:
        print_number = get_next_print_number(date_dir)
        print_dir = os.path.join(date_dir, f"Print {print_number}")

    os.makedirs(print_dir, exist_ok=True)

    return {
        "base_dir": base_dir,
        "date_dir": date_dir,
        "date_str": date_token,
        "print_number": print_number,
        "print_dir": print_dir,
        "reused_preferred": reused_preferred,
    }
