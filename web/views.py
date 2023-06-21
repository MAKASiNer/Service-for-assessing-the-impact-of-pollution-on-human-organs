import re
import csv
from io import StringIO, BytesIO
from flask import *
from datetime import date
from flask_mail import Message
from urllib.parse import urljoin
from werkzeug.security import generate_password_hash, check_password_hash

from web import app, mail
from .models import *


def ffield(label, name, type, error_feedbacks=None):
    return {
        'label': label,
        'valid': not error_feedbacks,
        'name': name,
        'type': type,
        'error_feedbacks': list() if not error_feedbacks else error_feedbacks
    }


def render_base(template_name_or_list, session, **context):
    return render_template(
        template_name_or_list,
        signed=Users.from_session(session) is not None,
        **context
    )


def render_form(title, form, session):
    return render_base('form.html', session=session, title='%s - Air quality' % title, form=form, )


def render_verify(message, session):
    return render_base('verify.html', session=session, message=message)


@app.route('/')
def index():
    return render_base('index.html', session=session)


# авторизация
@app.route('/signup', methods=['GET', 'POST'])
def signup():

    form = [[ffield('Имя', 'fname', 'text'), ffield('Фамилия', 'lname', 'text')],
            [ffield('Почта', 'email', 'email')],
            [ffield('Пароль', 'pass', 'password'), ffield('Повторите пароль', 'rpass', 'password')]]

    if request.method == 'POST':

        fail = False

        fname = request.values['fname']
        if len(fname) < 2:
            form[0][0]['error_feedbacks'].append('Слишком короткое имя')
            form[0][0]['valid'] = False
            fail = True

        lname = request.values['lname']
        if len(lname) < 2:
            form[0][1]['error_feedbacks'].append('Слишком короткая фамилия')
            form[0][1]['valid'] = False
            fail = True

        email = request.values['email']
        if not re.fullmatch(r'^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$', email):
            form[1][0]['error_feedbacks'].append('Неправильный формат')
            form[1][0]['valid'] = False
            fail = True
        elif Users.exists(email):
            form[1][0]['error_feedbacks'].append('Уже занято')
            form[1][0]['valid'] = False
            fail = True

        password = request.values['pass']
        if len(password) < 8:
            form[2][0]['error_feedbacks'].append('Слишком короткий пароль')
            form[2][0]['valid'] = False
            fail = True

        rpass = request.values['rpass']
        if rpass != password:
            form[2][1]['error_feedbacks'].append('Неправильно введен пароль')
            form[2][1]['valid'] = False
            fail = True

        if not fail:
            user = Users.create(
                first_name=fname,
                last_name=lname,
                email=email,
                password=generate_password_hash(password)
            )
            user.signin(session)
            token = Tokens.new(user)
            url = urljoin(request.base_url, url_for('verify', token=token))
            msg = Message(html=render_template(
                'verification_mail.html', url=url))
            msg.add_recipient(user.email)
            mail.send(msg)

            return render_verify('Письмо с ссылкой для подтверждения было выслано вам на почту.', session)

    return render_form('Регистрация', form, session)


@app.route('/signin', methods=['GET', 'POST'])
def signin():

    form = [[ffield('Почта', 'email', 'email')],
            [ffield('Пароль', 'pass', 'password')]]

    if request.method == 'POST':
        password = request.values['pass']
        user = Users.get_or_none(email=request.values['email'])

        if user is None or not check_password_hash(user.password, password):
            form[0][0]['error_feedbacks'].append(
                'Неправильный логин или пароль')
            form[0][0]['valid'] = False
            form[1][0]['error_feedbacks'].append(
                'Неправильный логин или пароль')
            form[1][0]['valid'] = False
        else:
            user.signin(session)
            return redirect(url_for('monitoring'))

    return render_form('Вход', form, session)


# деавторизация
@app.route('/signout', methods=['GET'])
def signout():
    Users.remove_session(session)
    return redirect(url_for('index'))


# верификация
@app.route('/verify/<token>', methods=['GET'])
def verify(token):
    token: Tokens = Tokens.get_or_none(token=token)

    if token is None or token.is_expired():
        msg = 'Ссылка не существует или ее срок истек.'
    else:
        token.user.verified = True
        token.user.save()
        Tokens.delete_by_id(token)
        msg = 'Вы успешно подтвердили почту'

    return render_verify(msg, session)


@app.route('/monitoring')
def monitoring():
    if Users.from_session(session) is None:
        return redirect('/signin')

    kind = request.args.get('kind', 'acute')
    if kind not in ('acute', 'chronic', 'acute hi', 'chronic hi', 'risk'):
        return Response(status=400)

    if kind in ('acute hi', 'chronic hi'):
        options = HealthPoint.possible_all()
    else:
        options = Substance.all()

    return render_base(
        'monitoring.html',
        kind=kind,
        session=session,
        regions=MeasurementRegion.all(),
        options=options,
        min_date=AtmosphericMeasurement.min_date(),
        max_date=AtmosphericMeasurement.max_date()
    )


