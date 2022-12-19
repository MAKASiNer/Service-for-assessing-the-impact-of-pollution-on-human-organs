import re
from flask import *
from datetime import date, timedelta
from flask_mail import Message
from urllib.parse import urljoin
from werkzeug.security import generate_password_hash, check_password_hash

from web import app, mail
from .models import Users, Tokens, AtmosphericMeasurements, MeasurementRegions


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
    return str(Users.from_session(session))


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
    return render_base(
        'monitoring.html',
        session=session,
        regions=MeasurementRegions.filter(),
        min_date=AtmosphericMeasurements.min_date(),
        max_date=AtmosphericMeasurements.max_date()
    )


# рест апи
@app.route('/api')
def api():
    '''
    Params:
        start        - левая дата в iso формате (YYYY-MM-DD). По умолчанию старейшая дата в бд.
        end          - правая дата в iso формате (YYYY-MM-DD). По умолчанию новейшая дата в бд.
        region_index - регион.
    
    Пример:
        /api?start=2022-12-11&region_index=buryat2
    '''
    if Users.from_session(session) is None:
        return Response(status=401)

    if (v := request.args.get('start')):
        start = date.fromisoformat(v)
    else:
        start = AtmosphericMeasurements.min_date()

    if (v := request.args.get('end')):
        end = date.fromisoformat(v)
    else:
        end = AtmosphericMeasurements.max_date()

    if not (region := MeasurementRegions.get_or_none(region_index=request.args.get('region_index'))):
        return Response(status=400)

    data = {
        'title': region.region_name,
        'labels': [str(start + timedelta(days=x)) for x in range((end - start).days + 1)],
        'measures': [
            {
                'data': [],
                'label': m
            } for m in ('CO', 'NO', 'NO2', 'SO2', 'H2S', 'O3', 'NH3', 'CH4', 'ΣCH', 'PM2.5', 'PM10')
        ]
    }

    for measure in AtmosphericMeasurements.select_by_timerange(start, end, region):
        data['measures'][0]['data'].append(measure.co)
        data['measures'][1]['data'].append(measure.no)
        data['measures'][2]['data'].append(measure.no2)
        data['measures'][3]['data'].append(measure.so2)
        data['measures'][4]['data'].append(measure.h2s)
        data['measures'][5]['data'].append(measure.o3)
        data['measures'][6]['data'].append(measure.nh3)
        data['measures'][7]['data'].append(measure.ch4)
        data['measures'][8]['data'].append(measure.σch)
        data['measures'][9]['data'].append(measure.pm25)
        data['measures'][10]['data'].append(measure.pm10)

    return jsonify(data)
