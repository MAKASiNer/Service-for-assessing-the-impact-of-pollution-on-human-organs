import sys


def main():
    sys.path.append('./feerc')
    from web import app
    app.run()


if __name__ == '__main__':
    main()
