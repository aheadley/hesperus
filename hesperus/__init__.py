if __name__ == '__main__':
    from core import Core
    from plugin import Plugin
    from plugins.irc import IRCPlugin
    import time, random, sys
    
    c = Core.load_from_file(sys.argv[1])
    try:
        c.start()
    except KeyboardInterrupt:
        c.stop()
        print "caught ^C, exiting..."
