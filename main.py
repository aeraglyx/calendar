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


def get_config() -> dict:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    config_file_default = os.path.join(SCRIPT_DIR, "config.toml")
    config_file_user = os.path.expandvars("$XDG_CONFIG_HOME/calendar/config.toml")

    with open(config_file_default, "rb") as d:
        cfg = tomllib.load(d)

    if os.path.isfile(config_file_user):
        with open(config_file_user, "rb") as u:
            cfg.update(tomllib.load(u))

    return cfg


def get_calendar_data(data_path: str) -> list[dict]:
    calendar_data = []
    for filename in os.listdir(data_path):
        if filename.startswith("."):
            continue
        filepath = os.path.join(data_path, filename)
        with open(filepath) as f:
            calendar_data.extend(json.load(f))
    return calendar_data


def get_entry_corrected(entry: dict, year: int) -> dict:
    """ return the same entry, but with updated year """

    def offset_year(dt_str: str, year: int) -> str:
        time = datetime.fromisoformat(dt_str)
        time_corrected = time.replace(year=year)
        if "T" not in dt_str:
            time_corrected = time_corrected.date()
        return time_corrected.isoformat()

    entry_corrected = entry.copy()
    entry_corrected["time"] = offset_year(entry["time"], year)

    if "stop" in entry:
        time = datetime.fromisoformat(entry["time"])
        stop = datetime.fromisoformat(entry["stop"])
        year_stop = stop.year + (year - time.year)
        entry_corrected["stop"] = offset_year(entry["stop"], year_stop)

    return entry_corrected


def get_data_filtered(calendar_data: list, date_list: list) -> dict:
    data_filtered = {date: [] for date in date_list}
    month_and_day_wanted = [(date.month, date.day) for date in date_list]

    for entry in calendar_data:
        stamp = datetime.fromisoformat(entry["time"]).date()
        month_and_day = (stamp.month, stamp.day)

        if entry.get("repeat"):
            if month_and_day not in month_and_day_wanted:
                continue
            for date in date_list:
                if (date.month, date.day) == month_and_day:
                    entry_corrected = get_entry_corrected(entry, date.year)
                    data_filtered[date].append(entry_corrected)
        else:
            if stamp in data_filtered:
                data_filtered[stamp].append(entry)

    return data_filtered


def width_to_chars(w: int) -> str:
    if w == 1: return "│ "
    middle = (2 * w - 3) * "-"
    return "╭" + middle + "╯ "


def lines_str(line_data) -> str:
    line_char_list = [width_to_chars(x["width"]) for x in line_data]
    return colors.BLACK + "".join(line_char_list) + colors.RESET


def update_line_data(data) -> list[dict]:
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
    num_color = colors.BLACK_BRIGHT if diff < 0 and args.compact else colors.BLACK
    start_str = "".join([
        num_color + f"{abs(diff):02d}".ljust(4) if diff != 0 else colors.BLUE + "🯩🯫".ljust(4),
        weekend_fmt + date_str + separator,
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
        time_str = time + " | " if time else ""

        show_days = args.compact and duration_days
        days_str = str(duration_days) + "d | " if show_days else ""

        entry_str = f"{start}{urgency_color}{icon} {time_str}{days_str}{name}"
        print(entry_str)

        if not args.compact and duration_days > 1:
            line_data.append({
                "remaining": duration_days,
                "index": sum([x["width"] for x in line_data]),
                "width": 1,
            })

    line_data = update_line_data(line_data)

    print(colors.RESET, end="" if entries else "\n")

