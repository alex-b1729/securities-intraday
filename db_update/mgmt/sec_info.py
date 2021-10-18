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

Updates table security_info with newest IEX supported symbols and returns a
dictionary of active symbols in form {'symbol': security_id}
"""

# project packages
import references
import speedydb

# python packages
import requests
from urllib import parse
import pandas as pd
import datetime
from time import sleep
import json
import psycopg2

def json_int_clean(json_elmnt):
    """return integer if json element is not none, otherwise return -1"""
    if json_elmnt:
        ret = int(json_elmnt)
    else:
        ret = -1
    return ret

def get_iex_symbols():
    "Returns list of symbols supported by iex for api calls, or `None` if api error."
    sym_url = 'stable/ref-data/symbols'
    url = parse.urljoin(references.base_iex_url, sym_url)
    payload = {'token': references.keys.token}
    response = requests.get(url, params=payload)
    syms = []
    exchs = []
    names = []
    dates = []
    types = []
    iexids = []
    regions = []
    currencies = []
    isenableds = []
    figis = []
    ciks = []
    symbols = None
    success = False
    retry = True
    while not success:
        # if the request was good
        if response.status_code == requests.codes.ok:
            success = True
            # parse json into dataframe
            json_obj = response.json()
            for line in json_obj:
                tp = line['type']
                if tp in references.symbol_types_for_use:
                    syms.append(line['symbol'])
                    exchs.append(line['exchange'])
                    names.append(line['name'])
                    dates.append(datetime.datetime.strptime(line['date'], "%Y-%m-%d"))
                    types.append(tp)
                    iexids.append(line['iexId'])
                    regions.append(line['region'])
                    currencies.append(line['currency'])
                    isenableds.append(bool(line['isEnabled']))
                    figis.append(line['figi'])
                    ciks.append(json_int_clean(line['cik']))
            symbols = pd.DataFrame({'iex_symbol':syms, 'exchange':exchs, 'comp_name':names,
                                    'date_added':dates, 'security_type':types,
                                    'iex_id':iexids, 'region':regions, 'currency':currencies,
                                    'is_enabled':isenableds, 'figi':figis, 'cik':ciks})
        # if the request failed due to a server error the first time
        elif response.status_code == requests.codes.server_error and retry:
            retry = False
            sleep(2)
            response = requests.get(url, params=payload)
        # failed twice due to server error
        else:
            success = True

    return symbols

def get_db_symbols(cur):
    """selects data for enabled database symbols, sorted by iex_id, and returns pd.DataFrame"""
    cur.execute('''SELECT
                        security_id,
                        symbol -> 'current',
                        iex_id
                   FROM security_info
                   WHERE is_enabled
                   ORDER BY iex_id ASC;''')
    # parse symbols
    sec_id = []
    enbl_syms = []
    iex_ids = []
    # for each returned line
    for ticker in cur:
        sec_id.append(int(ticker[0]))
        enbl_syms.append(ticker[1])
        iex_ids.append(ticker[2])
    return pd.DataFrame({'sec_id': sec_id, 'tbl_symbol': enbl_syms, 'iex_id': iex_ids})

def update(conn, cur):
    """Updates symbols in table security_info"""
    # get IEX supported symbols
    iex_symbols = get_iex_symbols()
    # get symbols in table security_info
    tbl_symbols = get_db_symbols(cur)

    # merge on unique iex_id
    symbols = iex_symbols.merge(tbl_symbols, how='outer', on='iex_id', indicator=True)

    # securities with a symbol change
    sym_chgs = symbols[symbols['_merge']=='both'][symbols.iex_symbol != symbols.tbl_symbol][['sec_id', 'iex_symbol']]
    if not sym_chgs.empty:
        for line in sym_chgs.itertuples():
            speedydb.update_syms(line.sec_id, line.iex_symbol, cur)

    # new securities
    new_syms = symbols[symbols['_merge']=='left_only']
    if not new_syms.empty:
        syms_to_add = list(zip(new_syms.iex_symbol.apply(lambda x: json.dumps({'current': x})),
                               new_syms.exchange, new_syms.comp_name, new_syms.date_added,
                               new_syms.security_type, new_syms.iex_id, new_syms.region,
                               new_syms.currency, new_syms.is_enabled, new_syms.figi,
                               new_syms.cik))
        # dictionary matching trading symbol with security_id
        security_dict = speedydb.insert_new_syms(syms_to_add, cur)
    else:
        security_dict = {}

    # depreciated symbols
    dep_syms = symbols[symbols['_merge']=='right_only']
    if not dep_syms.empty:
        speedydb.depreciate_syms(dep_syms.security_id.tolist(), cur)

    # remaining symbols already up to date
    uptodate_syms = symbols[symbols['_merge']=='both'][symbols.iex_symbol == symbols.tbl_symbol][['iex_symbol', 'sec_id']]
    if not uptodate_syms.empty:
        for line in uptodate_syms.itertuples():
            security_dict[line.iex_symbol] = int(line.sec_id)

    conn.commit()

    # return dictionary of {'symbol': security_id}
    return security_dict
