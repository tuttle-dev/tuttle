"""macOS EventKit bridge via a native helper app.

On macOS 14+, command-line processes (Python, scripts) cannot trigger the
calendar permission prompt because they lack ``NSCalendarsFullAccessUsageDescription``
in an Info.plist.  This module works around that by compiling a small Swift
helper binary, wrapping it in a proper ``.app`` bundle, and running all
EventKit operations through it.  The helper appears in
System Settings → Privacy → Calendars as "Tuttle Calendar".

On non-macOS platforms every public function degrades gracefully:
``is_available()`` returns False, listing/fetching return empty results.
"""

from __future__ import annotations

import datetime
import json
import platform
import plistlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pandas
from loguru import logger

from .calendar import extract_hashtag
from .data_dir import get_data_dir

_IS_DARWIN = platform.system() == "Darwin"

# ---------------------------------------------------------------------------
# Swift helper source — compiled on first use
# ---------------------------------------------------------------------------

_SWIFT_SOURCE = r"""
import EventKit
import Foundation

let store = EKEventStore()

func authStatus() -> String {
    let s = EKEventStore.authorizationStatus(for: .event)
    switch s {
    case .notDetermined: return "not_determined"
    case .restricted:    return "restricted"
    case .denied:        return "denied"
    case .fullAccess:    return "full_access"
    case .writeOnly:     return "write_only"
    @unknown default:    return "unknown"
    }
}

func requestAccess() -> Bool {
    let sem = DispatchSemaphore(value: 0)
    var ok = false
    if #available(macOS 14.0, *) {
        store.requestFullAccessToEvents { granted, _ in
            ok = granted; sem.signal()
        }
    } else {
        store.requestAccess(to: .event) { granted, _ in
            ok = granted; sem.signal()
        }
    }
    sem.wait()
    return ok
}

func listCalendars() -> [[String: String]] {
    store.calendars(for: .event).map { cal in
        ["id": cal.calendarIdentifier,
         "title": cal.title,
         "source": cal.source.title]
    }
}

func fetchEvents(calendarId: String, from: String, to: String) -> [[String: Any]] {
    let df = ISO8601DateFormatter()
    df.formatOptions = [.withFullDate]
    guard let start = df.date(from: from),
          let end = Calendar.current.date(byAdding: .day, value: 1, to: df.date(from: to) ?? Date())
    else { return [] }

    guard let cal = store.calendars(for: .event).first(where: { $0.calendarIdentifier == calendarId })
    else { return [] }

    let pred = store.predicateForEvents(withStart: start, end: end, calendars: [cal])
    let events = store.events(matching: pred)

    return events.map { ev in
        let begin = ev.startDate ?? Date()
        let finish = ev.endDate ?? begin
        let dur = finish.timeIntervalSince(begin) / 3600.0
        let row: [String: Any] = [
            "begin": ISO8601DateFormatter().string(from: begin),
            "end": ISO8601DateFormatter().string(from: finish),
            "title": ev.title ?? "",
            "description": ev.notes ?? "",
            "all_day": ev.isAllDay,
            "duration_hours": (dur * 100).rounded() / 100,
        ]
        return row
    }
}

func writeOutput(_ obj: Any, to path: String?) {
    let data = try! JSONSerialization.data(withJSONObject: obj, options: [])
    let json = String(data: data, encoding: .utf8)!
    if let path = path {
        try! json.write(toFile: path, atomically: true, encoding: .utf8)
    } else {
        print(json)
    }
}

// -- main --
var args = Array(CommandLine.arguments.dropFirst())

// Extract --output <path> if present
var outputPath: String? = nil
if let idx = args.firstIndex(of: "--output"), idx + 1 < args.count {
    outputPath = args[idx + 1]
    args.removeSubrange(idx...idx+1)
}

guard let cmd = args.first else {
    writeOutput(["error": "usage: TuttleCalendar <command> [--output <path>]"], to: outputPath)
    exit(1)
}

switch cmd {
case "status":
    writeOutput(["auth_status": authStatus()], to: outputPath)
case "request-access":
    let ok = requestAccess()
    writeOutput(["granted": ok, "auth_status": authStatus()], to: outputPath)
case "list-calendars":
    if !requestAccess() {
        writeOutput(["calendars": [] as [Any], "auth_status": authStatus()], to: outputPath)
    } else {
        writeOutput(["calendars": listCalendars(), "auth_status": authStatus()], to: outputPath)
    }
case "fetch-events":
    guard args.count >= 4 else {
        writeOutput(["error": "usage: fetch-events <cal_id> <from> <to>"], to: outputPath)
        exit(1)
    }
    if !requestAccess() {
        writeOutput(["events": [] as [Any], "auth_status": authStatus()], to: outputPath)
    } else {
        let evts = fetchEvents(calendarId: args[1], from: args[2], to: args[3])
        writeOutput(["events": evts, "auth_status": authStatus()], to: outputPath)
    }
default:
    writeOutput(["error": "unknown command: \(cmd)"], to: outputPath)
    exit(1)
}
"""

