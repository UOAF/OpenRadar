import sys

from app import App

if __name__ == '__main__':

    theApp = App(sys.argv)
    theApp.on_execute()