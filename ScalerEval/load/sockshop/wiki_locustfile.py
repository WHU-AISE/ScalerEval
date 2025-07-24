import base64
import uuid
import os
from random import randint, choice
import random
from locust import HttpLocust, HttpUser, LoadTestShape, TaskSet, between, task
import numpy as np
import pandas as pd


def get_base64(username, password):
    string = "%s:%s" % (username, password)
    string = string.encode()
    base64string = base64.b64encode(string)
    return base64string


items = [
    # '03fef6ac-1896-4ce8-bd69-b798f85c6e0b',
    '3395a43e-2d88-40de-b95f-e00e1502085b',
    '510a0d7e-8e83-4193-b483-e27e09ddc34d',
    '808a2de1-1aaa-4c25-a9b9-6612e8f29a38',
    '819e1fbf-8b7e-4f6d-811f-693534916a8b',
    '837ab141-399e-4c1f-9abc-bace40296bac',
    'a0a4f044-b040-410d-8ead-4de0446aec7e',
    'd3588630-ad8e-49df-bbd7-3167f7efb246',
    'zzz4f044-b040-410d-8ead-4de0446aec7e'
]

def index(l):
    l.client.get("/")

def catagory(l):
    l.client.get("/category.html")

def detail(l):
    item_id = random.choice(items)
    l.client.get("/detail.html?id={}".format(item_id))

def login(l):
    auth_header = get_base64("user", "password").decode()
    l.client.get("/login", headers={"Authorization":"Basic %s" % auth_header})

def view_cart(l):
    l.client.get("/basket.html")

def add_cart(l):
    item_id = random.choice(items)
    l.client.post("/cart", json={"id": item_id, "quantity": 1}) 

def delete_cart(l):
    l.client.delete("/cart")

def update_shipping_payment(l):
    l.client.post("/addresses", json={
        "city": "wuhan",
        "country": "China",
        "number": "61",
        "postcode": "12345",
        "street": "wuluo street"
    })
    l.client.post("/cards", json={
        "ccv": "12345",
        "expires": "12/99",
        "longNum": "1231414125"
    })


def order(l):
    auth_header = get_base64("user", "password").decode()

    # catalogue = l.client.get("/catalogue").json()
    item_id = choice(items)
    # item_id = '03fef6ac-1896-4ce8-bd69-b798f85c6e0b'

    l.client.get("/login", headers={"Authorization":"Basic %s" % auth_header})
    l.client.post("/cart", json={"id": item_id, "quantity": 1})
    l.client.post("/orders")
    l.client.delete("/cart")
    # auth_header = get_base64("user", "password").decode()
    # l.client.get("/login", headers={"Authorization":"Basic %s" % auth_header})
    
    # order_id = str(uuid.uuid4()).replace('-','')[:24]
    # order_data = {
    #         "id": order_id,
    #         "customerId": "57a98d98e4b00679b4a830b2",
    #         "address": {
    #             "id": None,
    #             "number": "246",
    #             "street": "Whitelees Road",
    #             "city": "Glasgow",
    #             "postcode": "G67 3DL",
    #             "country": "UK"
    #         },
    #         "card": {
    #             "id": None,
    #             "longNum": "5544154011345918",
    #             "expires": "08/19",
    #             "ccv": "958"
    #         },
    #         "customer": {
    #             "id": None,
    #             "firstName": "User",
    #             "lastName": "Name",
    #             "username": "user",
    #             "addresses": [],
    #             "cards": []
    #         },
    #         "date": "2024-11-26T03:41:15.866+0000",
    #         "items": [
    #             {
    #                 "id": "67454355de06490007658180",
    #                 "itemId": "3395a43e-2d88-40de-b95f-e00e1502085b",
    #                 "quantity": 1,
    #                 "unitPrice": 18
    #             }
    #         ],
    #         "shipment": {
    #             "id": "61c347cd-d1df-4af6-b46f-67412b821f7f",
    #             "name": "57a98d98e4b00679b4a830b2"
    #         },
    #         "total": 22.99
    #     }
    # l.client.post("/orders", json=order_data)

def flow(l):
    auth_header = get_base64("user", "password").decode()

    # catalogue = l.client.get("/catalogue").json()
    item_id = choice(items)
    # item_id = '03fef6ac-1896-4ce8-bd69-b798f85c6e0b'

    l.client.get("/login", headers={"Authorization":"Basic %s" % auth_header})
    l.client.get("/category.html")
    l.client.get("/detail.html?id={}".format(item_id))
    # l.client.delete("/cart")
    l.client.post("/cart", json={"id": item_id, "quantity": 1})
    l.client.get("/basket.html")
    l.client.post("/orders")
    l.client.delete("/cart")

    
class UserBehavior(TaskSet):

    def on_start(self):
        index(self)

    dist = os.getenv('load_dist', '1')
    tasks = {flow: 1}
    # if dist == '1':
    #     tasks = {index: 1,
    #         catagory: 2,
    #         detail: 10,
    #         login: 1,
    #         view_cart: 1,
    #         add_cart: 1,
    #         delete_cart: 1,
    #         update_shipping_payment: 1,
    #         order: 1}
    # elif dist == '2':
    #     tasks = {index: 1,
    #         catagory: 1,
    #         detail: 1,
    #         login: 4,
    #         view_cart: 10,
    #         add_cart: 3,
    #         delete_cart: 1,
    #         update_shipping_payment: 5,
    #         order: 5}
        
class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 10)


class StagesShapeWithCustomUsers(LoadTestShape):
    wave_df = pd.read_csv('load/sockshop/wiki.csv')
    wave_list = wave_df['count'].tolist()
    scale_factor = 0.2
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