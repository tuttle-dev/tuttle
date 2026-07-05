import base64
import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from pandas import DataFrame

from ..core.abstractions import Intent
from ..core.intent_result import IntentResult
from ..projects.intent import ProjectsIntent
from ...calendar import ICSCalendar
from ...eventkit_bridge import (
    fetch_events,
    is_available,
    list_calendars_with_status,
    open_calendar_privacy_settings,
)

from .aggregation import (
    build_calendar_data,
    build_summary,
    df_to_records,
    merge_dataframes,
)
from .data_source import (
    TimeTrackingDataFrameSource,
    TimeTrackingFileCalendarSource,
    TimeTrackingSpreadsheetSource,
)
from ...timetracking import get_planning_summary


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

    # -- RPC-facing methods ----------------------------------------------------

    def get_events(self, project_tag=None) -> IntentResult:
        df = self._timetracking_data_frame_source.get_data_frame()
        if df is None or df.empty:
            return IntentResult(was_intent_successful=True, data=[])
        if project_tag:
            df = df[df["tag"] == project_tag]
        return IntentResult(was_intent_successful=True, data=df_to_records(df))

    def get_calendar_data(
        self, year=None, month=None, project_tag=None
    ) -> IntentResult:
        df = self._timetracking_data_frame_source.get_data_frame()
        if df is None or df.empty:
            return IntentResult(
                was_intent_successful=True,
                data={
                    "events": [],
                    "projects": [],
                    "summary": {},
                },
            )
        if year is None:
            year = datetime.date.today().year
        if month is None:
            month = datetime.date.today().month
        proj_result = ProjectsIntent().get_all()
        projects = (
            proj_result.data
            if proj_result.was_intent_successful and proj_result.data
            else []
        )
        tag_to_title, tag_to_workday = _project_tag_maps(projects)
        return IntentResult(
            was_intent_successful=True,
            data=build_calendar_data(
                df, year, month, project_tag, tag_to_title, tag_to_workday
            ),
        )

    def import_ics(self, content: str, name: str = "imported.ics") -> IntentResult:
        raw = base64.b64decode(content)
        cal = ICSCalendar(name=name, content=raw)
        new_df = cal.to_data()
        ds = self._timetracking_data_frame_source
        ds.store_data_frame(merge_dataframes(ds.get_data_frame(), new_df))
        ds.save_to_cache()
        ds.save_source_config("ics", calendar_name=name)
        records = df_to_records(new_df)
        return IntentResult(
            was_intent_successful=True,
            data={"imported_count": len(records), "events": records},
        )

    def clear(self) -> IntentResult:
        self._timetracking_data_frame_source.store_data_frame(None)
        self._timetracking_data_frame_source.clear_cache()
        self._timetracking_data_frame_source.clear_source_config()
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
            ds = self._timetracking_data_frame_source
            ds.store_data_frame(merge_dataframes(ds.get_data_frame(), new_df))
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
        df = self._timetracking_data_frame_source.get_data_frame()
        config["has_data"] = df is not None and not df.empty
        return IntentResult(was_intent_successful=True, data=config)

    def restore(self) -> IntentResult:
        """Restore cached time-tracking data from disk (called on startup)."""
        ds = self._timetracking_data_frame_source
        if ds.get_data_frame() is not None:
            return IntentResult(
                was_intent_successful=True,
                data={"restored": False, "reason": "already_loaded", "has_data": True},
            )
        config = ds.get_source_config()
        source_type = config.get("source_type", "")
        if not source_type:
            return IntentResult(
                was_intent_successful=True,
                data={"restored": False, "reason": "no_config", "has_data": False},
            )
        if source_type == "system" and is_available():
            calendar_id = config.get("calendar_id", "")
            if calendar_id:
                try:
                    from_date = datetime.date.today() - datetime.timedelta(days=365)
                    to_date = datetime.date.max
                    new_df = fetch_events(calendar_id, from_date, to_date)
                    if not new_df.empty:
                        ds.store_data_frame(new_df)
                        ds.save_to_cache()
                        logger.info(
                            f"Restored {len(new_df)} events from system calendar {calendar_id}"
                        )
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
                        ds.store_data_frame(new_df)
                        ds.save_to_cache()
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
        projects = (
            proj_result.data
            if proj_result.was_intent_successful and proj_result.data
            else []
        )
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
        projects = (
            proj_result.data
            if proj_result.was_intent_successful and proj_result.data
            else []
        )
        tag_to_title, tag_to_workday = _project_tag_maps(projects)
        return IntentResult(
            was_intent_successful=True,
            data=build_summary(df, tag_to_title, project_tag, tag_to_workday),
        )

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
