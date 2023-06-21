import json
import requests
from datetime import date, timedelta
from geopy.geocoders import Nominatim
from web.models import Substance, MeasurementRegion, AtmosphericMeasurement, DataSource


def preload_regions(formula, date, index):
    geolocator = Nominatim(user_agent="geoapiExercises")

    url = 'https://www.feerc.ru/baikal/modules/monitoring/air/ask_overall/AirMonitoring4/services/getData.php'
    payload = {
        'lang': 'ru',
        'date': date.strftime('%d.%m.%Y'),
        'type': formula,
        'index': index,
    }
    res = requests.get(url, payload)
    data = json.loads(res.content).get('data', [])

    for x in data:
        location = geolocator.reverse(f"{x['lat']}, {x['lng']}")
        attrs = {
            'name': x['name'],
            'address': location.raw['display_name'],
            'lat': location.raw['lat'],
            'lng': location.raw['lon'],
            'postcode': location.raw['address'].get('postcode')
        }
        MeasurementRegion.get_or_create(**attrs)


def load_data(start: date, end: date = None, _preload_regions=False):

    if isinstance(start, str):
        start = date.fromisoformat(start)

    if not end:
        end = start
    elif isinstance(end, str):
        end = date.fromisoformat(end)

    source = DataSource.get_or_create(name='Росгидромет', address='https://www.feerc.ru/baikal/ru/monitoring/air/ask_overall')[0]

    idxs_per_substance = [
        (0, 'CO'),
        (1, 'NO'),
        (2, 'NO2'),
        (4, 'SO2'),
        (5, 'H2S'),
        (6, 'O3'),
        (7, 'NH3'),
        (10, 'PM10D'),
        (11, 'PM25D'),
        (12, 'PM1'),
    ]

    idxs_per_region = [
        (3020101, 'Улан-Удэ,пр.50 лет Октября, д.15'),
        (3020102, 'Улан-Удэ,ул.Бабушкина, участок № 16'),
        (3020103, 'Селенгинск,Южный мкр.'),
        (3020104, 'Селенгинск,с.Брянск, ул.Новая, д.19'),
        (3020105, 'Гусиноозерск,ул.Ленина, д.24'),
        (3020106, 'Улан-Удэ, ул.Революции 1905 г., участок № 74'),
        (38020101, 'Иркутск,ул.Севастопольская, д.239а'),
        (38020102, 'Байкальск,Промбаза, МС'),
        (38020103, 'Ангарск,ул.Ворошилова, д.49'),
        (38020104, 'Ангарск,ул.Московская, п.о.30'),
        (38020105, 'Усолье-Сибирское,Комсомольский пр., д.33'),
        (38020106, 'Шелехов,Комсомольский бульвар, д.14'),
        (38020107, 'Иркутск,ул.Лермонтова, д.317'),
        (38020108, 'Иркутск,ул.Партизанская, д.76'),
        (38020109, 'Иркутск,ул.Мира, д.101'),
        (38020110, 'Иркутск,ул.Сухэ-Батора, д.5'),
        (38020112, 'Свирск,ул.Ангарская, д.2'),
        (38020114, 'Усолье-Сибирское,ул.Интернациональная, д.52'),
        (38020121, 'Саянск,мкр.Благовещенский  д.1, МС'),
        (38020123, 'Черемхово,ул.Шевченко, д.72'),
        (75020101, 'Чита,ул.Красной Звезды, д.75, МС'),
        (75020102, 'Чита,ул.Лазо, д.30'),
        (75020103, 'Петровск-Забайкальский,ул.Маяковского, д.25а, МС'),
        (75020107, 'Чита,ул.Алексея Брызгалова, д.32/33')
    ]
    
    while start <= end:
        
        for index, formula in idxs_per_substance:
            
            if _preload_regions:
                preload_regions(formula, start, index)

            for ind, name in idxs_per_region:
                url = 'https://www.feerc.ru/baikal/modules/monitoring/air/ask_overall/AirMonitoring4/services/getStatData.php'
                payload = {
                    'date': start.strftime('%d.%m.%Y'),
                    'type': formula,
                    'ind': ind
                }
                res = requests.get(url, payload)
                data = json.loads(res.content).get('data', [])
                for x in data:
                    attrs = {
                        'date': date(day=int(x.get('day')), month=int(x.get('month')), year=int(x.get('year'))),
                        'substance': Substance.get(formula=formula),
                        'region': MeasurementRegion.get(name=name),
                        'source': source,
                        'stat': x.get('y')
                    }
                    try:
                        AtmosphericMeasurement.get_or_create(**attrs)
                    except:
                        pass

        start += timedelta(days=1)