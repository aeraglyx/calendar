import os
import json
from datetime import datetime, timedelta
import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--sensitive", action="store_true")
args = parser.parse_args()


DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

icon_map = {
    "default": "",
    "secret": "",
    "home": "",
    "work": "",
    "doctor": "",
    "bills": "",
}

num_days = 42

class colors():
    BLACK = '\033[30m'
    WHITE = '\033[37m'

    RED = '\033[31m'
    YELLOW = '\033[33m'
    GREEN = '\033[32m'
    CYAN = '\033[36m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'

    BLACK_BRIGHT = '\033[90m'

    RESET = '\033[0m'

urgency_map = {
    "low": colors.BLACK,
    "normal": colors.RESET,
    "high": colors.YELLOW
}

data_path = os.path.expanduser("~/.local/share/calendar")
file = os.path.join(data_path, "calendar.json")
file_recurring = os.path.join(data_path, "repeating.json")

with open(file) as f:
    calendar_data = json.load(f)

with open(file_recurring) as f:
    calendar_data_recurring = json.load(f)

today = datetime.today()
today_offset = 7
date_list = [today.date() + timedelta(days=x-today_offset) for x in range(num_days)]


data_filtered = {date: [] for date in date_list}

filtered_dates = data_filtered.keys()
for entry in calendar_data:
    stamp_str = entry["time"]
    date = datetime.fromisoformat(stamp_str).date()
    if date not in filtered_dates:
        continue
    data_filtered[date].append(entry)

fixed_year = 2000
filtered_dates_with_offset = [date.replace(year=fixed_year) for date in data_filtered.keys()]
for entry in calendar_data_recurring:
    stamp_str = entry["time"]
    date = datetime.fromisoformat(stamp_str).date()
    if date.replace(year=fixed_year) not in filtered_dates_with_offset:
        continue
    data_filtered[date].append(entry)

def width_to_chars(w):
    if w == 1: return "│ "
    n_middle = 2 * w - 3
    return "╭" + n_middle * "─" + "╯ "

def lines_str(cont_array):
    line_char_list = [width_to_chars(x["width"]) for x in cont_array]
    return colors.BLACK + "".join(line_char_list) + colors.RESET

def update_line_data(data):
    data_new = []
    i_new = 0
    for line in data:
        if line["remaining"] == 1:
            continue
        width_new = line["position"] - i_new + 1
        data_new.append({
            "remaining": line["remaining"] - 1,
            "position": i_new,
            "width": width_new,
        })
        i_new += width_new
    return data_new

line_data = []

for i, date in enumerate(date_list):
    diff = i - today_offset
    weekday_int = date.weekday()
    weekday_str = DAY_NAMES[weekday_int]

    is_weekend = weekday_int > 4
    weekend_fmt = colors.BLACK if is_weekend else colors.RESET

    entries = data_filtered.get(date)
    assert entries is not None

    date_str = date.strftime("%m-%d")
    if not is_weekend:
        dash_dim = f"{colors.BLACK}-{colors.RESET}"
        date_str = dash_dim.join(date_str.split("-"))

    separator = "  "
    start_str = separator.join([
        colors.BLACK + f"{abs(diff):02d}" if diff != 0 else colors.CYAN + "🯩🯫",
        weekend_fmt + date_str,
        weekday_str,
    ])

    # HACK:
    start_raw = re.sub(r'\033\[\d+m', "", start_str)
    l = len(start_raw)

    if date.day == 1:
        term_width = os.get_terminal_size().columns
        month_str = date.strftime(" %B %Y ")
        print(colors.BLACK + (term_width - len(month_str) - 3) * "─" + month_str + 3 * "─" + colors.RESET)

    lines = lines_str(line_data)
    print(start_str + separator + lines, end = "")

    for j, entry in enumerate(entries):
        is_sensitive = args.sensitive and entry.get("sensitive")

        name = entry["name"]
        if is_sensitive:
            name = re.sub(r"\S", "*", name)
            name = "redacted"

        event_urgency = entry.get("urgency", "normal")
        name = urgency_map[event_urgency] + name + colors.RESET

        event_type = entry.get("type", "default")
        icon = icon_map.get(event_type, icon_map["default"])
        if is_sensitive:
            icon = icon_map["secret"]

        urgency_color = urgency_map[event_urgency]
        icon = urgency_color + icon + colors.RESET

        stamp_str = entry["time"]
        time = datetime.fromisoformat(stamp_str).time()
        time = time.strftime("%H:%M") if "T" in stamp_str else None

        time_stop = None
        duration_days = 0
        if "stop" in entry:
            stop_datetime = datetime.fromisoformat(entry["stop"])
            time_stop = stop_datetime.time().strftime("%H:%M")

            date_stop = stop_datetime.date()
            duration_days = (date_stop - date).days + 1

        if time and time_stop:
            time = time + "-" + time_stop

        lines = lines_str(line_data)
        start = "" if j == 0 else (l + len(separator)) * " " + lines
        time_str = colors.CYAN + time + " " + colors.RESET if time else ""

        entry_str = f"{start}{icon} {time_str}{name}"
        print(entry_str)

        if duration_days > 1:
            line_data.append({
                "remaining": duration_days,
                "position": sum([x["width"] for x in line_data]),
                "width": 1,
            })

    line_data = update_line_data(line_data)

    print(colors.RESET, end="" if entries else "\n")

