import datetime
from typing import Union
from fastapi import FastAPI,Form
import numpy as np
import hashlib
import socket
import time
import json
from requests import  request
from common import  Common as Common
from mysqlact import mysqlact as my
app = FastAPI()
np.random.seed(0)
md5 = hashlib.md5()

# @app.get("/")
# async def root():
#     return {"message": "Hello World"}
# #
# #
# @app.get("/hello/{name}")
# async def say_hello(name: str):
#     return {"message": f"Hello {name}"}
#
# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}


import requests
import json
from datetime import datetime, timedelta
from operator import itemgetter



@app.post("/feedback")
def  feedback(order_data: str = Form("order_data"),reason: str = Form("reason")):
    order_data = eval(order_data)
    order_d = order_data['order']
    order_time = order_data['order']['order_time']
    order_id = order_data['order']['order_id']
    insert_sql = 'insert into feedback(order_id,order_content,reason,order_time,feedback_time) VALUES(%s,%s,%s,%s,now())'
    insert_args = (order_id,str(order_data),str(reason),order_time)
    insert_run = my.insert(insert_sql,insert_args)
    if insert_run:
        r= 200
        message="Order "+str(order_id) +" Save Success"
    else:
        message = "Save Failed"
        r = 501


    return  {"message":message,"status": r}


TENCENT_MAP_API_KEY = 'L4HBZ-2VTWO-CTQWV-S3CAX-KFFEE-YAF56'
MAX_BATTERY = 100
MAX_DELIVERY_TIME = 30
def get_distance_information(from_location, to_location):
    """
    使用腾讯地图API获取两点之间的距离信息
    :param from_location: 出发地点（纬度,经度）
    :param to_location: 目的地点（纬度,经度）
    :return: 距离信息
    """
    url = f'https://apis.map.qq.com/ws/distance/v1/?from={from_location}&to={to_location}&key={TENCENT_MAP_API_KEY}'
    response = requests.get(url)
    result = response.json()
    if result['status'] == 0:
        distance = result['result']['elements'][0]['distance']
        duration = result['result']['elements'][0]['duration']
        return {'distance': distance, 'duration': duration}
    else:
        return None
def get_available_deliveryman(deliverymen_data, restaurant_location, costumer_location, orders_data):
    # 计算餐厅和客户之间的距离
    restaurant_costumer_distance = Common.get_distance_information(restaurant_location, costumer_location)
    available_deliveryman = []
    for deliveryman in deliverymen_data:
        deliveryman_location = deliveryman['coordinate']
        # 计算配送员到餐厅和客户的距离
        deliveryman_restaurant_distance = Common.get_distance_information(deliveryman_location, restaurant_location)
        deliveryman_costumer_distance = Common.get_distance_information(deliveryman_location, costumer_location)
        # 检查该配送员是否能够及时送达
        if deliveryman_restaurant_distance + deliveryman_costumer_distance <= restaurant_costumer_distance:
            # 计算配送员能够顺路完成的订单数
            deliveryman['order_count'] = get_order_count_by_deliveryman(deliveryman, orders_data, restaurant_location, costumer_location)
            # 将可用的配送员添加到列表中
            available_deliveryman.append(deliveryman)
    return available_deliveryman

def get_order_count_by_deliveryman(deliveryman, orders_data, restaurant_location, costumer_location):
    order_count = 0
    for order in deliveryman['orders']:
        if order['delivery_status'] == 1:
            # 配送员正在派送订单，不计入顺路订单
            continue
        # 计算餐厅和订单之间的距离
        shop_location = order['shop_coordinate']
        shop_distance = Common.get_distance_information(restaurant_location, shop_location)
        # 计算订单和客户之间的距离
        user_location = order['user_coordinate']
        user_distance = Common.get_distance_information(shop_location, user_location)
        # 判断订单是否在配送员的可达范围内，如果是则计入顺路订单数
        if shop_distance + user_distance <= deliveryman['max_distance']:
            order_count += 1
    return order_count


