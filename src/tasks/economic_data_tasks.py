import requests
from models import models
from models.database import get_celery_db
from celery_app import celery_app
import os
from datetime import date, timedelta, datetime


ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")


@celery_app.task
def get_economic_data():
    get_real_gdp.delay()
    get_cpi.delay()
    get_inflation.delay()
    get_unemployment_rate.delay()


@celery_app.task
def get_real_gdp():
    # First we get the last date in the database
    with get_celery_db() as db:
        db_group = (
            db.query(models.EconomicDataGroup)
            .filter(models.EconomicDataGroup.data_type == "Real GDP")
            .first()
        )

        if not db_group:
            db_group = models.EconomicDataGroup(
                name="Real GDP",
                data_type="Real GDP",
                interval="quarterly",
                unit="USD",
            )

            db.add(db_group)
            db.commit()
            db.refresh(db_group)

        last_date = (
            db.query(models.EconomicData)
            .filter(models.EconomicData.economic_data_group_id == db_group.id)
            .order_by(models.EconomicData.date.desc())
            .first()
        )

        if last_date and last_date.date + timedelta(days=90) < datetime.now():
            return

    # Then we get the data from the API
    url = f"https://www.alphavantage.co/query?function=REAL_GDP&interval=quarterly&apikey={ALPHA_VANTAGE_API_KEY}"

    try:
        response = requests.get(url)
        data = response.json()

    except Exception as e:
        print(e)
        return

    # We add the data to the database
    points = data["data"]
    save_data(db_group.id, last_date.date, points)


@celery_app.task
def get_cpi():
    # First we get the last date in the database
    with get_celery_db() as db:
        db_group = (
            db.query(models.EconomicDataGroup)
            .filter(models.EconomicDataGroup.data_type == "CPI")
            .first()
        )

        if not db_group:
            db_group = models.EconomicDataGroup(
                name="Consumer Price Index for all Urban Consumers",
                data_type="CPI",
                interval="monthly",
                unit="index 1982-1984=100",
            )

            db.add(db_group)
            db.commit()
            db.refresh(db_group)

        last_date = (
            db.query(models.EconomicData)
            .filter(models.EconomicData.economic_data_group_id == db_group.id)
            .order_by(models.EconomicData.date.desc())
            .first()
        )

        if last_date and last_date.date + timedelta(days=27) < datetime.now():
            return

    # Then we get the data from the API
    url = f"https://www.alphavantage.co/query?function=CPI&interval=monthly&apikey={ALPHA_VANTAGE_API_KEY}"

    try:
        response = requests.get(url)
        data = response.json()

    except Exception as e:
        print(e)
        return

    # We add the data to the database
    points = data["data"]
    save_data(db_group.id, last_date.date, points)


def save_data(db_group_id: str, last_date: date, points):
    to_create = []

    with get_celery_db() as db:
        for point in points:
            date = point["date"]
            value = point["value"]

            if date > last_date:
                to_create.append(
                    models.EconomicData(
                        date=date,
                        value=value,
                        economic_data_group_id=db_group_id,
                    )
                )

        db.add_all(to_create)
        db.commit()


@celery_app.task
def get_inflation():
    # First we get the last date in the database
    with get_celery_db() as db:
        db_group = (
            db.query(models.EconomicDataGroup)
            .filter(models.EconomicDataGroup.data_type == "Inflation")
            .first()
        )

        if not db_group:
            db_group = models.EconomicDataGroup(
                name="Inflation - US Consumer Prices",
                data_type="Inflation",
                interval="annual",
                unit="percent",
            )

            db.add(db_group)
            db.commit()
            db.refresh(db_group)

        last_date = (
            db.query(models.EconomicData)
            .filter(models.EconomicData.economic_data_group_id == db_group.id)
            .order_by(models.EconomicData.date.desc())
            .first()
        )

        if last_date and last_date.date + timedelta(days=364) < datetime.now():
            return

    # Then we get the data from the API
    url = f"https://www.alphavantage.co/query?function=INFLATION&apikey={ALPHA_VANTAGE_API_KEY}"

    try:
        response = requests.get(url)
        data = response.json()

    except Exception as e:
        print(e)
        return

    # We add the data to the database
    points = data["data"]
    save_data(db_group.id, last_date.date, points)


@celery_app.task
def get_unemployment_rate():
    # First we get the last date in the database
    with get_celery_db() as db:
        db_group = (
            db.query(models.EconomicDataGroup)
            .filter(models.EconomicDataGroup.data_type == "Unemployment Rate")
            .first()
        )

        if not db_group:
            db_group = models.EconomicDataGroup(
                name="Unemployment Rate",
                data_type="Unemployment Rate",
                interval="monthly",
                unit="percent",
            )

            db.add(db_group)
            db.commit()
            db.refresh(db_group)

        last_date = (
            db.query(models.EconomicData)
            .filter(models.EconomicData.economic_data_group_id == db_group.id)
            .order_by(models.EconomicData.date.desc())
            .first()
        )

        if last_date and last_date.date + timedelta(days=27) < datetime.now():
            return

    # Then we get the data from the API
    url = f"https://www.alphavantage.co/query?function=UNEMPLOYMENT&apikey={ALPHA_VANTAGE_API_KEY}"

    try:
        response = requests.get(url)
        data = response.json()

    except Exception as e:
        print(e)
        return

    # We add the data to the database
    points = data["data"]
    save_data(db_group.id, last_date.date, points)
