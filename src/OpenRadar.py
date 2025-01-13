import sys
import argparse
import os

from app import App


def main():
    theApp = App(sys.argv)
    parser = argparse.ArgumentParser(prog='OpenRadar', description='TacView realtime telemetry radar tool')

    # set up some
    test_ini_path = os.path.join(os.getcwd(), 'Data', 'test.ini')

    parser.add_argument('-i', '--ini', nargs='?', const=test_ini_path, default=None, help='Load a test ini file.')

    args = parser.parse_args()

    theApp.on_execute(args)


if __name__ == '__main__':
    main()