def sort_deliveryman(deliverymen, order_time):
    """
    对可用的配送员进行排序，按照最大优先级排序。
    :param deliverymen: 可用的配送员列表。
    :param order_time: 订单下单时间，格式为 "%Y-%m-%d %H:%M:%S"。
    :return: 排序后的配送员列表。
    """
    for deliveryman in deliverymen:
        # 计算配送员从餐厅到顾客的距离和时间
        restaurant_to_customer = Common.get_distance_information(deliveryman['coordinate'],costumer_data['costumer_location'])
        deliveryman['restaurant_to_customer_distance'] = restaurant_to_customer['distance']
        deliveryman['restaurant_to_customer_duration'] = restaurant_to_customer['duration']

        # 计算配送员从餐厅到顾客再到餐厅的距离和时间
        restaurant_to_customer_to_restaurant = Common.get_distance_information(deliveryman['coordinate'],costumer_data['costumer_location'],restaurant_data['restaurant_location'])
        deliveryman['restaurant_to_customer_to_restaurant_distance'] = restaurant_to_customer_to_restaurant['distance']
        deliveryman['restaurant_to_customer_to_restaurant_duration'] = restaurant_to_customer_to_restaurant['duration']

        # 计算从配送员的位置到餐厅的距离和时间
        deliveryman_to_restaurant = Common.get_distance_information(deliveryman['coordinate'],
                                                                     restaurant_data['restaurant_location'])
        deliveryman['deliveryman_to_restaurant_distance'] = deliveryman_to_restaurant['distance']
        deliveryman['deliveryman_to_restaurant_duration'] = deliveryman_to_restaurant['duration']

        # 计算订单从下单到配送员到达餐厅的时间
        order_to_deliveryman_to_restaurant_duration = deliveryman['deliveryman_to_restaurant_duration'] + \
                                                      restaurant_data['prepare_time'] + \
                                                      restaurant_to_customer_to_restaurant['duration']
        deliveryman['order_to_deliveryman_to_restaurant_duration'] = order_to_deliveryman_to_restaurant_duration

        # 计算订单从下单到配送员到达顾客的时间
        order_to_deliveryman_to_customer_duration = deliveryman['deliveryman_to_restaurant_duration'] + \
                                                     restaurant_to_customer_to_restaurant['duration'] + \
                                                     costumer_data['costumer_order_duration']
        deliveryman['order_to_deliveryman_to_customer_duration'] = order_to_deliveryman_to_customer_duration

        # 计算配送员的等待时间
        deliveryman['waiting_time'] = max(0, deliveryman['order_to_deliveryman_to_restaurant_duration'] -
                                          (datetime.strptime(order_time, "%Y-%m-%d %H:%M:%S") - datetime.now()).seconds)

    # 按照最大优先级排序
    return sorted(deliverymen, key=lambda x: (x['order_to_deliveryman_to_customer_duration'], -x['waiting_time']))



def choose_deliveryman(deliveryman_list, costumer_location, restaurant_location, prepare_time, order_time):
    """
    选择最优配送员

    :param deliveryman_list: list，配送员列表
    :param costumer_location: str，顾客位置
    :param restaurant_location: str，餐厅位置
    :param prepare_time: int，餐厅准备时间
    :param order_time: str，下单时间
    :return: tuple，最优配送员信息
    """
    # 1. 过滤出可用的配送员列表
    available_deliveryman_list = get_available_deliveryman(deliveryman_list, order_time, prepare_time)
    if not available_deliveryman_list:
        return None

    # 2. 计算每个配送员到餐厅和客户的距离和时间，并根据优先级排序
    distance_list = []
    for deliveryman in available_deliveryman_list:
        distance_to_restaurant = Common.get_distance_information(deliveryman['coordinate'], restaurant_location)
        distance_to_costumer = Common.get_distance_information(deliveryman['coordinate'], costumer_location)
        if distance_to_restaurant and distance_to_costumer:
            distance_list.append({
                'deliveryman': deliveryman,
                'distance': distance_to_restaurant['distance'] + distance_to_costumer['distance'],
                'duration': distance_to_restaurant['duration'] + distance_to_costumer['duration']
            })

    # 3. 根据顺路程度选择最优配送员
    sorted_deliveryman_list = sort_deliveryman(distance_list)
    return sorted_deliveryman_list[0] if sorted_deliveryman_list else None





