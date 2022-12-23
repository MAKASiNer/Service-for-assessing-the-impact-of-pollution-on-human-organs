# Web-сервер сервиса Air quality
Необходим python => 3.9

## Установка библиотек
Список всех библиотек в requirements.txt
```
cd <папка проекта>
pip install -r requirements.txt
```

## Регистрация почтового ящика
У яндекс-почты есть [инструкция](https://yandex.ru/support/mail/mail-clients/others.html) для настройки почтового ящика.
Нас интересует настройка протокола SMTP.
Параметры такие:
- MAIL_SERVER = адрес почтового сервера (smtp.yandex.ru)
- MAIL_PORT = порт (465)
- MAIL_USE_TLS = False
- MAIL_USE_SSL = True
- MAIL_USERNAME = просто почта
- MAIL_PASSWORD = специальный пароль "для приложений"
- MAIL_DEFAULT_SENDER = еще раз просто почта

## Настройка базы данных  
Для начала необходимо установить соответсвующий драйвер для бд!!!
Для MySQL ``` pip install pymysql ``` или ```pip install pysqlite3``` для SQLitre.
Параметры такие:
- DB_DBMS = название драйвера (sqlite, mysql, postgresql)
- DB_NAME = 'database.db'
- DB_USER = None
- DB_PASSWORD = None
- DB_HOST = None
- DB_PORT = None
    
## Запуск
Для тестового сервера просто запустить main файл
```
python main.py
```
