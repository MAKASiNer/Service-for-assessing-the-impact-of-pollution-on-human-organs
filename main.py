import argparse
from datetime import date
from web import app
from myparser import load_data


def main():
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=lambda x: app.run())
    subparsers = parser.add_subparsers()

    parser_migrate = subparsers.add_parser('migrate', help='Создает бд')
    parser_migrate.set_defaults(func=lambda args: __import__('web.models'))

    parser_load = subparsers.add_parser('load', help='Загружает данные с сайта росгидромета')
    parser_load.set_defaults(func=lambda args: load_data(args.start, args.end, _preload_regions=True))
    parser_load.add_argument('start', type=date.fromisoformat, help='Дата начала')
    parser_load.add_argument('end', type=date.fromisoformat, nargs='?', help='Дата конца')

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
