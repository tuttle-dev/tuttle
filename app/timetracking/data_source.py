from core.abstractions import SQLModelDataSourceMixin
from tuttle.calendar import ICSCalendar
from core.intent_result import IntentResult
from .model import CloudCalendarInfo, CloudConfigurationResult

from tuttle.cloud import login_iCloud, verify_icloud_session, CloudLoginResult


class TimeTrackingDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the TimeTracking data in the database"""

    def __init__(self):
        super().__init__()

    def load_from_timetracking_file(self, file_name: str, file_path) -> IntentResult:
        """load the time tracking data

        Arguments:
            file_name : name of the uploaded file
            file_path : path to an uploaded ics or spreadsheet file

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : FileCalendar if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        # TODO: this should be specific for loading from a calendar file, there should be another method for the spreadsheet
        try:
            file_calendar = ICSCalendar(name=file_name, path=file_path)
            return IntentResult(was_intent_successful=True, data=file_calendar)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource.load_from_timetracking_file {e.__class__.__name__}",
                exception=e,
            )

    def load_cloud_calendar_data(
        self, info: CloudCalendarInfo, cloud_session: any
    ) -> IntentResult:
        """TODO Attempts to load data given CloudCalendarInfo

        Params:
            info :
                information about the calendar - name, account, provider
            cloud_session :
                a reference to the authenticated cloud session
        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  CloudConfigurationResult(
                        calendar_loaded_successfully = True
                ) if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            return IntentResult(
                was_intent_successful=False,
                log_message="Not implemented",
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource._load_cloud_calendar {e.__class__.__name__}",
                exception=e,
            )

    """ ICLOUD LOGIN STEPS """

    def login_to_icloud(
        self,
        calendar_info: CloudCalendarInfo,
    ):
        """Attempts to authenticate user with their icloud account

        Returns IntentResult
        -------
            data : [CloudCalendarInfo] if was_intent_successful else None

        """
        cloud_login_result: CloudLoginResult = login_iCloud(
            user_name=calendar_info.account, password=calendar_info.password
        )
        return IntentResult(
            was_intent_successful=True,
            data=CloudConfigurationResult(
                request_2fa_code=cloud_login_result.request_2fa_code,
                session_ref=cloud_login_result.icloud_session_ref,
                cloud_acc_configured_successfully=cloud_login_result.is_logged_in,
                auth_error_occurred=cloud_login_result.auth_error_occured,
            ),
        )

    def verify_icloud_with_2fa(
        self,
        login_result: CloudConfigurationResult,
        two_factor_code: str,
    ) -> IntentResult:
        """Attempts to verify an icloud session given a 2fa code

        Returns
        -------
            data as CloudConfigurationResult
        """
        session_res = verify_icloud_session(
            iCloud=login_result.session_ref,
            two_factor_auth_code=two_factor_code,
        )
        return IntentResult(
            data=CloudConfigurationResult(
                cloud_acc_configured_successfully=session_res.is_logged_in,
                session_ref=session_res.icloud_session_ref,
            )
        )

    """ GOOGLE LOGIN STEPS """

    def login_to_google(
        self,
        calendar_info: CloudCalendarInfo,
    ):
        # TODO
        return IntentResult(
            was_intent_successful=False,
            log_message="Not implemented",
        )

    def verify_google_with_2fa(
        self,
        login_result: CloudConfigurationResult,
        two_factor_code: str,
    ):
        # TODO
        return IntentResult(
            was_intent_successful=False,
            log_message="Not implemented",
        )
