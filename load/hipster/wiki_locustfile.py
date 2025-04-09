#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import random

import numpy as np
from gevent import spawn
from locust import HttpUser, LoadTestShape, TaskSet, between, User
import pandas as pd
from psutil import users

products = [
    '0PUK6V6EV0',
    '1YMWWN1N4O',
    '2ZYFJ3GM2N',
    '66VCHSJNUP',
    '6E92ZMYYFZ',
    '9SIQT8TOJO',
    'L9ECAV7KIM',
    'LS4PSXUNUM',
    'OLJCESPC7Z']

def index(l):
    l.client.get("/")

def setCurrency(l):
    currencies = ['EUR', 'USD', 'JPY', 'CAD']
    l.client.post("/setCurrency",
        {'currency_code': random.choice(currencies)})

def browseProduct(l):
    l.client.get("/product/" + random.choice(products))

def viewCart(l):
    l.client.get("/cart")

def addToCart(l):
    product = random.choice(products)
    l.client.get("/product/" + product)
    l.client.post("/cart", {
        'product_id': product,
        'quantity': random.choice([1,2,3,4,5,10])})

def checkout(l):
    addToCart(l)
    l.client.post("/cart/checkout", {
        'email': 'someone@example.com',
        'street_address': '1600 Amphitheatre Parkway',
        'zip_code': '94043',
        'city': 'Mountain View',
        'state': 'CA',
        'country': 'United States',
        'credit_card_number': '4432-8015-6152-0454',
        'credit_card_expiration_month': '1',
        'credit_card_expiration_year': '2039',
        'credit_card_cvv': '672',
    })

class UserBehavior(TaskSet):

    def on_start(self):
        index(self)

    dist = os.getenv('load_dist', '1')
    if dist == '1':
        tasks = {index: 1,
            setCurrency: 2,
            browseProduct: 10,
            addToCart: 2,
            viewCart: 3,
            checkout: 1}
    elif dist == '2':
        tasks = {index: 5,
            setCurrency: 1,
            browseProduct: 1,
            addToCart: 5,
            viewCart: 5,
            checkout: 5}

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 10)


class StagesShapeWithCustomUsers(LoadTestShape):
    wave_df = pd.read_csv('load/hipster/wiki.csv')
    wave_list = wave_df['count'].tolist()
    scale_factor = 0.5
    time_limit, window_num = 20 * 60, 20
    window_size = time_limit / window_num
    stages = []
    for i in range(window_num):
        segm_len = int(len(wave_list)/ window_num)
        users = int(np.mean(wave_list[i*segm_len:(i+1)*segm_len]) * scale_factor)
        stages.append({"duration": int((i+1) * window_size), "users": users, "spawn_rate": 50})

    def tick(self):
        run_time = round(self.get_run_time())
        for stage in self.stages:
            if run_time <= stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        return None