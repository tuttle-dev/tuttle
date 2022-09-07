"""Main application."""
from pathlib import Path
import os
import sys
import datetime

import pandas
import sqlmodel
from sqlmodel import pool

from loguru import logger

from . import model, timetracking, dataviz, rendering, invoicing, calendar, cloud


class Controller:
    """The application controller."""

    def __init__(self, home_dir=None, verbose=False, in_memory=False):
        if home_dir is None:
            self.home = Path.home() / ".tuttle"
        else:
            self.home = Path(home_dir)
        if not os.path.exists(self.home):
            os.mkdir(self.home)
        if in_memory:
            self.db_engine = sqlmodel.create_engine(
                f"sqlite:///",
                echo=verbose,
                connect_args={"check_same_thread": False},
                poolclass=pool.StaticPool,
            )
        else:
            self.db_path = self.home / "tuttle.db"
            self.db_engine = sqlmodel.create_engine(
                f"sqlite:///{self.db_path}",
                echo=verbose,
            )
        # configure logging
        if verbose:
            # TODO:
            pass
        else:
            # TODO:
            pass
        # setup DB
        self.create_model()
        self.db_session = self.create_session()
        # setup visual theme
        # TODO: by user settings
        dataviz.enable_theme("tuttle_dark")

    def create_model(self):
        logger.info("creating database model")
        sqlmodel.SQLModel.metadata.create_all(self.db_engine, checkfirst=True)

    def create_session(self):
        return sqlmodel.Session(
            self.db_engine,
            expire_on_commit=False,
        )

    def get_session(self):
        return self.db_session

    def clear_database(self):
        """
        Delete the database and rebuild database model.
        """
        self.db_path.unlink()
        self.db_engine = sqlmodel.create_engine(f"sqlite:///{self.db_path}", echo=True)
        self.create_model()

    def store(self, entity):
        """Store an entity in the database."""
        with self.get_session() as session:
            session.add(entity)
            session.commit()

    def delete(self, entity):
        """Delete an entity from the database."""
        with self.get_session() as session:
            session.delete(entity)
            session.commit()

    def store_all(self, entities):
        """Store a collection of entities in the database."""
        with self.get_session() as session:
            for entity in entities:
                session.add(entity)
            session.commit()

    def retrieve_all(self, entity_type):
        with self.get_session() as session:
            entities = session.exec(
                sqlmodel.select(entity_type),
            ).all()
            return entities

    @property
    def contacts(self):
        contacts = self.db_session.exec(
            sqlmodel.select(model.Contact),
        ).all()
        return contacts

    @property
    def contracts(self):
        contracts = self.db_session.exec(
            sqlmodel.select(model.Contract),
        ).all()
        return contracts

    @property
    def projects(self):
        contracts = self.db_session.exec(
            sqlmodel.select(model.Project),
        ).all()
        return contracts

    @property
    def user(self):
        user = self.db_session.exec(sqlmodel.select(model.User)).one()
        return user

    def get_project(
        self,
        title: str = None,
        tag: str = None,
    ):
        """Get a project by title or tag."""
        if title:
            project = self.db_session.exec(
                (sqlmodel.select(model.Project).where(model.Project.title == title))
            ).one()
            return project
        elif tag:
            project = self.db_session.exec(
                (sqlmodel.select(model.Project).where(model.Project.tag == tag))
            ).one()
            return project
        else:
            raise ValueError("either project title or tag required")

    def eval_time_planning(
        self, planning_source, by="project", from_date: datetime.date = None
    ):
        def duration_to_revenue(
            row,
        ):
            if isinstance(row.name, tuple):
                tag = row.name[0]
            else:
                tag = row.name
            project = self.get_project(tag=tag)
            units = row["duration"] / project.contract.unit.to_timedelta()
            rate = project.contract.rate
            revenue = units * float(rate)
            return {
                "units": units,
                "revenue": revenue,
                "currency": project.contract.currency,
            }

        planning_data = timetracking.get_time_planning_data(
            planning_source,
        )
        if by == "project":
            grouped_planning_data = (
                planning_data.filter(["tag", "duration"]).groupby("tag").sum()
            )
        elif by == ("month", "project"):
            grouped_planning_data = (
                planning_data.filter(["tag", "duration"])
                .groupby(["tag", pandas.Grouper(freq="1M")])
                .sum()
            )
        else:
            raise ValueError(f"unrecognized grouping parameter: {by}")
        # postprocess planning data
        expanded_data = grouped_planning_data.join(
            grouped_planning_data.apply(
                duration_to_revenue, axis=1, result_type="expand"
            )
        )
        plot = dataviz.plot_eval_time_planning(
            expanded_data,
            by=by,
        )
        return plot

    def billing(
        self,
        project_tags,
        out_dir,
        period_start,
        period_end=None,
        timetracking_method="calendar",
    ):
        """Generate time sheets and invoices for a given period"""
        # TODO: read method from user settings
        if timetracking_method == "calendar":
            timetracking_calendar = calendar.ICloudCalendar(
                icloud=cloud.login_iCloud(user_name=self.user.icloud_account.user_name),
                # TODO: read from user settings
                name="TimeTracking",
            )
        else:
            raise ValueError(f"unsupported time tracking method: {timetracking_method}")

        for i, tag in enumerate(project_tags):
            project = self.get_project(tag=tag)
            logger.info(f"generating timesheet for {project.title}")
            timesheet = timetracking.generate_timesheet(
                source=timetracking_calendar,
                project=project,
                period_start=period_start,
                period_end=period_end,
                item_description=project.title,
            )
            rendering.render_timesheet(
                user=self.user,
                timesheet=timesheet,
                style="anvil",
                document_format="pdf",
                out_dir=out_dir,
            )
            logger.info(f"generating invoice for {project.title}")
            invoice = invoicing.generate_invoice(
                timesheets=[timesheet],
                contract=project.contract,
                date=datetime.date.today(),
                counter=(i + 1),
            )
            rendering.render_invoice(
                user=self.user,
                invoice=invoice,
                style="anvil",
                document_format="pdf",
                out_dir=out_dir,
            )
