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

Functions for (faster) PostgreSQL insert statements.
"""

from typing import Iterator, Dict, Any, Optional
import io
import json
import psycopg2
import psycopg2.extras
import datetime

class StringIteratorIO(io.TextIOBase):
    """source https://stackoverflow.com/questions/12593576/adapt-an-iterator-to-behave-like-a-file-like-object-in-python/12604375#12604375"""
    def __init__(self, iter: Iterator[str]):
        self._iter = iter
        self._buff = ''

    def readable(self) -> bool:
        return True

    def _read1(self, n: Optional[int] = None) -> str:
        while not self._buff:
            try:
                self._buff = next(self._iter)
            except StopIteration:
                break
        ret = self._buff[:n]
        self._buff = self._buff[len(ret):]
        return ret

    def read(self, n: Optional[int] = None) -> str:
        line = []
        if n is None or n < 0:
            while True:
                m = self._read1()
                if not m:
                    break
                line.append(m)
        else:
            while n > 0:
                m = self._read1(n)
                if not m:
                    break
                n -= len(m)
                line.append(m)
        return ''.join(line)

def clean_csv_value(value: Optional[Any]) -> str:
    """source https://hakibenita.com/fast-load-data-python-postgresql"""
    if value is None:
        return r'\N'
    return str(value).replace('\n', '\\n')

def insert_new_syms(data, cur):
    """Inserts data into security_info for new symbols and returns dict of {symbol: security_id}"""
    update_command = '''
        INSERT INTO security_info(
            symbol, exchange, comp_name, date_added,
            security_type, iex_id, region, currency,
            is_enabled, figi, cik)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING security_id, symbol -> 'current'
        ;
        '''
    for_close = {}
    for line in data:
        cur.execute(update_command, line)
        ret = cur.fetchone()
        for_close[ret[1]] = int(ret[0])
    return for_close

def update_syms(sec_id, new, cur):
    """Updates json entry for security symbol in table security_info"""
    # get json of previous symbols
    select_command = '''
                SELECT symbol
                FROM security_info
                WHERE security_id = %s;
                '''
    cur.execute(select_command, (sec_id,))
    prev_sym_dict = cur.fetchone()[0]
    last_sym = prev_sym_dict['current']
    prev_sym_dict['current'] = new
    prev_sym_dict[len(prev_sym_dict)-1] = last_sym
    tbl_json = json.dumps(prev_sym_dict)
    update_command = '''
                UPDATE security_info
                SET symbol = %s
                WHERE security_id = %s;
                '''
    cur.execute(update_command, (tbl_json, sec_id))

def depreciate_syms(sec_id_list, cur):
    tds = [str(datetime.date.today())] * len(sec_id_list)
    data = list(zip(tds, sec_id_list))
    update_command = '''
                    UPDATE security_info
                    SET date_depreciated = %s,
                        is_enabled = 'False'
                    WHERE
                        security_id = %s;
                    '''
    psycopg2.extras.execute_batch(cur, update_command, data)

def iter_copy_from(daily_data_iter, cur):
    """Inserts iterator object into postgres using psycopg.cursor.copy_from"""
    # csv like object to insert into postgres
    minute_string_iterator = StringIteratorIO((
        '|'.join(map(clean_csv_value, (
            minute['security_id'],
            minute['datetime'],
            minute['marketOpen'],
            minute['marketHigh'],
            minute['marketLow'],
            minute['marketClose'],
            int(minute['marketVolume']),
            minute['marketNotional'],
            int(minute['marketNumberOfTrades'])
            ))) + '\n'
            for minute in daily_data_iter
        ))
    cur.copy_from(minute_string_iterator, 'security_data', sep='|', size=8192)
