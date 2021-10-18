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

Updates security_data and saves min data from yesterday
"""

# project modules
import mgmt.sec_info
import priceseries
import references
import speedydb

# other modules
import psycopg2
import datetime
import os

def save_price_data(date):
    """Save intra-day data from IEX to Postgres database."""
    # connect to postgres
    conn = psycopg2.connect(references.conn_string)
    # will close psql connection and cursor if un-handeled exception is raised
    try:
        with conn.cursor() as cur:
            # update security_info table and get dictionary of {'trading symbol': security_id}
            sec_dict = mgmt.sec_info.update(conn, cur)
            # separate trading symbols into groups of 100 for api calls
            sym_groups = mgmt.api_symbol_groups(sec_dict)
            # yesterday's date formatted as yyyymmdd
            api_dt = ''.join(str(date).split('-'))
            # for each 100 symbols
            for sym_grp in sym_groups:
                # get bulk url
                bulk_url = references.intraday_url_endpoint(api_dt, sym_grp)
                # itterator object for each line of aggregated data
                daily_data = priceseries.iter_intraday_api(bulk_url, sec_dict)
                # insert into postres using copy_from
                speedydb.iter_copy_from(daily_data, cur)
            # commit changes to db
            conn.commit()
    # close postgres connection regardless of errors etc
    finally:
        conn.close()
