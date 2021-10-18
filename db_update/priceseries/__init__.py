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

Functions to help with handeling timeseries price data.
"""

import pandas as pd
import datetime
import json
import requests

def aggregate(price_json, sec_id, interval='98min'):
    """Generates pd.DataFrame and can aggregate 390 minutes of data up to interval
    (currently supports 98 minutes) and returns json"""
    dt = []
    for minute_data in price_json:
        datestring = "{} {}".format(minute_data['date'], minute_data['minute'])
        time_index = datetime.datetime.strptime(datestring, "%Y-%m-%d %H:%M")
        dt.append(str(time_index))
    ts = pd.DataFrame.from_records(price_json, exclude=['date','minute'])
    ts['datetime'] = dt
    # following can be used to aggregate from minute level to higher level
    '''
    ts['gb'] = [0]*98 + [1]*97 + [2]*98 + [3]*(len(ts.index) - 293)
    aggts = ts.groupby('gb').agg({'datetime':'last','marketOpen':'first',
                                  'marketHigh':'max','marketLow':'min',
                                  'marketClose':'last','marketVolume':'sum',
                                  'marketNotional':'sum',
                                  'marketNumberOfTrades':'sum'})
    aggts['security_id'] = [sec_id] * 4
    '''
    ts['security_id'] = [sec_id] * 390
    return json.loads(ts.to_json(orient='records', double_precision=3,
                                       date_format='epoch'))

def iter_intraday_api(url, sec_dict):
    """Yields next line of aggregated intraday minute data"""
    response = requests.get(url)
    if response.status_code == requests.codes.ok:
        json_obj = response.json()
        for ticker in json_obj:
            try:
                sec_id = sec_dict[ticker]
            except:
                # not certian if anything would trip this...
                pass
            else:
                intraday_prices = json_obj[ticker]['intraday-prices']
                if intraday_prices:
                    agg_prices = aggregate(intraday_prices, sec_id)
                    for data_line in agg_prices:
                        yield data_line
