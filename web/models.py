import numpy as np
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
        co:     float              - CO    [3]
        no:     float              - NO    [4]
        no2:    float              - NO2   [5]
        sc2:    float              - SO2   [6]
        h2s:    float              - H2S   [7]
        o3:     float              - O3    [8]
        nh3:    float              - NH3   [9]
        ch4:    float              - CH4   [10]
        σch:    float              - ΣCH   [11]
        pm25:   float              - PM2.5 [12]
        pm10:   float              - PM10  [13]
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
        '''Производит выборку по региону и дате. Сортирует во возрастанию даты'''
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

    @staticmethod
    def _recover_seq(a):
        '''
        Линейно восстанавливает последовательность.

        Пример:
            [None, None, None, 1, 2, None, None, 5, 6, None, None] =>
            [1, 1, 1, 1, 2, 3.5, 5, 5, 6, 6, 6]
        '''
        b = np.copy(a)
        j = None
        for i, p in enumerate(b):
            if p is not None:
                if j is None:
                    b[j: i] = np.ones(i) * p
                else:
                    b[j: i] = np.linspace(b[j], p, i - j)
                j = i

        if j is None:
            b = np.zeros(b.shape)
        else:
            b[j:] = np.ones(i - j + 1) * b[j]

        return b

    @staticmethod
    def C(start, end, region, days=1, indexes=None):
        '''
        Подсчитывает С - среднее арифмметическое по соседям слева и справа 

        Args:
            start:   date               - дата начала выборки (включительно)
            end:     date               - дата конца выборки (включительно)
            region:  str                - регион, для которого брать измерения
            days:    int                - длина выборки для среднего (по скольки дням будет считатся среднее арифметичекое)
            indexes: str|list[str]|None - элемент или элементы ('CO', 'NO', 'NO2', 'SO2', 'H2S', 'O3', 'NH3', 'CH4', 'ΣCH', 'PM2.5', 'PM10')

        Returns:
            NDArray NxM, где N = len(indexes), M = end - start
        '''
        t1 = end + timedelta(days=days // 2)
        t0 = start - timedelta(days=days // 2)

        measures = np.asarray(
            AtmosphericMeasurements.select_by_timerange(t0, t1, region)
            .tuples()
        )[:, 3:14].T

        if indexes is None:
            indexes = ['CO', 'NO', 'NO2', 'SO2', 'H2S', 'O3',
                       'NH3', 'CH4', 'ΣCH', 'PM2.5', 'PM10']

        def extract_index(v):
            return {'CO': 0, 'NO': 1, 'NO2': 2, 'SO2': 3, 'H2S': 4, 'O3': 5, 'NH3': 6, 'CH4': 7, 'ΣCH': 8, 'PM2.5': 9, 'PM10': 10}.get(v)

        m = []
        if isinstance(indexes, str):
            if (i := extract_index(index)) is not None:
                m.append(measures[i])
        elif hasattr(indexes, '__iter__'):
            for index in indexes:
                if (i := extract_index(index)) is not None:
                    m.append(measures[i])
        else:
            raise TypeError('unexpected indexes type %s' % type(indexes))

        return np.apply_along_axis(
            lambda x: np.convolve(x, np.ones(days) / days, mode='valid'),
            axis=1,
            arr=np.apply_along_axis(
                AtmosphericMeasurements._recover_seq,
                axis=1,
                arr=m
            )
        )

    @staticmethod
    def HI(start, end, region, days, indexes, rfc_list):
        c = AtmosphericMeasurements.C(start, end, region, days, indexes)
        rfc = iter(rfc_list)
        hq = np.apply_along_axis(
            lambda c: np.divide(c, next(rfc)),
            axis=1,
            arr=c
        )
        hi = np.sum(hq, axis=0)
        return hi

    @staticmethod
    def HI_1(start, end, region):
        return AtmosphericMeasurements.HI(
            start=start,
            end=end,
            region=region,
            days=1,
            indexes=[
                'CO', 'NO', 'NO2', 'SO2', 'H2S', 'O3', 'NH3', 'PM2.5', 'PM10'
            ],
            rfc_list=[
                23, 0.72, 0.47, 0.66, 0.1, 0.18, 0.35, 0.15, 0.065
            ]
        )

    @staticmethod
    def HI_365(start, end, region):
        return AtmosphericMeasurements.HI(
            start=start,
            end=end,
            region=region,
            days=365,
            indexes=[
                'CO', 'NO', 'NO2', 'SO2', 'H2S', 'O3', 'NH3', 'PM2.5', 'PM10'
            ],
            rfc_list=[
                3, 0.06, 0.04, 0.05, 0.002, 0.03, 0.1, 0.05, 0.015
            ]
        )

    @staticmethod
    def prod(start, end, region, indexes, pdk_list, hazard_list):

        def a(hazard):
            return {1: 9.15, 2: 5.51, 3: 2.35, 4: 1.41}[hazard]

        def b(hazard):
            return {1: 11.66, 2: 7.49, 3: 3.73, 4: 2.33}[hazard]

        def prod(c, pdk, hazard):
            return np.log10(c / pdk) * b(hazard) - a(hazard)

        c = AtmosphericMeasurements.C(
            start=start,
            end=end,
            region=region,
            days=1,
            indexes=indexes
        )

        pdk = iter(pdk_list)
        hazard = iter(hazard_list)
        return np.apply_along_axis(
            lambda c: prod(c.astype(float), next(pdk), next(hazard)),
            axis=1,
            arr=c
        )

    @staticmethod
    def risk(start,
             end,
             region,
             indexes=['CO', 'NO', 'NO2', 'SO2', 'H2S', 'O3', 'NH3'],
             pdk_list=[5, 0.4, 0.2, 0.5, 0.008, 0.16, 0.2],
             hazard_list=[4, 3, 3, 3, 2, 1, 4]):

        table = (
                (-3.0, 0.001), (-2.5, 0.006), (-2.0, 0.023), (-1.9, 0.029),
                (-1.8, 0.036), (-1.7, 0.045), (-1.6, 0.055), (-1.5, 0.067),
                (-1.4, 0.081), (-1.3, 0.097), (-1.2, 0.115), (-1.1, 0.136),
                (-1.0, 0.157), (-0.9, 0.184), (-0.8, 0.212), (-0.7, 0.242),
                (-0.6, 0.274), (-0.5, 0.309), (-0.4, 0.345), (-0.3, 0.382),
                (-0.2, 0.421), (-0.1, 0.460), (0.0, 0.500), (0.1, 0.540),
                (0.2, 0.579), (0.3, 0.618), (0.4, 0.655), (0.5, 0.692),
                (0.6, 0.726), (0.7, 0.758), (0.8, 0.788), (0.9, 0.816),
                (1.0, 0.841), (1.1, 0.864), (1.2, 0.885), (1.3, 0.903),
                (1.4, 0.919), (1.5, 0.933), (1.6, 0.945), (1.7, 0.955),
                (1.8, 0.964), (1.9, 0.971), (2.0, 0.977), (2.5, 0.994),
                (3.0, 0.999))

        def scalar_risk(prod):
            for a, b in table:
                if prod <= a:
                    return b
            return 1.0

        return np.vectorize(scalar_risk)(
            AtmosphericMeasurements.prod(start, end, region, indexes, pdk_list, hazard_list))


def mk_database():
    db.create_tables([
        Users, Tokens, MeasurementRegions, AtmosphericMeasurements
    ])
