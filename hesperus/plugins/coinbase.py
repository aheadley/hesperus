from ..plugin import CommandPlugin
from ..shorturl import short_url

import requests
import datetime
import random

API_VERSION_HEADER = {'CB-VERSION': '2017-12-01'}

class CoinPricePlugin(CommandPlugin):
    @CommandPlugin.config_types()
    def __init__(self, core):
        super(CoinPricePlugin, self).__init__(core)
        pass

    @CommandPlugin.register_command(r'(btc|eth|ltc|bch)(?:\s+(\w+))?')
    def price_command(self, chans, name, match, direct, reply):
        coin = match.group(1).upper()
        # HI ACHIN
        if coin == 'BTC' and random.random() < 0.05:
            reply('Current BTC price is https://youtu.be/yUPqZGQyBw8')
            return
        currency = 'USD'
        if match.group(2):
            currency = match.group(2).upper()
        yesterday_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        try:
            resp = requests.get('https://api.coinbase.com/v2/prices/{}-{}/spot'.format(
                coin, currency), headers=API_VERSION_HEADER).json()
            prev = requests.get('https://api.coinbase.com/v2/prices/{}-{}/spot?date={}'.format(
                coin, currency, yesterday_date), headers=API_VERSION_HEADER).json()
            prev = prev['data']['amount']
            msg = 'Current {} price is {} {}'.format(
                coin, resp['data']['amount'], resp['data']['currency'])
            if float(prev) > 1.0:
                if float(prev) < float(resp['data']['amount']):
                    dir = 'up'
                else:
                    dir = 'down'
                msg += ', {} from {} yesterday'.format(dir.upper(), prev)
            else:
                self.log_warning('Got zero price for yesterday from CB API')
            reply(msg)
        except Exception as err:
            self.log_warning(err)
            reply('I dunno, probably like a billion in your monopoly money')
