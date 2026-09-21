import base64
import datetime
from pathlib import Path
from typing import Optional

import pandas
from loguru import logger
from pandas import DataFrame

from ...calendar import ICSCalendar
from ...eventkit_bridge import (
    fetch_events,
    is_available,
    list_calendars_with_status,
    open_calendar_privacy_settings,
)
from ...timetracking import get_planning_summary
from ..core.abstractions import Intent
from ..core.intent_result import IntentResult
from ..projects.intent import ProjectsIntent
from .aggregation import (
    build_calendar_data,
    build_summary,
    df_to_records,
    empty_calendar_data,
    merge_dataframes,
)
from .data_source import (
    ManualEntriesDataSource,
    TimeTrackingDataFrameSource,
    TimeTrackingFileCalendarSource,
    TimeTrackingSpreadsheetSource,
    to_cet,
)

_MISSING_ENTRY = "This entry no longer exists. Reload the calendar and try again."


class _EntryError(ValueError):
    pass


def _parse_local(date: str, time: str) -> pandas.Timestamp:
    return to_cet(datetime.datetime.fromisoformat(f"{date}T{time}"))


def _validate_entry(tag: str, date: str, start_time: str, end_time: str):
    if not tag:
        raise _EntryError("Choose a project for this entry.")
    try:
        begin, end = _parse_local(date, start_time), _parse_local(date, end_time)
    except ValueError:
        raise _EntryError("Enter the date as YYYY-MM-DD and the times as HH:MM.")
    if end <= begin:
        raise _EntryError("The end time must be after the start time.")
    return begin, end


def _ensure_source_column(df: DataFrame, source: str = "calendar") -> DataFrame:
    if "source" not in df.columns:
        df = df.copy()
        df["source"] = source
    return df


def _manual_entry_starts_at(df: Optional[DataFrame], begin, exclude_id: Optional[int] = None) -> bool:
    if df is None or df.empty or "source" not in df.columns:
        return False
    mask = (df.index == to_cet(begin)) & (df["source"] == "manual").to_numpy()
    if exclude_id is not None and "entry_id" in df.columns:
        mask &= (df["entry_id"] != exclude_id).to_numpy()
    return bool(mask.any())