_INFO_PLIST = {
    "CFBundleName": "Tuttle Calendar",
    "CFBundleDisplayName": "Tuttle Calendar",
    "CFBundleIdentifier": "dev.tuttle.calendar-helper",
    "CFBundleVersion": "1.0",
    "CFBundleShortVersionString": "1.0",
    "CFBundlePackageType": "APPL",
    "CFBundleExecutable": "TuttleCalendar",
    "LSUIElement": False,
    "NSCalendarsFullAccessUsageDescription": ("Tuttle needs access to your calendars to import events for time tracking."),
}


# ---------------------------------------------------------------------------
# Helper app lifecycle
# ---------------------------------------------------------------------------


def _helper_app_dir() -> Path:
    return get_data_dir() / "TuttleCalendar.app"


def _helper_executable() -> Path:
    return _helper_app_dir() / "Contents" / "MacOS" / "TuttleCalendar"


def _ensure_helper() -> Path:
    """Compile the Swift helper and create the .app bundle if needed."""
    exe = _helper_executable()
    if exe.exists():
        return exe

    app = _helper_app_dir()
    macos_dir = app / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True, exist_ok=True)

    plist_path = app / "Contents" / "Info.plist"
    with open(plist_path, "wb") as f:
        plistlib.dump(_INFO_PLIST, f)

    swift_src = app / "Contents" / "MacOS" / "main.swift"
    swift_src.write_text(_SWIFT_SOURCE)

    logger.info("Compiling TuttleCalendar helper…")
    result = subprocess.run(
        [
            "swiftc",
            "-O",
            "-o",
            str(exe),
            str(swift_src),
            "-framework",
            "EventKit",
            "-framework",
            "Foundation",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"swiftc failed: {result.stderr}")
        raise RuntimeError(f"Failed to compile calendar helper: {result.stderr}")

    swift_src.unlink()

    subprocess.run(
        ["codesign", "--force", "--sign", "-", str(app)],
        capture_output=True,
    )
    logger.info(f"TuttleCalendar helper compiled at {exe}")
    return exe


def _run_helper(*args: str) -> dict:
    """Run the helper via ``open`` so macOS treats it as its own app process
    (required for TCC to check the helper's bundle, not the parent's)."""
    import tempfile

    _ensure_helper()
    app_path = _helper_app_dir()

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = tmp.name

    try:
        result = subprocess.run(
            [
                "open",
                "--wait-apps",
                str(app_path),
                "--args",
                *args,
                "--output",
                out_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"Helper launch failed: {result.stderr}")
            return {"error": result.stderr}

        out_file = Path(out_path)
        if not out_file.exists() or out_file.stat().st_size == 0:
            return {"error": "helper produced no output"}

        return json.loads(out_file.read_text())
    except json.JSONDecodeError:
        logger.error("Helper returned invalid JSON")
        return {"error": "invalid helper output"}
    except subprocess.TimeoutExpired:
        logger.error("Helper timed out")
        return {"error": "timeout"}
    finally:
        Path(out_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_available() -> bool:
    return _IS_DARWIN


def authorization_status() -> str:
    if not _IS_DARWIN:
        return "not_available"
    try:
        data = _run_helper("status")
        return data.get("auth_status", "unknown")
    except Exception as ex:
        logger.warning(f"Could not get auth status: {ex}")
        return "unknown"


def open_calendar_privacy_settings():
    """Open macOS System Settings → Privacy & Security → Calendars."""
    subprocess.Popen(
        [
            "open",
            "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Calendars",
        ]
    )


def request_access() -> bool:
    if not _IS_DARWIN:
        return False
    try:
        data = _run_helper("request-access")
        return data.get("granted", False)
    except Exception as ex:
        logger.warning(f"Could not request access: {ex}")
        return False


def list_calendars() -> List[Dict[str, str]]:
    if not _IS_DARWIN:
        return []
    try:
        data = _run_helper("list-calendars")
        return data.get("calendars", [])
    except Exception as ex:
        logger.warning(f"Could not list calendars: {ex}")
        return []


def list_calendars_with_status() -> Dict[str, Any]:
    """Return calendars and auth_status together."""
    if not _IS_DARWIN:
        return {"calendars": [], "auth_status": "not_available"}
    try:
        return _run_helper("list-calendars")
    except Exception as ex:
        logger.warning(f"Could not list calendars: {ex}")
        return {"calendars": [], "auth_status": "unknown"}


def fetch_events(
    calendar_id: str,
    from_date: datetime.date,
    to_date: datetime.date,
) -> pandas.DataFrame:
    """Fetch events from a macOS system calendar and return a time-tracking DataFrame."""
    if not _IS_DARWIN:
        return _empty_df()

    try:
        data = _run_helper(
            "fetch-events",
            calendar_id,
            from_date.isoformat(),
            to_date.isoformat(),
        )
    except Exception as ex:
        logger.warning(f"Could not fetch events: {ex}")
        return _empty_df()

    raw_events = data.get("events", [])
    if not raw_events:
        return _empty_df()

    rows = []
    for ev in raw_events:
        try:
            begin_dt = datetime.datetime.fromisoformat(ev["begin"])
            end_dt = datetime.datetime.fromisoformat(ev["end"])
        except (KeyError, ValueError):
            continue

        title = ev.get("title", "")
        is_all_day = ev.get("all_day", False)
        tag = extract_hashtag(title)
        description = ev.get("description", "")

        def _ts(dt):
            return (
                pandas.Timestamp(dt).tz_convert("CET")
                if dt.tzinfo
                else pandas.Timestamp(dt).tz_localize("UTC").tz_convert("CET")
            )

        if is_all_day and (end_dt - begin_dt).days > 1:
            # Expand multi-day all-day events into one row per day
            day = begin_dt.date()
            end_date = end_dt.date()
            while day < end_date:
                day_start = datetime.datetime.combine(day, datetime.time.min, tzinfo=begin_dt.tzinfo)
                day_end = day_start + datetime.timedelta(days=1)
                rows.append(
                    {
                        "begin": _ts(day_start),
                        "title": title,
                        "description": description,
                        "end": _ts(day_end),
                        "all_day": True,
                        "duration": datetime.timedelta(days=1),
                        "tag": tag,
                    }
                )
                day += datetime.timedelta(days=1)
        else:
            rows.append(
                {
                    "begin": _ts(begin_dt),
                    "title": title,
                    "description": description,
                    "end": _ts(end_dt),
                    "all_day": is_all_day,
                    "duration": end_dt - begin_dt,
                    "tag": tag,
                }
            )

    if not rows:
        return _empty_df()

    df = pandas.DataFrame(rows)
    df = df.set_index("begin")
    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _empty_df() -> pandas.DataFrame:
    df = pandas.DataFrame(columns=["title", "description", "end", "all_day", "duration", "tag"])
    df.index.name = "begin"
    return df
