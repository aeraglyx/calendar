import os
import json
from datetime import datetime, timedelta
import re
import argparse
import tomllib


parser = argparse.ArgumentParser()
parser.add_argument("-n", "--num_days", type=int, default=42)
parser.add_argument("-o", "--offset", type=int, default=-7)
parser.add_argument("-c", "--compact", action="store_true")
parser.add_argument("-s", "--sensitive", action="store_true")
args = parser.parse_args()


class colors():
    BLACK = '\033[30m'
    BLACK_BRIGHT = '\033[90m'
    WHITE = '\033[37m'

    RED = '\033[31m'
    YELLOW = '\033[33m'
    GREEN = '\033[32m'
    CYAN = '\033[36m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'

    RESET = '\033[0m'

urgency_map = {
    "low": colors.BLACK,
    "normal": colors.RESET,
    "high": colors.YELLOW
}


def get_config():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    config_file_default = os.path.join(SCRIPT_DIR, "config.toml")
    config_file_user = os.path.expandvars("$XDG_CONFIG_HOME/calendar/config.toml")

    with open(config_file_default, "rb") as d:
        cfg = tomllib.load(d)

    if os.path.isfile(config_file_user):
        with open(config_file_user, "rb") as u:
            cfg.update(tomllib.load(u))

    return cfg


def get_calendar_data(data_path):
    calendar_data = []
    for filename in os.listdir(data_path):
        if filename.startswith("."):
            continue
        filepath = os.path.join(data_path, filename)
        with open(filepath) as f:
            calendar_data.extend(json.load(f))
    return calendar_data


def get_data_filtered(calendar_data, date_list):
    fixed_year = 2000
    data_filtered = {date: [] for date in date_list}
    filtered_dates = data_filtered.keys()
    filtered_dates_with_offset = [date.replace(year=fixed_year) for date in filtered_dates]

    for entry in calendar_data:
        stamp_str = entry["time"]
        date = datetime.fromisoformat(stamp_str).date()
        if entry.get("repeat"):
            date_normalized = date.replace(year=fixed_year)
            if date_normalized not in filtered_dates_with_offset:
                continue
        if date not in filtered_dates:
            continue
        data_filtered[date].append(entry)

    return data_filtered


def width_to_chars(w):
    if w == 1: return "│ "
    n_middle = 2 * w - 3
    return "╭" + n_middle * "─" + "╯ "


def lines_str(line_data):
    line_char_list = [width_to_chars(x["width"]) for x in line_data]
    return colors.BLACK + "".join(line_char_list) + colors.RESET


def update_line_data(data):
    data_new = []
    index_new = 0
    for line in data:
        if line["remaining"] == 1:
            continue
        width_new = line["index"] - index_new + 1
        data_new.append({
            "remaining": line["remaining"] - 1,
            "index": index_new,
            "width": width_new,
        })
        index_new += width_new
    return data_new


cfg = get_config()
data_path = os.path.expanduser(os.path.expandvars(cfg["data_path"]))
calendar_data = get_calendar_data(data_path)

today = datetime.today()
date_list = [today.date() + timedelta(days=x+args.offset) for x in range(args.num_days)]
data_filtered = get_data_filtered(calendar_data, date_list)

line_data = []
lines = ""

for i, date in enumerate(date_list):
    entries = data_filtered.get(date)
    assert entries is not None

    if date.day == 1:
        term_width = os.get_terminal_size().columns
        month_str = date.strftime(" %B %Y ")
        month_line = (term_width - len(month_str) - 3) * "─" + month_str + 3 * "─"
        print(colors.BLACK + month_line + colors.RESET)

    if args.compact and not entries:
        continue

    diff = i + args.offset
    weekday_int = date.weekday()
    weekday_str = cfg["day_names"][weekday_int]

    is_weekend = weekday_int > 4
    weekend_fmt = colors.BLACK if is_weekend else colors.RESET
    date_str = date.strftime("%m-%d")

    separator = "  "
    start_str = separator.join([
        colors.BLACK + f"{abs(diff):02d}" if diff != 0 else colors.BLUE + "🯩🯫",
        weekend_fmt + date_str,
        weekday_str,
    ])

    if not args.compact:
        lines = lines_str(line_data)

    print(start_str + separator + lines, end = "")

    # HACK:
    start_raw = re.sub(r'\033\[\d+m', "", start_str)
    l = len(start_raw)

    for j, entry in enumerate(entries):
        is_sensitive = args.sensitive and entry.get("sensitive")

        name = entry["name"]
        if is_sensitive:
            name = "redacted"

        event_urgency = entry.get("urgency", "normal")
        name = urgency_map[event_urgency] + name + colors.RESET

        event_type = entry.get("type", "default")
        icon = cfg["icon_map"].get(event_type, cfg["icon_default"])
        if is_sensitive:
            icon = cfg["icon_secret"]

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

        if not args.compact:
            lines = lines_str(line_data)

        start = "" if j == 0 else (l + len(separator)) * " " + lines
        time_str = colors.BLUE + time + " " + colors.RESET if time else ""

        days_str = ""
        if args.compact and duration_days:
            days_str = colors.YELLOW + str(duration_days) + "d " + colors.RESET

        entry_str = f"{start}{icon} {time_str}{days_str}{name}"
        print(entry_str)

        if not args.compact and duration_days > 1:
            line_data.append({
                "remaining": duration_days,
                "index": sum([x["width"] for x in line_data]),
                "width": 1,
            })

    line_data = update_line_data(line_data)

    print(colors.RESET, end="" if entries else "\n")

