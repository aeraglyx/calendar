# calendar

A simple TUI calendar. Stable for my usecase, unstable for public.

Features:
- Multiple entries per day
- Entries with end date or time
- Overlapping entries
- Redacting sensitive entries
- Urgency levels
- Different icons for entry types
- Dimmed weekend days
- New month hint


## Data Specs

Data is currently in `json`. List of supported entry fields:

| field | description |
| ----- | ----------- |
| name | Label for the event. |
| time | ISO-8601-ish date. |
| stop | Same, but for the entry end. |
| urgency | One of `low`, `normal`, `high`. |
| sensitive | Boolean for entries that should be redacted when using the `-s` flag. |

Example:

```json
[
    { "name": "A simple entry", "time": "2026-07-19" },
    { "name": "A 2 day entry starting today", "time": "2026-07-20", "stop": "2026-07-21" },
    { "name": "Overlapping entry", "time": "2026-07-21", "stop": "2026-07-23" },
    { "name": "Entry with time", "time": "2026-07-23T10:30:00" },
    { "name": "A 2 hour entry", "time": "2026-07-24T12:00:00", "stop": "2026-08-24T14:00:00" }
]
```

By default, the above example would return something like this (note that the readme is missing colors):

```
01  07-24  fri   A simple entry
🯩🯫  07-20  mon   A 2 day entry starting today
01  07-21  tue  │  Overlapping entry
02  07-22  wed  ╭─╯
03  07-23  thu  │  10:30 Entry with time
04  07-24  fri   12:00-14:00 A 2 hour entry
```
