"""User management: registration, profile updates, demo provisioning."""

import shutil
from pathlib import Path
from typing import Any, Dict

from loguru import logger
from sqlmodel import Session as SqlSession, create_engine as sql_create_engine, select

from ...app_db import AppDatabase
from ...data_dir import get_data_dir
from ...model import Address, BankAccount, Invoice, Timesheet, User
from ..auth.data_source import UserDataSource
from ..core.abstractions import get_active_db, set_active_db
from ..core.intent_result import IntentResult
from ..core.rpc_utils import reset_all
from ...db_schema import ensure_schema


#: Logos are downscaled so the longest edge is at most this many pixels before
#: being stored as a base64 data URI in the per-user database.
LOGO_MAX_DIMENSION = 600

#: Signatures are stored at higher resolution for crisp 300 DPI print at ~5 cm.
SIGNATURE_MAX_DIMENSION = 1200


def _normalize_logo(data_uri: str) -> str:
    """Validate, downscale, and re-encode a logo image as a PNG data URI.

    Accepts a ``data:image/...;base64,<...>`` string (or a bare base64 string),
    decodes it via PIL, scales the longest edge down to ``LOGO_MAX_DIMENSION``
    (never up), and returns a ``data:image/png;base64,<...>`` string. Raises on
    anything that is not a decodable image.
    """
    import base64
    import io

    import PIL.Image

    encoded = data_uri.split(",", 1)[1] if data_uri.startswith("data:") else data_uri
    raw = base64.b64decode(encoded)

    with PIL.Image.open(io.BytesIO(raw)) as img:
        img = img.convert("RGBA")
        # thumbnail() preserves aspect ratio and is a no-op when already smaller.
        img.thumbnail((LOGO_MAX_DIMENSION, LOGO_MAX_DIMENSION), PIL.Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _normalize_signature(data_uri: str) -> str:
    """Process a signature image: remove background, crop, and encode as PNG data URI.

    Accepts a photo or scan of a hand-written signature on paper. Automatically
    removes the paper background via soft alpha masking, darkens the ink, crops
    to the bounding box of the signature strokes, and returns a high-resolution
    transparent PNG suitable for embedding in documents.
    """
    import base64
    import io

    import numpy as np
    import PIL.Image

    encoded = data_uri.split(",", 1)[1] if data_uri.startswith("data:") else data_uri
    raw = base64.b64decode(encoded)

    with PIL.Image.open(io.BytesIO(raw)) as img:
        img = img.convert("RGBA")
        arr = np.array(img, dtype=np.float32)

    # Background detection: sample 10px-deep strips from all four corners
    h, w = arr.shape[:2]
    margin = min(10, h // 4, w // 4)
    corners = np.concatenate(
        [
            arr[:margin, :margin, :3].reshape(-1, 3),
            arr[:margin, -margin:, :3].reshape(-1, 3),
            arr[-margin:, :margin, :3].reshape(-1, 3),
            arr[-margin:, -margin:, :3].reshape(-1, 3),
        ]
    )
    bg_color = np.median(corners, axis=0)

    # Per-pixel color distance from background
    rgb = arr[:, :, :3]
    dist = np.sqrt(np.sum((rgb - bg_color) ** 2, axis=2))

    # Soft alpha: smooth falloff between thresholds
    low_thresh = 25.0
    high_thresh = 80.0
    alpha = np.clip((dist - low_thresh) / (high_thresh - low_thresh), 0.0, 1.0)

    # Darken ink toward black for consistent rendering regardless of lighting
    ink_alpha_mask = alpha > 0.1
    if ink_alpha_mask.any():
        for c in range(3):
            channel = arr[:, :, c]
            channel[ink_alpha_mask] = channel[ink_alpha_mask] * 0.2
            arr[:, :, c] = channel

    arr[:, :, 3] = alpha * 255.0

    # Crop to bounding box of non-transparent pixels
    opaque_mask = alpha > 0.01
    rows = np.any(opaque_mask, axis=1)
    cols = np.any(opaque_mask, axis=0)
    if rows.any() and cols.any():
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        arr = arr[rmin : rmax + 1, cmin : cmax + 1]

    result = PIL.Image.fromarray(arr.astype(np.uint8), "RGBA")
    result.thumbnail(
        (SIGNATURE_MAX_DIMENSION, SIGNATURE_MAX_DIMENSION), PIL.Image.LANCZOS
    )
    buf = io.BytesIO()
    result.save(buf, format="PNG")

    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class UsersIntent:
    """Manages the user registry (app.db) and per-user profile (user.db)."""

    def __init__(self):
        self._app_db = AppDatabase()

    # -- helpers ---------------------------------------------------------------

    def _ensure_user_db(self, db_path: Path):
        ensure_schema(f"sqlite:///{db_path}")

    def _switch_to_user_db(self, db_file: str):
        """Switch the active per-user database and flush intent caches."""
        db_path = self._app_db.get_user_db_path(db_file)
        reg = self._app_db.get_user_by_db_file(db_file)
        is_demo = reg and reg.is_demo if reg else False
        self._ensure_user_db(db_path)
        set_active_db(db_path)
        self._app_db.set_active(db_file)
        reset_all()
        logger.info(f"Switched to user DB: {db_file}")

        if is_demo:
            self._ensure_demo_timetracking(db_path)

    def _ensure_demo_timetracking(self, db_path: Path = None):
        """Repopulate demo time-tracking data for the Harry Tuttle demo user."""
        from ..timetracking.data_source import TimeTrackingDataFrameSource

        ds = TimeTrackingDataFrameSource()
        if ds.get_data_frame() is not None:
            return
        try:
            from sqlmodel import Session, create_engine, select
            from ...model import Project
            from ...demo import create_fake_calendar
            from ...calendar import ICSCalendar

            if db_path is None:
                db_path = get_active_db()

            engine = create_engine(f"sqlite:///{db_path}")
            with Session(engine) as session:
                projects = session.exec(select(Project)).all()
            if not projects:
                return
            cal = ICSCalendar(
                name="Demo calendar",
                ics_calendar=create_fake_calendar(list(projects)),
            )
            df = cal.to_data()
            ds.store_data_frame(df)
            ds.save_to_cache()
            ds.save_source_config("demo", calendar_name="Demo calendar")
            logger.info(f"Repopulated {len(df)} demo time-tracking events")
        except Exception as ex:
            logger.warning(f"Could not repopulate demo timetracking: {ex}")

    # -- user list / switch / delete ------------------------------------------

    def list(self) -> IntentResult:
        users = self._app_db.list_users()
        return IntentResult(was_intent_successful=True, data=users)

    list_users = list

    def switch(self, db_file: str, **_kw) -> IntentResult:
        self._switch_to_user_db(db_file)
        return IntentResult(was_intent_successful=True, data=None)

    def delete(self, db_file: str, **_kw) -> IntentResult:
        """Delete a user, their database, and all rendered output files."""
        db_path = self._app_db.get_user_db_path(db_file)
        self._cleanup_rendered_files(db_path)
        removed = self._app_db.remove_user(db_file)
        if removed:
            reset_all()
        return IntentResult(was_intent_successful=True, data=removed)

    def _cleanup_rendered_files(self, db_path: Path):
        """Remove rendered invoices and timesheets produced by this user."""
        if not db_path.exists():
            return
        tuttle_dir = get_data_dir()
        invoices_dir = tuttle_dir / "Invoices"
        timesheets_dir = tuttle_dir / "Timesheets"
        try:
            engine = sql_create_engine(f"sqlite:///{db_path}")
            with SqlSession(engine) as s:
                invoices = s.exec(select(Invoice)).all()
                for inv in invoices:
                    if not inv.rendered:
                        continue
                    pdf = invoices_dir / inv.file_name
                    if pdf.exists():
                        pdf.unlink()
                        logger.info(f"Deleted rendered invoice: {pdf}")
                    prefix_dir = invoices_dir / inv.prefix
                    if prefix_dir.is_dir():
                        shutil.rmtree(prefix_dir)
                        logger.info(f"Deleted invoice directory: {prefix_dir}")

                timesheets = s.exec(select(Timesheet)).all()
                for ts in timesheets:
                    if not ts.rendered:
                        continue
                    for ext in ("pdf", "html"):
                        f = timesheets_dir / f"{ts.prefix}.{ext}"
                        if f.exists():
                            f.unlink()
                            logger.info(f"Deleted rendered timesheet: {f}")
                    prefix_dir = timesheets_dir / ts.prefix
                    if prefix_dir.is_dir():
                        shutil.rmtree(prefix_dir)
                        logger.info(f"Deleted timesheet directory: {prefix_dir}")
            engine.dispose()
        except Exception as ex:
            logger.warning(f"Could not clean up rendered files for {db_path}: {ex}")

    def get_active(self) -> IntentResult:
        """Return the active registered user with their profile.

        Returns a flat dict with registration fields at the top level
        and the user profile nested under ``profile``.
        """
        active_path = get_active_db()
        active_file = active_path.name
        reg = self._app_db.get_user_by_db_file(active_file)
        if not reg:
            return IntentResult(was_intent_successful=True, data=None)
        try:
            ds = UserDataSource()
            profile = ds.get_user()
        except Exception:
            profile = None
        data = reg.model_dump()
        data["profile"] = profile
        return IntentResult(was_intent_successful=True, data=data)

    # -- create ---------------------------------------------------------------

    def create(self, params: Dict[str, Any], **_kw) -> IntentResult:
        """Register a new user and initialise their database."""
        name = params["name"]
        subtitle = params.get("subtitle", "")
        reg = self._app_db.add_user(name=name, subtitle=subtitle)
        db_path = self._app_db.get_user_db_path(reg.db_file)
        ensure_schema(f"sqlite:///{db_path}")

        engine = sql_create_engine(f"sqlite:///{db_path}")
        with SqlSession(engine) as s:
            address = Address(
                street=params.get("street", ""),
                number=params.get("street_num", ""),
                postal_code=params.get("postal_code", ""),
                city=params.get("city", ""),
                country=params.get("country", ""),
            )
            user = User(
                name=name,
                subtitle=subtitle,
                email=params.get("email", ""),
                phone_number=params.get("phone", ""),
                website=params.get("website", ""),
                operating_country=params.get("operating_country", "Germany"),
                VAT_number=params.get("vat_number", ""),
                tax_number=params.get("tax_number", ""),
                address=address,
            )
            bank = params.get("bank_account")
            if bank and any(bank.get(k) for k in ("IBAN", "BIC", "name")):
                user.bank_account = BankAccount(
                    name=bank.get("name", ""),
                    IBAN=bank.get("IBAN", ""),
                    BIC=bank.get("BIC", ""),
                )
            s.add(user)
            s.commit()
        engine.dispose()

        self._switch_to_user_db(reg.db_file)
        return IntentResult(was_intent_successful=True, data=reg)

    # -- profile update -------------------------------------------------------

    def update_profile(self, profile_data: Dict[str, Any]) -> IntentResult:
        """Update the active user's profile from a dict."""
        ds = UserDataSource()
        profile = ds.get_user()
        if not profile:
            return IntentResult(
                was_intent_successful=False,
                error_msg="No user profile found",
            )

        for k in (
            "name",
            "subtitle",
            "email",
            "phone_number",
            "website",
            "VAT_number",
            "tax_number",
            "operating_country",
        ):
            if k in profile_data:
                setattr(profile, k, profile_data[k])

        if "logo" in profile_data:
            raw_logo = profile_data["logo"]
            if not raw_logo:
                profile.logo = None
            else:
                try:
                    profile.logo = _normalize_logo(raw_logo)
                except Exception as ex:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg=f"Could not process logo image: {ex}",
                    )

        if "signature" in profile_data:
            raw_sig = profile_data["signature"]
            if not raw_sig:
                profile.signature = None
            else:
                try:
                    profile.signature = _normalize_signature(raw_sig)
                except Exception as ex:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg=f"Could not process signature image: {ex}",
                    )

        if "accent_color" in profile_data:
            profile.accent_color = profile_data["accent_color"] or None

        addr = profile_data.get("address")
        if addr:
            if profile.address:
                for k in ("street", "number", "postal_code", "city", "country"):
                    if k in addr:
                        setattr(profile.address, k, addr[k])
            else:
                profile.address = Address(
                    **{
                        k: v
                        for k, v in addr.items()
                        if k != "id" and not k.startswith("_")
                    }
                )

        bank = profile_data.get("bank_account")
        if bank is not None:
            if profile.bank_account:
                for k in ("name", "IBAN", "BIC"):
                    if k in bank:
                        setattr(profile.bank_account, k, bank[k])
            else:
                profile.bank_account = BankAccount(
                    name=bank.get("name", ""),
                    IBAN=bank.get("IBAN", ""),
                    BIC=bank.get("BIC", ""),
                )

        with ds.create_session() as s:
            s.add(profile)
            s.commit()
            s.refresh(profile)

        # Sync name/subtitle back to the app.db registration record.
        active_file = get_active_db().name
        reg = self._app_db.get_user_by_db_file(active_file)
        if reg and (
            reg.name != profile.name or reg.subtitle != (profile.subtitle or "")
        ):
            with self._app_db._session() as s:
                db_reg = s.get(type(reg), reg.id)
                if db_reg:
                    db_reg.name = profile.name
                    db_reg.subtitle = profile.subtitle or ""
                    s.add(db_reg)
                    s.commit()

        return IntentResult(was_intent_successful=True, data=profile)

    # -- demo -----------------------------------------------------------------

    def ensure_demo(
        self,
        invoice_language: str = "en",
        invoice_template: str = "invoice-modern",
    ) -> IntentResult:
        """Ensure the Harry Tuttle demo user exists."""
        from ...demo import install_demo_data
        from ..timetracking.data_source import TimeTrackingDataFrameSource

        if self._app_db.get_user_by_db_file("harry-tuttle.db"):
            reg = self._app_db.get_user_by_db_file("harry-tuttle.db")
            return IntentResult(was_intent_successful=True, data=reg)

        reg = self._app_db.add_user(
            name="Harry Tuttle",
            subtitle="Heating Engineer",
            is_demo=True,
            db_file="harry-tuttle.db",
        )
        db_path = self._app_db.get_user_db_path(reg.db_file)
        if db_path.exists():
            db_path.unlink()

        def _cache_demo_timetracking(df):
            ds = TimeTrackingDataFrameSource()
            ds.store_data_frame(df)
            ds.save_to_cache()
            ds.save_source_config("demo", calendar_name="Demo calendar")
            logger.info(f"Cached {len(df)} demo time-tracking events")

        install_demo_data(
            n_projects=4,
            db_path=str(db_path),
            on_cache_timetracking_dataframe=_cache_demo_timetracking,
            invoice_language=invoice_language,
            invoice_template=invoice_template,
        )
        logger.info("Demo user Harry Tuttle created with heating-repair data")
        return IntentResult(was_intent_successful=True, data=reg)

    def ensure_db(self, **_kw) -> IntentResult:
        """Ensure app.db exists and switch to last-active user if any."""
        self._app_db.ensure()
        self._app_db.migrate_llm_config_from_json()

        last = self._app_db.get_last_active()
        if last:
            self._switch_to_user_db(last.db_file)
        else:
            users = self._app_db.list_users()
            if users:
                self._switch_to_user_db(users[0].db_file)
        return IntentResult(was_intent_successful=True, data=None)
