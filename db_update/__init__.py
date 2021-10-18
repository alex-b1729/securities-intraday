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

"""

import intraday_update
import references

import datetime
import logging

def main():
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    # if trading day yesterday
    if references.yesterday_was_trading_day():
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        # update database with yesterday's prices
        intraday_cron.save_price_data(yesterday)

if __name__ == "__main__":
    main()
