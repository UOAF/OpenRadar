import sys

from app import App

def main():
    theApp = App(sys.argv)
    theApp.on_execute()

if __name__ == '__main__':
    main()