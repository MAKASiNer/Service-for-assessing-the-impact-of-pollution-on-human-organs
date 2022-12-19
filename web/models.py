import peewee as pw
from peewee import fn
from uuid import uuid4
from datetime import datetime, timedelta, date as date_t
from config import DB_DBMS, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


if DB_DBMS == 'sqlite':
    db = pw.SqliteDatabase(DB_NAME)

elif DB_DBMS == 'mysql':
    db = pw.MySQLDatabase(
        database=DB_NAME,
        user=DB_USER,
        passwd=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

elif DB_DBMS == 'postgresql':
    db = pw.PostgresqlDatabase(
        database=DB_NAME,
        user=DB_USER,
        passwd=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

else:
    raise RuntimeError("Unavailable dbms '%s'" % DB_DBMS)


class BaseModel(pw.Model):
    class Meta:
        database = db


class Users(BaseModel):
    '''
    Пользователи

    Fields:
        id:         int  - pk
        first_name: str  - имя
        last_name:  str  - фамилия
        email:      str  - почта
        password:   str  - хеш пароля
        verified:   bool - почта подтверждена?
    '''
    first_name: str = pw.CharField(255)
    last_name: str = pw.CharField(255)
    email: str = pw.CharField(255, unique=True)
    verified: bool = pw.BooleanField(255, default=False)
    password: str = pw.CharField(255)

    @staticmethod
    def exists(email):
        return Users.get_or_none(email=email) is not None

    @staticmethod
    def from_session(session):
        pass

    @staticmethod
    def from_session(session):
        try:
            return Users.get_or_none(
                id=session['user_id'],
                email=session['email'],
                password=session['password']
            )
        except KeyError:
            return None

    @staticmethod
    def remove_session(session):
        '''True если сессия была удалена'''
        user = Users.from_session(session)
        if user is not None:
            user.signout(session)
            return True
        return False

    def has_session(self, session):
        return (session['user_id'] == self.id and
                session['email'] == self.email and
                session['password'] == self.password)

    def signin(self, session):
        session['user_id'] = self.id
        session['email'] = self.email
        session['password'] = self.password

    def signout(self, session):
        '''True если сессия успешно удалена'''
        try:
            session.pop('user_id')
            session.pop('email')
            session.pop('password')
            return True
        except KeyError:
            return False


class Tokens(BaseModel):
    '''
    Токены верификации

    Fields:
        id:         int      - pk
        user:       Users    - чей токен?
        token:      str      - токен
        expires_on: datetime - когда истекает?
    '''
    user: Users = pw.ForeignKeyField(Users)
    token: str = pw.CharField(255, unique=True)
    expires_on: datetime = pw.DateTimeField()

    def __str__(self) -> str:
        return self.token

    @classmethod
    def new(cls, for_user, term=timedelta(minutes=30)):
        '''Создает новый случайны токен для юзера'''
        return cls.create(
            user=for_user,
            token=Tokens._generate_token(),
            expires_on=datetime.now() + term
        )

    def is_expired(self):
        '''Проверяет, истек ли токен'''
        return datetime.now() > self.expires_on

    @staticmethod
    def _generate_token():
        t = str(uuid4())
        while Tokens.get_or_none(token=t):
            t = str(uuid4())
        return t


class MeasurementRegions(BaseModel):
    '''
    Регионы, для которых собираются измерения.

    Fields:
        region_index: str - индекс региона (как на сайте)
        region_name:  str - название региона
    '''
    region_index: str = pw.CharField(255, primary_key=True)
    region_name: str = pw.CharField(255, null=True)


class AtmosphericMeasurements(BaseModel):
    '''
    Измерения.

    Fields:
        id:     int                - pk
        date:   date               - дата сбора показателей
        region: MeasurementRegions - регион сбора показателей
        co:     float              - CO
        no:     float              - NO
        no2:    float              - NO2
        sc2:    float              - SO2
        h2s:    float              - H2S
        o3:     float              - O3
        nh3:    float              - NH3
        ch4:    float              - CH4
        σch:    float              - ΣCH
        pm25:   float              - PM2.5
        pm10:   float              - PM10
    '''
    date: date_t = pw.DateField()
    region: MeasurementRegions = pw.ForeignKeyField(
        MeasurementRegions, 'region_index')
    co = pw.FloatField(null=True, verbose_name='CO')
    no = pw.FloatField(null=True, verbose_name='NO')
    no2 = pw.FloatField(null=True, verbose_name='NO2')
    so2 = pw.FloatField(null=True, verbose_name='SO2')
    h2s = pw.FloatField(null=True, verbose_name='H2S')
    o3 = pw.FloatField(null=True, verbose_name='O3')
    nh3 = pw.FloatField(null=True, verbose_name='NH3')
    ch4 = pw.FloatField(null=True, verbose_name='CH4')
    σch = pw.FloatField(null=True, verbose_name='ΣCH')
    pm25 = pw.FloatField(null=True, verbose_name='PM2.5')
    pm10 = pw.FloatField(null=True, verbose_name='PM10')

    @staticmethod
    def select_by_timerange(start, end, region=None):
        if not region:
            return AtmosphericMeasurements\
                .select()\
                .where(AtmosphericMeasurements.date.between(start, end))\
                .order_by(AtmosphericMeasurements.date)
        else:
            return AtmosphericMeasurements\
                .select()\
                .where(
                    (AtmosphericMeasurements.date.between(start, end)) &
                    (AtmosphericMeasurements.region == region))\
                .order_by(AtmosphericMeasurements.date)

    @staticmethod
    def min_date():
        return AtmosphericMeasurements\
            .select(fn.MIN(AtmosphericMeasurements.date))\
            .scalar()

    @staticmethod
    def max_date():
        return AtmosphericMeasurements\
            .select(fn.MAX(AtmosphericMeasurements.date))\
            .scalar()


def mk_database():
    db.create_tables([
        Users, Tokens, MeasurementRegions, AtmosphericMeasurements
    ])
