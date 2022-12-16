import re
from flask import *
from flask_mail import Message
from urllib.parse import urljoin
from werkzeug.security import generate_password_hash, check_password_hash

from web import app, mail
from .models import Users, Tokens


def ffield(label, name, type, error_feedbacks=None):

    if not error_feedbacks:
        error_feedbacks = []
        valid = True
    else:
        valid = False

    return {
        'label': label,
        'valid': valid,
        'name': name,
        'type': type,
        'error_feedbacks': error_feedbacks
    }


def render_form(title, form, session):
    return render_template(
        'form.html',
        title=title,
        form=form,
        signed=Users.from_session(session) is not None
    )


def render_verify(message, session):
    return render_template(
        'verify.html',
        message=message,
        signed=Users.from_session(session) is not None
    )


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
            msg = Message(html=render_template('verification_mail.html', url=url))
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
            return redirect('/')

    return render_form('Вход', form, session)


# деавторизация
@app.route('/signout', methods=['GET'])
def logout():
    Users.remove_session(session)
    return redirect('/')


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
