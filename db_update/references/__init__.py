#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2021 Alexander Brefeld
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
@author: abrefeld
Alexander Brefeld
alexander.brefeld@protonmail.com

Includes constants and helper functions for use throughout code
"""

from . import keys
import urllib.parse
import datetime
import requests
import os

# postgres connection info
dbname = 'security_data'
conn_string = "{1} dbname={2} password={3}".format(os.environ['POSTGRESCONN'], dbname, keys.psqlpw)

# IEX vars
base_iex_url = "https://cloud.iexapis.com/"
intraday_ret_vars = ['date','minute','marketOpen','marketHigh','marketLow',
                   'marketClose','marketVolume','marketNotional',
                   'marketNumberOfTrades']

def intraday_url_endpoint(date, syms):
    """Returns formatted url for IEX intra-day stock price API."""
    payload = {'types':'intraday-prices', 'symbols':','.join(syms),
               'filter':','.join(intraday_ret_vars),'token':keys.token}
    bulk_url = urllib.parse.urljoin(base_iex_url, 'stable/stock/market/batch/date/' + date)
    return bulk_url + '?' + urllib.parse.urlencode(payload, safe=',')

def yesterday_was_trading_day():
    """Returns True if yesterday was a trading day."""
    trading_day = False
    trade_url = urllib.parse.urljoin(base_iex_url, 'stable/ref-data/us/dates/trade/last')
    payload = {'token':keys.token}
    response = requests.get(trade_url, params=payload)
    if response.status_code == requests.codes.ok:
        yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
        days = response.json()
        last_trade = days[0]['date']
        if last_trade == yesterday:
            trading_day = True
    return trading_day


# general data variables
symbol_types_for_use = {'cs', 'cef', 'oef', 'ps', 'et'}