@app.post("/test2")
def  test2(order_data: str = Form("order_data"),t:Union[int, None]=None):
    Data = eval(order_data)
    Order_data = Data['order']
    Deliveryman_data = Data['delivery']

    Restaurant_data = {}
    Restaurant_data['restaurant_location'] = Order_data['shop_coordinate']
    Restaurant_data['prepare_time'] = Order_data['meal_time']
    Restaurant_data['order_time'] = Order_data['order_time']
    Restaurant_data['delivery_deadline'] = Order_data['delivery_time']
    Restaurant_data['restaurant_preparing_order_count'] = Order_data['shop_order_count']

    Costumer_data = {}
    Costumer_data['costumer_location'] = Order_data['user_coordinate']
    Costumer_data['costumer_order_time'] = Order_data['order_time']

    restaurant_location = Order_data['shop_coordinate']
    client_location = Order_data['user_coordinate']

    Distance_1 = Common.get_distance_information(restaurant_location,client_location,0)
    Distance_1 = Distance_1['data']

    Distance_data = {}
    Distance_data['restaurant_clinet_distance'] = Distance_1




    temp_dict = {}
    temp_dict['restaurant_data']=Restaurant_data
    temp_dict['costumer_data']=Costumer_data
    temp_dict['deliveryman_data']=Deliveryman_data
    temp_dict['distance_data']=Distance_data
    # print(" D ",Distance_1)
    # # 执行示例代码
    # deliveryman_data = Common.read_json_file("deliveryman_data.json")
    # distance_data = Common.read_json_file("distance_data.json")
    # restaurant_data = Common.read_json_file("restaurant_data.json")
    # costumer_data = Common.read_json_file("costumer_data.json")

    deliveryman_data = Deliveryman_data
    distance_data = Distance_data
    restaurant_data = Restaurant_data
    costumer_data = Costumer_data

    # available_deliveryman = get_available_deliveryman(deliveryman_data, restaurant_data['restaurant_location'], restaurant_data['order_time
    # 找到可用的配送员并按照优先级排序
    available_deliveryman = get_available_deliveryman(deliveryman_data, costumer_data, restaurant_data, distance_data)
    sorted_deliveryman = sort_deliveryman(available_deliveryman, restaurant_data['order_time'])
    # 选择最优配送员
    prepare_time = restaurant_data.get('prepare_time')
    restaurant_location = restaurant_data.get('restaurant_location')
    order_time = restaurant_data.get('order_time')

    optimal_deliveryman = choose_deliveryman(available_deliveryman, prepare_time, restaurant_location,
                                     costumer_data['costumer_location'],order_time)
    # optimal_deliveryman = choose_deliveryman(sorted_deliveryman, restaurant_data, costumer_data)
    # 打印最优配送员信息
    print(f"The optimal deliveryman is {optimal_deliveryman['name']}, "
          f"and the estimated delivery time is {optimal_deliveryman['estimated_delivery_time']} minutes.")

    return temp_dict
@app.post("/test")
def  test(order_data: str = Form("order_data"),t:Union[int, None]=None):
    hostname = socket.gethostname()
    # order_data = request.form['order_data']
    # try:
    #     t = int(request.form['t'])
    # except:
    #     t = 0
    # 配送员现有已取餐的订单客户和餐厅的距离
    order_id = eval(order_data)['order']['order_id']
    Common.write_local(str(order_id), "A", str(order_data))
    try:
        pre_order_client_info = Common.get_preOrder_client_info(order_data, t)
    except KeyError as msg:
        Common.write_local(str(order_id), "C", str(msg))
        return []
    # 数据整合
    dist_l = []
    r_data = []
    for data1 in pre_order_client_info:
        deliveryman_dict = Common.get_deliveryman_inf(order_data, data1['id'])
        delivery_man = {}
        delivery_man['id'] = data1['id']
        try:
            delivery_man['name'] = deliveryman_dict['name']
        except:
            delivery_man['name'] = ''
        delivery_man['nex_dist'] = data1['nex_dist']
        try:
            delivery_man['delivering_count'] = deliveryman_dict['delivering_order_count']
        except:
            delivery_man['delivering_count'] = 0
        delivery_man['distance_sum'] = int(data1['with_dist_distance'])
        dist_l.append(delivery_man['distance_sum'])
        r_data.append(delivery_man)
    r_data.sort(key=lambda x: x['distance_sum'])
    server_info_data = {}
    server_info_data['hostname'] = str(hostname)
    server_info_data['response_time'] = time.time()
    for r in r_data:
        r['server_info'] = server_info_data
    Common.write_local(str(order_id), "B", str(r_data))
    return r_data
