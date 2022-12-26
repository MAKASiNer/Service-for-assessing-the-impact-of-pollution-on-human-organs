from datetime import timedelta

from web import scheduler, SCRAPING_INTENSITY, CLEARING_INTENSITY
from feerc import get_actual_data
from .models import MeasurementRegions, AtmosphericMeasurements, Tokens


def cyclic_parsing():
    data = get_actual_data()
    for region_index, reports in data.items():

        region, _ = MeasurementRegions.get_or_create(region_index=region_index)

        for report in reports:
            date, end = report['date']

            while date <= end:
                keys = {'CO': 'co', 'NO': 'no', 'NO2': 'no2', 'SO2': 'so2', 'H2S': 'h2s', 'O3': 'o3',
                        'NH3': 'nh3', 'CH4': 'ch4', 'ΣCH': 'σch', 'PM2.5': 'pm25', 'PM10': 'pm10'}

                AtmosphericMeasurements.get_or_create(
                    date=date,
                    region=region,
                    **{keys[k]: v for k, v in report['measures'].items()}
                )
                
                date += timedelta(days=1)


def clearing_tokens():
    for token in Tokens.filter():
        if token.is_expired():
            Tokens.delete_by_id(token)
            

#cyclic_parsing()

# автоматический парсинг
scheduler.add_job(
    id=cyclic_parsing.__name__, func=cyclic_parsing, trigger='interval', seconds=SCRAPING_INTENSITY)

# автоматическая чистка бд
scheduler.add_job(
    id=clearing_tokens.__name__, func=clearing_tokens, trigger='interval', seconds=CLEARING_INTENSITY)

