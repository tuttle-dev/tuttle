from core.abstractions import SQLModelDataSourceMixin

from core.intent_result import IntentResult
from .model import CloudCalendarInfo, CloudConfigurationResult
from typing import Optional
from tuttle.cloud import login_iCloud, verify_icloud_session, CloudLoginResult
from preferences.model import CloudAccounts


class TimeTrackingDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the TimeTracking data in the database"""

    def __init__(self):
        super().__init__()

    def load_from_timetracking_file(self, file_path) -> IntentResult:
        """TODO load the time tracking data

        Arguments:
            file_path : path to an uploaded ics or spreadsheet file

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  #TODO? was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            return IntentResult(
                was_intent_successful=False, log_message="Un Implemented error"
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource.load_from_timetracking_file {e.__class__.__name__}",
                exception=e,
            )

    def _load_cloud_calendar_data(
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
                log_message="Un Implemented error",
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource._load_cloud_calendar {e.__class__.__name__}",
                exception=e,
            )

    def configure_cloud_acc_and_load_calendar_data(
        self,
        calendar_info: CloudCalendarInfo,
        two_factor_code: Optional[str] = "",
        prev_un_verified_login_res: Optional[CloudConfigurationResult] = None,
    ):
        """Attempts to configure cloud account and load data given CloudCalendarInfo
        *This is a multi-step process

        Params
        ------
        calendar_info: CloudCalendarInfo
            information about the calendar to load and it's associated account
        two_factor_code: Optional[str]
            set during an Optional second step if user has been asked to enter a 2fa code
        prev_un_verified_login_res : CloudConfigurationResult
            keeps track of the session if any that is pending a 2fa code

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : CloudConfigurationResult if was_intent_successful else None
                    the data result can be CloudConfigurationResult(request_2fa_code = True) if a 2fa code is needed
                    Or CloudConfigurationResult(request_2fa_code = True, provided_2fa_code_is_invalid = True) if a 2fa code is needed and the user just provided an incorrect one
                    Or CloudConfigurationResult(cloud_acc_configured_successfully = True) when and if configuration steps complete successfully and a cloud session is created (user is logged in)
                    Or CloudConfigurationResult(calendar_loaded_successfully = True) if calendar data is loaded succesffuly
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """

        res: IntentResult = None
        if not two_factor_code:
            # STEP 1 user is login in
            if calendar_info.provider == CloudAccounts.ICloud.value:
                res = self._login_to_icloud(calendar_info=calendar_info)
            else:
                # TODO other providers - we assume only google below?
                res = self._login_to_google(calendar_info=calendar_info)
        else:
            # STEP 2 complete login with 2FA
            if calendar_info.provider == CloudAccounts.ICloud.value:
                res = self._verify_icloud_with_2fa(
                    login_result=prev_un_verified_login_res,
                    two_factor_code=two_factor_code,
                )
            else:
                # TODO other providers - we assume only google below?
                res = self._verify_google_with_2fa(
                    login_result=prev_un_verified_login_res,
                    two_factor_code=two_factor_code,
                )
        config_result: CloudConfigurationResult = res.data
        if config_result and config_result.cloud_acc_configured_successfully:
            # proceed to load cloud calendar data
            return self._load_cloud_calendar_data(
                info=calendar_info, cloud_session=res.session_ref
            )
        else:
            return res

    """ ICLOUD LOGIN STEPS """

    def _login_to_icloud(
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

    def _verify_icloud_with_2fa(
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

    def _login_to_google(
        self,
        calendar_info: CloudCalendarInfo,
    ):
        # TODO
        return IntentResult(
            was_intent_successful=False,
            log_message="Un Implemented error",
        )

    def _verify_google_with_2fa(
        self,
        login_result: CloudConfigurationResult,
        two_factor_code: str,
    ):
        # TODO
        return IntentResult(
            was_intent_successful=False,
            log_message="Un Implemented error",
        )
