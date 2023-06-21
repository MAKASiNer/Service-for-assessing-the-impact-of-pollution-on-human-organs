import numpy as np
import peewee as pw
from peewee import fn
from uuid import uuid4
from datetime import datetime, timedelta, date
from config import DB_DBMS, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


ACUTE_W = 1
CHRONIC_W = 365


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

    @classmethod
    def all(cls):
        return cls.select()


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


class HazardClass(BaseModel):
    '''
    Класс опасности

    Fields:
        id: int   - pk
        a:  float - b0 коэффициент формулы prod
        b   float - b1 коэффициент формулы prod
    '''
    a = pw.FloatField()
    b = pw.FloatField()


class Substance(BaseModel):
    '''
    Класс вещества

    Fields:
        id:           int         - pk 
        name:         str         - название вещества
        formula:      str         - химическая формула (type)
        hazard_class: HazardClass - класс опасности вещества
        daily_pdk:    float       - среднедневное пдк
        yearly_pdk:   float       - среднегодовое пдк
        chronic_rfc:  float       - хроническая референтная концентрация
        acute_rfc:    float       - острая референтная концентрация
    '''
    name = pw.CharField(100, unique=True)
    formula = pw.CharField(20, unique=True)
    hazard_class = pw.ForeignKeyField(HazardClass, null=True)
    daily_pdk = pw.FloatField()
    yearly_pdk = pw.FloatField()
    chronic_rfc = pw.FloatField()
    acute_rfc = pw.FloatField()

    def __str__(self):
        return self.formula


class ReferenceConcentration(BaseModel):
    '''
    Референтная концентрация вещества

    Fields:
        id:        int       - pk
        substance: Substance - вещество 
        chronic:   float     - хроническое пдк
        acute:     float     - острое пдк
    '''
    substance = pw.ForeignKeyField(Substance, unique=True)
    chronic = pw.FloatField()
    acute = pw.FloatField()


class MeasurementRegion(BaseModel):
    '''
    Регионы измерения

    Fields:
        id:       int   - pk
        name:     str   - название региона
        address:  str   - полный адресс 
        lat:      flaot - широта
        lng:      float - долгота
        postcode: int   - почтовый индекс 
    '''
    name = pw.CharField(255, unique=True)
    address = pw.TextField(unique=True)
    lat = pw.FloatField()
    lng = pw.FloatField()
    postcode = pw.IntegerField(null=True)


class DataSource(BaseModel):
    '''
    Источники данных

    Fields:
        id:      int - pk
        name:    str - название источника
        address: str - адрес источника
    '''
    name = pw.CharField(255, unique=True)
    address = pw.CharField(255, unique=True)


