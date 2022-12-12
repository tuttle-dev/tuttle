"""helper functions for manipulating dates"""
import datetime


DAYS_IN_A_WEEK = 7


def get_date_as_str(date: datetime.date, hide_year: bool = False):
    if hide_year:
        return f"{date.day} / {date.month}"
    else:
        return f"{date.day} / {date.month} / {date.year}"


def get_last_seven_days():
    today = datetime.date.today()
    last_seven = []
    i = DAYS_IN_A_WEEK - 1
    while i >= 0:
        past_day = today - datetime.timedelta(days=i)
        last_seven.append(get_date_as_str(past_day, hide_year=True))
        i = i - 1
    return last_seven
