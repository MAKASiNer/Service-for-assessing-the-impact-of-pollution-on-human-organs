import logging
from urllib import request, parse, error

from _parsetools import parse_document


logger = logging.getLogger('parser')


HOME_URL = 'https://www.feerc.ru/baikal/'


URLS = [
    'ru/monitoring/air/bulletin/buryat/1',
    'ru/monitoring/air/bulletin/buryat/2',
    'ru/monitoring/air/bulletin/buryat/3',
    'ru/monitoring/air/bulletin/buryat/4',
    'ru/monitoring/air/bulletin/buryat/5',
    'ru/monitoring/air/bulletin/buryat/6',

    'ru/monitoring/air/bulletin/irkutsk/1',
    'ru/monitoring/air/bulletin/irkutsk/2',
    'ru/monitoring/air/bulletin/irkutsk/3',
    'ru/monitoring/air/bulletin/irkutsk/4',
    'ru/monitoring/air/bulletin/irkutsk/5',
    'ru/monitoring/air/bulletin/irkutsk/6',
    'ru/monitoring/air/bulletin/irkutsk/7',
    'ru/monitoring/air/bulletin/irkutsk/8',
    'ru/monitoring/air/bulletin/irkutsk/9',
    'ru/monitoring/air/bulletin/irkutsk/10',

    'ru/monitoring/air/bulletin/zabaikalskoe/1',
    'ru/monitoring/air/bulletin/zabaikalskoe/2',
    'ru/monitoring/air/bulletin/zabaikalskoe/3',
]


def get_actual_data(home_url=HOME_URL, urls=URLS):

    data = dict()

    for url in urls:
        url = parse.urljoin(home_url, url)

        try:
            res = request.urlopen(url, timeout=10)
            region = ''.join(url.split('/')[-2:])

            if res.status == 200:
                logger.info('url: %s status code: %s ', res.url, res.status)
                data[region] = parse_document(res.read())
            else:
                logger.error('url: %s status code: %s ', res.url, res.status)

        except error.URLError as err:
            logger.error('url: %s error: %s', url, err)

    return data


if __name__ == '__main__':
    from pprint import pprint
    data = get_actual_data()
    pprint(data, indent=4, sort_dicts=False, compact=False)