class AtmosphericMeasurement(BaseModel):
    '''
    Измерения

    Fields:
        id:        int               - pk
        date:      date              - дата измерения
        substance: Substance         - вещество
        region:    MeasurementRegion - регион
        source:    DataSource        - источник данных
        stat:      flaot             - показание измерения
    '''
    date = pw.DateField()
    substance = pw.ForeignKeyField(Substance)
    region = pw.ForeignKeyField(MeasurementRegion)
    source = pw.ForeignKeyField(DataSource)
    stat = pw.FloatField(null=True)

    class Meta:
        indexes = (
            (('date', 'substance_id', 'region_id'), True),
        )

    @property
    def x(self):
        return self.data

    def y(self):
        return self.stat
    
    @classmethod
    def min_date(cls, w=CHRONIC_W):
        if not w:
            w = 0
        return cls.select(fn.MIN(cls.date)).scalar() + timedelta(days=w)

    @classmethod
    def max_date(cls):
        a = cls.select(fn.MAX(cls.date)).scalar()
        b = datetime.now().date()
        return min(a, b)
    
    @staticmethod
    def validate_substances(substances=None):
        if substances is None:
            substances = list(Substance.all())
        elif not hasattr(substances, '__iter__'):
            substances = [substances, ]
        return substances
    
    @staticmethod
    def validate_regions(regions=None):
        if regions is None:
            regions = list(MeasurementRegion.all())
        elif not hasattr(regions, '__iter__'):
            regions = [regions, ]
        return regions

    @classmethod
    def C(cls, start, end, substances=None, regions=None, w=None):
        '''
        Скользящее среднее измерений

        Args:
            start:      datetime|str                              - дата начала
            end:        datetime|str                              - дата конца 
            substances: Substance|list[Substance]                 - вещества (по умолчанию все)
            regions:    MeasurementRegion|list[MeasurementRegion] - регионы (по умолчанию все)
            w:          int                                       - длина окна (по умолчанию 1)

        Returns:
            np.ndarray[регион][вещество][измерение][дата/показание]
        '''
        if not w:
            w = 1

        if isinstance(start, str):
            start = date.fromisoformat(start)
        
        if isinstance(end, str):
            end = date.fromisoformat(end)

        # левая дата выборки с учетом длины выборки
        wstart = start - timedelta(days=w)
        # даты дней в выборке. нужно для создания маски (массив X есть массив дат)
        x = np.asarray([wstart + timedelta(days=i) for i in range((end-wstart).days + 1)])
        # переменная под показания
        c = []
        # проходимся по каждому региону
        for region in cls.validate_regions(regions):
            c.append([])
            # проходимся по каждому веществу
            for substance in cls.validate_substances(substances):
                c[-1].append([])
                
                # вытаскиваем из бд показания с конкретным регионом и вещество и датой в промежуткке между [wstart, end]
                q = np.asarray(
                    cls.
                    select(cls.date, cls.stat)
                    .where(
                        (cls.region == region) &
                        (cls.substance == substance) &
                        (cls.date.between(wstart, end)))
                    .order_by(cls.date)
                    .tuples()
                )

                # создаем пустой массив показаний то же длинны, что и X (массив Y есть массив показаний)
                y = np.zeros(len(x), dtype=object)

                # если выборка не пустая
                if q.size:
                    # берем непустые показания из выборки
                    data = q[np.nonzero(q[:, 1])]
                    # сопоставляем их по датам с массивом X (нужно создать ассоциацию дату и индекса - маску)
                    mask = np.isin(x, data[:, 0], assume_unique=False, invert=False)
                    # сопоставляем показания из выборки с массивом Y
                    y[np.nonzero(mask)] = data[:, 1]
                    # считаем скользящее среднее
                    _y = np.convolve(y, np.ones(w) / w, mode='valid')
                    y[y.size - _y.size:] = _y
                    # помещаем None в дни когда показаний нет 
                    y[np.nonzero(~mask)] = None

                # берем показания в промежутке [start, end]
                select = np.where((start <= x) & (x < end))
                # упаковываем их в пары дата+показание и помещаем в переменную
                c[-1][-1] = np.column_stack((x[select], y[select]))


        return np.asarray(c)

    @classmethod
    def HQ(cls, type, start, end, substances=None, regions=None):
        '''
        Коэффициент опасности

        Args:
            type:       str                                       - тип хронический или острый 'acute'/'chronic'
            start:      datetime|str                              - дата начала
            end:        datetime|str                              - дата конца 
            substances: Substance|list[Substance]                 - вещества (по умолчанию все)
            regions:    MeasurementRegion|list[MeasurementRegion] - регионы (по умолчанию все)

        Returns:
            np.ndarray[регион][вещество][измерение][дата/показание]
        '''
        substances = cls.validate_substances(substances)
        regions = cls.validate_regions(regions)
        
        # получаем нужно значение C
        if type == 'acute':
            c = cls.C(start, end, substances, regions, ACUTE_W)
            rfc = np.reshape([x.acute_rfc for x in substances], (1, -1, 1))
        elif type == 'chronic':
            c = cls.C(start, end, substances, regions, CHRONIC_W)
            rfc = np.reshape([x.chronic_rfc for x in substances], (1, -1, 1))
        else:
            raise ValueError('unexpected type, use "acute" or "chronic"')
        
        # делаем пустые значения нулями
        c[c == None] = 0.0
        # считаем по формуле HQ = C/ RfC (результат пишется в c чтобы не делать лишнюю копию масива)
        c[:, :, :, 1] = c[:, :, :, 1] / rfc

        return c

    @classmethod
    def HI(cls, type, start, end, substances=None, regions=None):
        '''
        Индекс опасности

        Args:
            type:       str                                       - тип хронический или острый 'acute'/'chronic'
            start:      datetime|str                              - дата начала
            end:        datetime|str                              - дата конца 
            substances: Substance|list[Substance]                 - вещества (по умолчанию все)
            regions:    MeasurementRegion|list[MeasurementRegion] - регионы (по умолчанию все)

        Returns:
            np.ndarray[регион][измерение][дата/показание]
        '''
        # получаем нужное значение HQ
        hq = cls.HQ(type, start, end, substances, regions)
        # считаем сумму вдоль показаний (вдоль оси показаний)
        sum = np.sum(hq[:, :, :, 1], axis=1)
        # избавляемся от оси веществ
        hi = np.stack([hq[:, 0, :, 0], sum], axis=2)
        return hi

    @classmethod
    def prob(cls, type, start, end, substances=None, regions=None):
        '''
        Величина связанная с риском

        Args:
            type:       str                                       - тип хронический или острый 'acute'/'chronic'
            start:      datetime|str                              - дата начала
            end:        datetime|str                              - дата конца 
            substances: Substance|list[Substance]                 - вещества (по умолчанию все)
            regions:    MeasurementRegion|list[MeasurementRegion] - регионы (по умолчанию все)

        Returns:
            np.ndarray[регион][вещество][измерение][величина]
        '''
        substances = cls.validate_substances(substances)
        regions = cls.validate_regions(regions)
        
        # получаем нужное значение C
        if type == 'acute':
            c = cls.C(start, end, substances, regions, ACUTE_W)
            pdk = np.reshape([x.daily_pdk for x in substances], (1, -1, 1))
        elif type == 'chronic':
            c = cls.C(start, end, substances, regions, CHRONIC_W)
            pdk = np.reshape([x.yearly_pdk for x in substances], (1, -1, 1))
        else:
            raise ValueError('unexpected type, use "acute" or "chronic"')
        
        # коэффициенты a и b (если индекс опасности для вещества не указан, то кф. одбираются такие чтобы вещество не оказало влияния на результат)
        a = np.reshape([x.hazard_class.a if x.hazard_class else -3 for x in substances],(1, -1, 1))
        b = np.reshape([x.hazard_class.b if x.hazard_class else 0 for x in substances],(1, -1, 1))
        # делаем пустые значения нулями
        c[c == None] = 0.0
        # считаем по формуле prob = a + b * ln(C/ПДК)
        c[:, :, :, 1] = a + b * np.log((c[:, :, :, 1] / pdk).astype(float))
        return c
    
    @classmethod
    def risk(cls, type, start, end, substances=None, regions=None):
        '''
        Риски

        Args:
            type:       str                                       - тип хронический или острый 'acute'/'chronic'
            start:      datetime|str                              - дата начала
            end:        datetime|str                              - дата конца 
            substances: Substance|list[Substance]                 - вещества (по умолчанию все)
            regions:    MeasurementRegion|list[MeasurementRegion] - регионы (по умолчанию все)

        Returns:
            np.ndarray[регион][вещество][измерение][риски]
        '''
        # не удалось найти уравнение функции распределения
        table = ((-3.0, 0.001), (-2.5, 0.006), (-2.0, 0.023), (-1.9, 0.029),
                 (-1.8, 0.036), (-1.7, 0.045), (-1.6, 0.055), (-1.5, 0.067),
                 (-1.4, 0.081), (-1.3, 0.097), (-1.2, 0.115), (-1.1, 0.136),
                 (-1.0, 0.157), (-0.9, 0.184), (-0.8, 0.212), (-0.7, 0.242),
                 (-0.6, 0.274), (-0.5, 0.309), (-0.4, 0.345), (-0.3, 0.382),
                 (-0.2, 0.421), (-0.1, 0.460), (0.0,  0.500),  (0.1, 0.540),
                 (0.2,  0.579), (0.3,  0.618), (0.4,  0.655),  (0.5, 0.692),
                 (0.6,  0.726), (0.7,  0.758), (0.8,  0.788),  (0.9, 0.816),
                 (1.0,  0.841), (1.1,  0.864), (1.2,  0.885),  (1.3, 0.903),
                 (1.4,  0.919), (1.5,  0.933), (1.6,  0.945),  (1.7, 0.955),
                 (1.8,  0.964), (1.9,  0.971), (2.0,  0.977),  (2.5, 0.994))
        
        # потому используем "таблицу значений функции"
        @np.vectorize
        def distribution(prob):
            if prob is None:
                return 0.0
            for a, b in table:
                if prob <= a:
                    return b
            return 1.0
        
        # применяем эту таблицу для каждого значения prob
        risk = cls.prob(type, start, end, substances, regions)
        risk[:,:,:,1] = distribution(risk[:,:,:,1])

        return risk


