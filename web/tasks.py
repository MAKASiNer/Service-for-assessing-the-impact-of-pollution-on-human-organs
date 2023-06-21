from datetime import datetime, timedelta


from web import scheduler, SCRAPING_INTENSITY, CLEARING_INTENSITY
from myparser import load_data
from .models import Tokens, AtmosphericMeasurement


def clearing_tokens():
    for token in Tokens.filter():
        if token.is_expired():
            Tokens.delete_by_id(token)


def parse_data():
    # now = datetime.now().date()
    # if now == AtmosphericMeasurement.max_date():
    #     return None
    # else:
    #     yesterday = now - timedelta(days=1)
    #     while AtmosphericMeasurement.max_date() < yesterday:
    #         load_data(AtmosphericMeasurement.max_date() + timedelta(days=30))
    #     load_data(now)
    #     load_data(AtmosphericMeasurement.min_date())
    now = datetime.now().date()
    if now != AtmosphericMeasurement.max_date():
        load_data(now)
    load_data(AtmosphericMeasurement.min_date())

    

# автоматическая чистка бд
scheduler.add_job(
    id=clearing_tokens.__name__,
    func=clearing_tokens,
    trigger='interval',
    seconds=CLEARING_INTENSITY)

# автоматический парсинг
scheduler.add_job(
    id=parse_data.__name__,
    func=parse_data,
    trigger='interval',
    seconds=SCRAPING_INTENSITY
)