def _coerce_id(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _project_tag_maps(projects) -> tuple[dict, dict]:
    tag_to_title = {}
    tag_to_workday = {}
    for p in projects or []:
        if p.tag:
            tag_to_title[p.tag] = p.title
            if p.contract:
                tag_to_workday[p.tag] = p.contract.units_per_workday
    return tag_to_title, tag_to_workday


class TimeTrackingIntent(Intent):
    """Time-tracking data access, import, aggregation."""

    def __init__(self, client_storage=None):
        self._file_calendar_source = TimeTrackingFileCalendarSource()
        self._spreadsheet_source = TimeTrackingSpreadsheetSource()
        self._timetracking_data_frame_source = TimeTrackingDataFrameSource()

    @staticmethod
    def _manual_entries() -> ManualEntriesDataSource:
        # Built per call so it is always bound to the active user's database.
        return ManualEntriesDataSource()

    def _replace_calendar_rows(self, new_df: DataFrame):
        """Swap in freshly fetched calendar rows; manual entries live in the database."""
        ds = self._timetracking_data_frame_source
        ds.store_data_frame(_ensure_source_column(new_df, "calendar"))
        ds.save_to_cache()

    def _entry_record(self, entry_id: int) -> Optional[dict]:
        df = self._timetracking_data_frame_source.get_data_frame()
        if df is None or "entry_id" not in df.columns:
            return None
        records = df_to_records(df[df["entry_id"] == entry_id])
        return records[0] if records else None

    # -- RPC-facing methods ----------------------------------------------------

    def get_events(self, project_tag=None) -> IntentResult:
        df = self._timetracking_data_frame_source.get_data_frame()
        if df is None or df.empty:
            return IntentResult(was_intent_successful=True, data=[])
        if project_tag:
            df = df[df["tag"] == project_tag]
        return IntentResult(was_intent_successful=True, data=df_to_records(df))

    def get_calendar_data(self, year=None, month=None, project_tag=None) -> IntentResult:
        if year is None:
            year = datetime.date.today().year
        if month is None:
            month = datetime.date.today().month
        df = self._timetracking_data_frame_source.get_data_frame()
        if df is None or df.empty:
            return IntentResult(was_intent_successful=True, data=empty_calendar_data(year, month))
        proj_result = ProjectsIntent().get_all()
        projects = proj_result.data if proj_result.was_intent_successful and proj_result.data else []
        tag_to_title, tag_to_workday = _project_tag_maps(projects)
        return IntentResult(
            was_intent_successful=True,
            data=build_calendar_data(df, year, month, project_tag, tag_to_title, tag_to_workday),
        )

    def import_ics(self, content: str, name: str = "imported.ics") -> IntentResult:
        raw = base64.b64decode(content)
        cal = ICSCalendar(name=name, content=raw)
        new_df = _ensure_source_column(cal.to_data(), "calendar")
        ds = self._timetracking_data_frame_source
        ds.store_data_frame(merge_dataframes(ds.calendar_rows(), new_df))
        ds.save_to_cache()
        ds.save_source_config("ics", calendar_name=name)
        records = df_to_records(new_df)
        return IntentResult(
            was_intent_successful=True,
            data={"imported_count": len(records), "events": records},
        )

    def clear(self) -> IntentResult:
        """Disconnect the calendar source. Manually tracked entries stay in the database."""
        ds = self._timetracking_data_frame_source
        ds.store_data_frame(None)
        ds.clear_cache()
        ds.clear_source_config()
        return IntentResult(was_intent_successful=True, data=None)

    def list_system_calendars(self, open_settings=False) -> IntentResult:
        if not is_available():
            return IntentResult(
                was_intent_successful=True,
                data={
                    "calendars": [],
                    "auth_status": "not_available",
                },
            )
        if open_settings:
            open_calendar_privacy_settings()
            return IntentResult(
                was_intent_successful=True,
                data={
                    "calendars": [],
                    "auth_status": "pending",
                },
            )
        try:
            return IntentResult(
                was_intent_successful=True,
                data=list_calendars_with_status(),
            )
        except Exception as ex:
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                data={"calendars": [], "auth_status": "unknown"},
                error_msg=str(ex),
            )

    def import_system_calendar(
        self,
        calendar_id,
        from_date=None,
        to_date=None,
    ) -> IntentResult:
        if not is_available():
            return IntentResult(
                was_intent_successful=False,
                error_msg="System calendar access is only available on macOS",
            )
        if from_date is None:
            from_date = datetime.date.today() - datetime.timedelta(days=365)
        elif isinstance(from_date, str):
            from_date = datetime.date.fromisoformat(from_date)
        if to_date is None:
            to_date = datetime.date.max
        elif isinstance(to_date, str):
            to_date = datetime.date.fromisoformat(to_date)
        try:
            new_df = fetch_events(calendar_id, from_date, to_date)
            if new_df.empty:
                return IntentResult(
                    was_intent_successful=True,
                    data={
                        "imported_count": 0,
                        "events": [],
                    },
                )
            new_df = _ensure_source_column(new_df, "calendar")
            ds = self._timetracking_data_frame_source
            ds.store_data_frame(merge_dataframes(ds.calendar_rows(), new_df))
            ds.save_to_cache()
            ds.save_source_config("system", calendar_id=str(calendar_id))
            records = df_to_records(new_df)
            return IntentResult(
                was_intent_successful=True,
                data={
                    "imported_count": len(records),
                    "events": records,
                },
            )
        except Exception as ex:
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=str(ex),
            )

    def get_source_config(self) -> IntentResult:
        config = self._timetracking_data_frame_source.get_source_config()
        config["has_data"] = self._timetracking_data_frame_source.has_calendar_rows()
        return IntentResult(was_intent_successful=True, data=config)

    def restore(self) -> IntentResult:
        """Restore cached time-tracking data from disk (called on startup)."""
        ds = self._timetracking_data_frame_source
        if ds.has_calendar_rows():
            return IntentResult(
                was_intent_successful=True,
                data={"restored": False, "reason": "already_loaded", "has_data": True},
            )
        config = ds.get_source_config()
        source_type = config.get("source_type", "")
        if not source_type:
            # No calendar connected, but manually tracked entries may be cached.
            restored = ds.load_from_cache()
            df = ds.get_data_frame()
            return IntentResult(
                was_intent_successful=True,
                data={
                    "restored": restored,
                    "reason": "no_config",
                    "has_data": df is not None and not df.empty,
                },
            )
        if source_type == "system" and is_available():
            calendar_id = config.get("calendar_id", "")
            if calendar_id:
                try:
                    from_date = datetime.date.today() - datetime.timedelta(days=365)
                    to_date = datetime.date.max
                    new_df = fetch_events(calendar_id, from_date, to_date)
                    if not new_df.empty:
                        self._replace_calendar_rows(new_df)
                        logger.info(f"Restored {len(new_df)} events from system calendar {calendar_id}")
                        return IntentResult(
                            was_intent_successful=True,
                            data={
                                "restored": True,
                                "source": "system",
                                "count": len(new_df),
                                "has_data": True,
                            },
                        )
                except Exception as ex:
                    logger.warning(f"Failed to restore from system calendar: {ex}")
        restored = ds.load_from_cache()
        has_data = ds.get_data_frame() is not None and not ds.get_data_frame().empty
        return IntentResult(
            was_intent_successful=True,
            data={
                "restored": restored,
                "source": source_type if restored else "cache",
                "has_data": has_data,
            },
        )

    def sync(self) -> IntentResult:
        """Re-fetch from the configured calendar source (manual refresh)."""
        ds = self._timetracking_data_frame_source
        config = ds.get_source_config()
        source_type = config.get("source_type", "")
        if not source_type:
            return IntentResult(
                was_intent_successful=True,
                data={"synced": False, "reason": "no_config"},
            )
        if source_type == "system" and is_available():
            calendar_id = config.get("calendar_id", "")
            if calendar_id:
                try:
                    from_date = datetime.date.today() - datetime.timedelta(days=365)
                    to_date = datetime.date.max
                    new_df = fetch_events(calendar_id, from_date, to_date)
                    if not new_df.empty:
                        self._replace_calendar_rows(new_df)
                        return IntentResult(
                            was_intent_successful=True,
                            data={"synced": True, "count": len(new_df)},
                        )
                except Exception as ex:
                    logger.warning(f"Failed to sync from system calendar: {ex}")
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg=f"Calendar sync failed: {ex}",
                    )
        return IntentResult(
            was_intent_successful=True,
            data={
                "synced": False,
                "reason": f"source_type '{source_type}' not syncable",
            },
        )

    def get_planning_summary(self) -> IntentResult:
        """Per-project summary of planned (future) hours and revenue."""
        df = self._timetracking_data_frame_source.get_data_frame()
        if df is None or df.empty:
            return IntentResult(was_intent_successful=True, data=[])
        proj_result = ProjectsIntent().get_all()
        projects = proj_result.data if proj_result.was_intent_successful and proj_result.data else []
        return IntentResult(
            was_intent_successful=True,
            data=get_planning_summary(df, projects),
        )

    def get_summary(self, project_tag: Optional[str] = None) -> IntentResult:
        df = self._timetracking_data_frame_source.get_data_frame()
        if df is None or df.empty:
            return IntentResult(
                was_intent_successful=True,
                data={
                    "total_events": 0,
                    "total_hours": 0,
                    "projects": [],
                },
            )
        proj_result = ProjectsIntent().get_all()
        projects = proj_result.data if proj_result.was_intent_successful and proj_result.data else []
        tag_to_title, tag_to_workday = _project_tag_maps(projects)
        return IntentResult(
            was_intent_successful=True,
            data=build_summary(df, tag_to_title, project_tag, tag_to_workday),
        )

    # -- Timer and manual entry ------------------------------------------------

    def start_timer(self, tag: Optional[str] = None, title: Optional[str] = None) -> IntentResult:
        ds = self._timetracking_data_frame_source
        if ds.get_timer_state()["running"]:
            return IntentResult(
                was_intent_successful=False,
                error_msg="A timer is already running. Stop or discard it first.",
            )
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        ds.save_timer_state(start_iso=now.isoformat(), tag=tag or "", title=title or "")
        return IntentResult(
            was_intent_successful=True,
            data={"started": True, "start_time": now.isoformat()},
        )

    def update_timer(self, tag: Optional[str] = None, title: Optional[str] = None) -> IntentResult:
        ds = self._timetracking_data_frame_source
        state = ds.get_timer_state()
        if not state["running"]:
            return IntentResult(was_intent_successful=False, error_msg="No timer is running.")
        ds.save_timer_state(
            start_iso=state["start_time"],
            tag=(state["tag"] or "") if tag is None else tag,
            title=(state["title"] or "") if title is None else title,
        )
        return IntentResult(was_intent_successful=True, data=ds.get_timer_state())

    def stop_timer(
        self,
        tag: Optional[str] = None,
        title: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> IntentResult:
        ds = self._timetracking_data_frame_source
        state = ds.get_timer_state()
        if not state["running"]:
            return IntentResult(was_intent_successful=False, error_msg="No timer is running.")
        final_tag = tag or state["tag"] or ""
        if not final_tag:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Choose a project for this entry before saving it.",
            )
        begin = to_cet(state["start_time"])
        try:
            end = to_cet(end_time) if end_time else to_cet(datetime.datetime.now(tz=datetime.timezone.utc))
        except (ValueError, TypeError):
            return IntentResult(
                was_intent_successful=False,
                error_msg="The end time could not be read. Stop the timer again.",
            )
        if end < begin:
            end = begin
        final_title = title if title is not None else (state["title"] or "")
        entry_id = self._manual_entries().add(begin, end, final_tag, final_title)
        ds.refresh_manual_rows()
        ds.clear_timer_state()
        return IntentResult(
            was_intent_successful=True,
            data={
                "stopped": True,
                "duration_hours": round((end - begin).total_seconds() / 3600, 2),
                "entry": self._entry_record(entry_id),
            },
        )

    def get_timer_state(self) -> IntentResult:
        return IntentResult(
            was_intent_successful=True,
            data=self._timetracking_data_frame_source.get_timer_state(),
        )

    def discard_timer(self) -> IntentResult:
        self._timetracking_data_frame_source.clear_timer_state()
        return IntentResult(was_intent_successful=True, data={"discarded": True})

    def add_manual_entry(
        self,
        tag: str,
        date: str,
        start_time: str,
        end_time: str,
        title: Optional[str] = None,
    ) -> IntentResult:
        try:
            begin, end = _validate_entry(tag, date, start_time, end_time)
        except _EntryError as ex:
            return IntentResult(was_intent_successful=False, error_msg=str(ex))
        ds = self._timetracking_data_frame_source
        if _manual_entry_starts_at(ds.get_data_frame(), begin):
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"You already have an entry starting at {start_time} on {date}. "
                "Edit that entry or choose a different start time.",
            )
        entry_id = self._manual_entries().add(begin, end, tag, title or "")
        ds.refresh_manual_rows()
        return IntentResult(
            was_intent_successful=True,
            data={"added": True, "entry": self._entry_record(entry_id)},
        )

    def update_manual_entry(
        self,
        entry_id,
        tag: str,
        date: str,
        start_time: str,
        end_time: str,
        title: Optional[str] = None,
    ) -> IntentResult:
        entry_id = _coerce_id(entry_id)
        if entry_id is None:
            return IntentResult(was_intent_successful=False, error_msg=_MISSING_ENTRY)
        try:
            begin, end = _validate_entry(tag, date, start_time, end_time)
        except _EntryError as ex:
            return IntentResult(was_intent_successful=False, error_msg=str(ex))
        ds = self._timetracking_data_frame_source
        if _manual_entry_starts_at(ds.get_data_frame(), begin, exclude_id=entry_id):
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Another entry already starts at {start_time} on {date}. Choose a different start time.",
            )
        if not self._manual_entries().update(entry_id, begin, end, tag, title or ""):
            return IntentResult(was_intent_successful=False, error_msg=_MISSING_ENTRY)
        ds.refresh_manual_rows()
        return IntentResult(
            was_intent_successful=True,
            data={"updated": True, "entry": self._entry_record(entry_id)},
        )

    def delete_manual_entry(self, entry_id) -> IntentResult:
        entry_id = _coerce_id(entry_id)
        if entry_id is None or not self._manual_entries().delete(entry_id):
            return IntentResult(was_intent_successful=False, error_msg=_MISSING_ENTRY)
        self._timetracking_data_frame_source.refresh_manual_rows()
        return IntentResult(was_intent_successful=True, data={"deleted": True})

    def get_project_tags(self) -> IntentResult:
        proj_result = ProjectsIntent().get_all()
        projects = proj_result.data if proj_result.was_intent_successful and proj_result.data else []
        tags = [{"tag": p.tag, "title": p.title, "id": p.id} for p in projects if p.tag]
        return IntentResult(was_intent_successful=True, data=tags)

    # -- Legacy internal methods -----------------------------------------------

    def process_timetracking_file(self, file_path: Path) -> IntentResult[DataFrame]:
        """processes a time tracking spreadsheet or ics file in the uploads folder

        Returns
        -------
            IntentResult
                data : time tracking data as a pandas DataFrame if intent successful else None
                error_msg  : text to display to the user if an error occurs else is empty
        """
        # check the file extension. file_path is a Path object
        is_calendar = file_path.suffix == ".ics"
        if is_calendar:
            timetracking_data: DataFrame = self._file_calendar_source.load_data(
                ics_file_path=file_path,
            )
            return IntentResult(
                was_intent_successful=True,
                data=timetracking_data,
            )
        else:
            timetracking_data: DataFrame = self._spreadsheet_source.load_data(
                file_path=file_path,
            )
            return IntentResult(
                was_intent_successful=True,
                data=timetracking_data,
            )

    def get_timetracking_data(self) -> IntentResult[Optional[DataFrame]]:
        try:
            data = self._timetracking_data_frame_source.get_data_frame()
            return IntentResult(
                was_intent_successful=True,
                data=data,
            )
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load time tracking data: {ex}",
                exception=ex,
                data=None,
            )

    def set_timetracking_data(self, data: DataFrame) -> IntentResult[None]:
        try:
            self._timetracking_data_frame_source.store_data_frame(data=data)
            return IntentResult(
                was_intent_successful=True,
            )
        except Exception as ex:
            error_msg = f"Failed to store time tracking data: {ex}"
            logger.error(error_msg)
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_msg,
                exception=ex,
                data=None,
            )