class HealthPoint(BaseModel):
    name = pw.CharField(255, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def possible_all(cls):
        q = (
            cls
            .select()
            .join(SubstancesInclusionInHealthPoints, pw.JOIN.LEFT_OUTER, on=(cls.id == SubstancesInclusionInHealthPoints.point_id))
            .where(SubstancesInclusionInHealthPoints.id.is_null(False))
            .distinct()
        )
        return q


class SubstancesInclusionInHealthPoints(BaseModel):
    point = pw.ForeignKeyField(HealthPoint)
    substance = pw.ForeignKeyField(Substance)
    
    @classmethod
    def all_for_health_point(cls, health_point):
        return cls.select().where(cls.point == health_point)


def mk_database():
    db.create_tables([
        Users,
        Tokens,
        HazardClass,
        Substance,
        ReferenceConcentration,
        MeasurementRegion,
        DataSource,
        AtmosphericMeasurement,
        HealthPoint,
        SubstancesInclusionInHealthPoints,
    ])

    _HC1 = HazardClass.get_or_create(id=1, a=-9.15, b=11.66)[0]
    _HC2 = HazardClass.get_or_create(id=2, a=-5.51, b=7.49)[0]
    _HC3 = HazardClass.get_or_create(id=3, a=-2.35, b=3.73)[0]
    _HC4 = HazardClass.get_or_create(id=4, a=-1.4, b=2.33)[0]

    s01 = Substance.get_or_create(hazard_class=_HC4, yearly_pdk=3.000, chronic_rfc=3.000, daily_pdk=5.000, acute_rfc=23.000, name='углерод', formula='CO')[0]
    s02 = Substance.get_or_create(hazard_class=_HC3, yearly_pdk=0.060, chronic_rfc=0.060, daily_pdk=0.400, acute_rfc=00.720, name='оксид азота', formula='NO')[0]
    s03 = Substance.get_or_create(hazard_class=_HC3, yearly_pdk=0.040, chronic_rfc=0.040, daily_pdk=0.200, acute_rfc=00.470, name='диоксид азота', formula='NO2')[0]
    # s04 = Substance.get_or_create(hazard_class=HC4, yearly_pdk=0, chronic_rfc=0, daily_pdk=0, acute_rfc=0, name='оксиды озота (NO и NO2)', formula='NOX')[0]
    s05 = Substance.get_or_create(hazard_class=_HC3, yearly_pdk=0.050, chronic_rfc=0.050, daily_pdk=0.050, acute_rfc=00.660, name='диоксид серы', formula='SO2')[0]
    s06 = Substance.get_or_create(hazard_class=_HC2, yearly_pdk=0.008, chronic_rfc=0.002, daily_pdk=0.008, acute_rfc=00.100, name='сероводород', formula='H2S')[0]
    s07 = Substance.get_or_create(hazard_class=_HC1, yearly_pdk=0.030, chronic_rfc=0.030, daily_pdk=0.160, acute_rfc=00.180, name='озон', formula='O3')[0]
    s08 = Substance.get_or_create(hazard_class=_HC4, yearly_pdk=0.040, chronic_rfc=0.100, daily_pdk=0.200, acute_rfc=00.350, name='аммиак', formula='NH3')[0]
    # s09 = Substance.get_or_create(hazard_class=HC4, yearly_pdk=0, chronic_rfc=0, daily_pdk=0, acute_rfc=0, name='сумма углеводородов (∑CH)', formula='HCH')[0]
    # s10 = Substance.get_or_create(hazard_class=HC4, yearly_pdk=0, chronic_rfc=0, daily_pdk=0, acute_rfc=0, name='метан', formula='CH4')[0]
    s11 = Substance.get_or_create(hazard_class=None, yearly_pdk=0.060, chronic_rfc=0.050, daily_pdk=0.300, acute_rfc=00.150, name='PM10', formula='PM10D')[0]
    s12 = Substance.get_or_create(hazard_class=None, yearly_pdk=0.035, chronic_rfc=0.015, daily_pdk=0.160, acute_rfc=00.065, name='PM2,5', formula='PM25D')[0]
    s13 = Substance.get_or_create(hazard_class=_HC3, yearly_pdk=0.150, chronic_rfc=0.075, daily_pdk=0.500, acute_rfc=00.300, name='PM1', formula='PM1')[0]

    p01 = HealthPoint.get_or_create(id=1, name='Дыхание')[0]
    p02 = HealthPoint.get_or_create(id=2, name='Кровообращение')[0]
    p03 = HealthPoint.get_or_create(id=3, name='ЦНС')[0]
    p04 = HealthPoint.get_or_create(id=4, name='Кроветворение')[0]
    p05 = HealthPoint.get_or_create(id=5, name='Смертность')[0]
    p06 = HealthPoint.get_or_create(id=6, name='Иммунитет')[0]
    p07 = HealthPoint.get_or_create(id=7, name='Рост и развитие')[0]
    p08 = HealthPoint.get_or_create(id=8, name='Зрение')[0]
    p09 = HealthPoint.get_or_create(id=9, name='Репродукция')[0]
    p10 = HealthPoint.get_or_create(id=10, name='Системное воздействие')[0]

    SubstancesInclusionInHealthPoints.get_or_create(point=p01, substance=s03)
    SubstancesInclusionInHealthPoints.get_or_create(point=p01, substance=s05)
    SubstancesInclusionInHealthPoints.get_or_create(point=p01, substance=s11)
    SubstancesInclusionInHealthPoints.get_or_create(point=p01, substance=s12)
    SubstancesInclusionInHealthPoints.get_or_create(point=p01, substance=s13)
    SubstancesInclusionInHealthPoints.get_or_create(point=p01, substance=s08)
    SubstancesInclusionInHealthPoints.get_or_create(point=p01, substance=s02)

    SubstancesInclusionInHealthPoints.get_or_create(point=p02, substance=s01)
    SubstancesInclusionInHealthPoints.get_or_create(point=p02, substance=s11)
    SubstancesInclusionInHealthPoints.get_or_create(point=p02, substance=s12)
    SubstancesInclusionInHealthPoints.get_or_create(point=p02, substance=s13)

    SubstancesInclusionInHealthPoints.get_or_create(point=p03, substance=s01)

    SubstancesInclusionInHealthPoints.get_or_create(point=p04, substance=s01)
    SubstancesInclusionInHealthPoints.get_or_create(point=p04, substance=s03)

    SubstancesInclusionInHealthPoints.get_or_create(point=p05, substance=s05)
    SubstancesInclusionInHealthPoints.get_or_create(point=p05, substance=s11)
    SubstancesInclusionInHealthPoints.get_or_create(point=p05, substance=s12)
    SubstancesInclusionInHealthPoints.get_or_create(point=p05, substance=s13)

    SubstancesInclusionInHealthPoints.get_or_create(point=p07, substance=s01)
    SubstancesInclusionInHealthPoints.get_or_create(point=p07, substance=s11)
    SubstancesInclusionInHealthPoints.get_or_create(point=p07, substance=s12)
    SubstancesInclusionInHealthPoints.get_or_create(point=p07, substance=s13)

    SubstancesInclusionInHealthPoints.get_or_create(point=p08, substance=s08)

    SubstancesInclusionInHealthPoints.get_or_create(point=p10, substance=s11)
    SubstancesInclusionInHealthPoints.get_or_create(point=p10, substance=s12)
    SubstancesInclusionInHealthPoints.get_or_create(point=p10, substance=s13)