@app.route('/download/<kind>/<region>/<option>/<start>/<end>')
def download(kind, region, option, start, end):
    if Users.from_session(session) is None:
        return Response(status=401)

    data = make_chart(kind, region, option, start, end)
    header = ('Дата', *[dataset['label'] for dataset in data['datasets']])
    body = zip(data['labels'], *[dataset['data']
               for dataset in data['datasets']])

    file = StringIO()
    writer = csv.writer(file, lineterminator='\n')
    writer.writerows([header])
    writer.writerows(body)

    file.seek(0)
    return send_file(BytesIO(file.read().encode('utf-8', 'replace')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=re.sub(r'[^\w\-_\.]+', '_', f"{data['title']}.csv"))


def dataset(data, label, color, width=2, pradius=0.1):
    return {
        'label': label,
        'fill': color,
        'backgroundColor': color,
        'borderColor': color,
        'data': data,
        'pointRadius': pradius,
        'borderWidth': width,
    }


def select_periods(data, n, threshold=1):
    exc = data >= threshold
    exc_idx  = np.where(np.convolve(exc, np.ones(n), mode='same') == n)[0] - int(np.ceil(n / 2))
    exc_seq = np.concatenate([exc_idx + i for i in range(n + 2)])
    exc_seq = exc_seq[exc_seq < len(data)]
    y = np.asarray([None] * len(data))
    y[exc_seq] = data[exc_seq]
    return y


def make_chart(kind, region, option, start, end):

    if isinstance(region, (int, str)):
        region = MeasurementRegion.get_or_none(id=region)
        if not region:
            return None

    if kind in ('acute hi', 'chronic hi'):
        if isinstance(option, (int, str)):
            hp = HealthPoint.get(id=option)
            substance = [
                x.substance for x in SubstancesInclusionInHealthPoints.all_for_health_point(hp)]
    else:
        if isinstance(option, (int, str)):
            if not (substance := Substance.get_or_none(id=option)):
                return None

    if not start:
        start = AtmosphericMeasurement.min_date()
    else:
        start = date.fromisoformat(start)

    if not end:
        end = AtmosphericMeasurement.max_date()
    else:
        end = date.fromisoformat(end)

    if kind == 'acute':
        c = AtmosphericMeasurement.C(start, end, substance, region, w=ACUTE_W)
        x = list(map(str, c[0, 0, :, 0]))
        y0 = [substance.daily_pdk] * len(x)
        y1 = c[0, 0, :, 1].tolist()
        data = {
            'title': region.name + f' (Среднесуточные {substance.formula})',
            'labels': x,
            'datasets': [dataset(y0, 'ПДК', 'red', width=1, pradius=0),
                         dataset(y1, substance.formula, 'blue')]
        }

    elif kind == 'chronic':
        c = AtmosphericMeasurement.C(start, end, substance, region, w=CHRONIC_W)
        x = list(map(str, c[0, 0, :, 0]))
        y0 = [substance.yearly_pdk] * len(x)
        y1 = c[0, 0, :, 1].tolist()
        data = {
            'title': region.name + f' (Среднегодовые {substance.formula})',
            'labels': x,
            'datasets': [dataset(y0, 'ПДК', 'red', width=1, pradius=0),
                         dataset(y1, substance.formula, 'blue')]
        }

    elif kind == 'acute hi':
        acute_hi = AtmosphericMeasurement.HI('acute', start, end, substance, region)
        x = list(map(str, acute_hi[0, :, 0]))
        y0 = [1] * len(x)
        y1 = acute_hi[0, :, 1].tolist()
        y2 = select_periods( acute_hi[0, :, 1], 5).tolist()

        data = {
            'title': region.name + f' (Острый HI {hp})',
            'labels': x,
            'datasets': [dataset(y0, 'Пороговое значение', 'gray', width=1, pradius=0),
                         dataset(y2, 'Острое влияние', 'red'),
                         dataset(y1, 'Острый HI', 'blue')]
        }

    elif kind == 'chronic hi':
        chronic_hi = AtmosphericMeasurement.HI('chronic', start, end, substance, region)
        x = list(map(str, chronic_hi[0, :, 0]))
        y0 = [1] * len(x)
        y1 = chronic_hi[0, :, 1].tolist()
        y2 = select_periods(chronic_hi[0, :, 1], 90).tolist()

        data = {
            'title': region.name + f' (Хронический HI {hp})',
            'labels': x,
            'datasets': [dataset(y0, 'Пороговое значение', 'gray', width=1, pradius=0),
                         dataset(y2, 'Хроническое влияние', 'red'),
                         dataset(y1, 'Хронический HI', 'blue')]
        }

    elif kind == 'risk':
        acute_risk = AtmosphericMeasurement.risk('acute', start, end, substance, region)
        chronic_risk = AtmosphericMeasurement.risk('chronic', start, end, substance, region)
        x = list(map(str, acute_risk[0, 0, :, 0]))
        y0 = acute_risk[0, 0, :, 1].tolist()
        y1 = chronic_risk[0, 0, :, 1].tolist()

        data = {
            'title': region.name + f' (Индекс опасности)',
            'labels': x,
            'datasets': [dataset(y0, 'Острый risk', 'red'),
                         dataset(y1, 'Хронический risk', 'blue')]
        }

    else:
        return None

    return data


@app.route('/api')
def api():
    '''
    Params:
        start        - левая дата в iso формате (YYYY-MM-DD). По умолчанию старейшая дата в бд.
        end          - правая дата в iso формате (YYYY-MM-DD). По умолчанию новейшая дата в бд.
        region_id    - id региона
        option       - опция (id вещества или органа)
        kind         - тип данных ('acute', 'chronic', 'acute hi', 'chronic hi', 'risk')

    Пример:
        /api?region_id=13&substance_id=8
    '''
    if Users.from_session(session) is None:
        return Response(status=401)

    start = request.args.get('start')
    end = request.args.get('end')
    region = request.args.get('region_id')
    option = request.args.get('option')
    kind = request.args.get('kind')

    data = make_chart(kind, region, option, start, end)
    if not data:
        return Response(status=400)
    else:
        return jsonify(data)
