from lxml import html
from datetime import datetime, date


def float_or_none(v):
    if v is None:
        return None
    return float(v)


def parse_date(date_str):
    now_y = datetime.now().year
    months_rus = [
        'января', 'февраля', 'марта',
        'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября',
        'октября', 'ноября', 'декабря'
    ]

    date_start, date_end = date_str.split(' - ')

    a, b = date_start.split()
    start_d, start_m, start_y = int(a), months_rus.index(b) + 1, now_y

    a, b = date_end.split()
    end_d, end_m, end_y = int(a), months_rus.index(b) + 1, now_y

    if start_m == 12 and start_d + 7 > 31:
        start_y = now_y - 1

    return date(start_y, start_m, start_d), date(end_y, end_m, end_d)



def _parse_document(document):

    measurements = list()
    for j, col in enumerate(document.xpath('//*[@id="content"]/table/tr[5]/td'), 2):
        measurements.append(''.join(col.itertext()))

    data = list()
    for row in (17, 18, 19):
        if (all :=  document.xpath(f'//*[@id="content"]/table/tr[{row}]/td[1]')):
            date = list(parse_date(all[0].text))

        measures = {}
        for i, title in enumerate(measurements, 2):
            if (all := document.xpath(f'//*[@id="content"]/table/tr[{row}]/td[{i}]')):
                measures[title] = float_or_none(all[0].text)

        data.append({
            'date': date,
            'measures': measures,
        })

    return data


def parse_document(document, encoding='utf-8', errors='ignore'):

    if isinstance(document, str):
        doc = html.fromstring(document)
        return _parse_document(doc)

    elif isinstance(document, bytes):
        doc = html.fromstring(document.decode(encoding, errors))
        return _parse_document(doc)

    else:
        return _parse_document(document)


if __name__ == '__main__':
    from pprint import pprint
    data = parse_document(open('маленький.html', 'rb').read())
    pprint(data, indent=4, sort_dicts=False, compact=False)
