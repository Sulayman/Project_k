import requests
from typing import List, Tuple


def get_distance_information(from_loc: str, to_loc: str) -> int:
    """
    调用腾讯地图API获取两个坐标点之间的距离信息
    :param from_loc: 起点坐标
    :param to_loc: 终点坐标
    :return: 两点之间距离（单位：米）
    """
    url = f"https://apis.map.qq.com/ws/distance/v1/?mode=walking&from={from_loc}&to={to_loc}&key=YOUR_TENCENT_MAP_API_KEY"
    response = requests.get(url)
    data = response.json()
    if data["status"] != 0:
        raise Exception("Failed to get distance information")
    return data["result"]["elements"][0]["distance"]


def get_available_deliveryman(deliveryman_data: List[dict], restaurant_location: str) -> List[dict]:
    """
    获取当前有空闲配送员的列表
    :param deliveryman_data: 配送员列表
    :param restaurant_location: 餐厅位置
    :return: 空闲配送员列表
    """
    available_deliveryman = []
    for deliveryman in deliveryman_data:
        if deliveryman["delivering_order_count"] > 0:
            continue
        from_loc = deliveryman["coordinate"]
        to_loc = restaurant_location
        distance = get_distance_information(from_loc, to_loc)
        if distance > 5000:
            continue
        available_deliveryman.append(deliveryman)
    return available_deliveryman


def sort_deliveryman(deliveryman_list: List[dict], costumer_location: str) -> List[dict]:
    """
    对可用的配送员按照优先级排序
    :param deliveryman_list: 可用配送员列表
    :param costumer_location: 客户位置
    :return: 排序后的配送员列表
    """
    # 按距离从近到远排序
    deliveryman_list.sort(key=lambda x: get_distance_information(x["coordinate"], costumer_location))
    # 按已完成订单数量从少到多排序
    deliveryman_list.sort(key=lambda x: x["delivered_order_count"])
    # 按正在配送订单数从少到多排序
    deliveryman_list.sort(key=lambda x: x["delivering_order_count"])
    return deliveryman_list

def choose_deliveryman(prepare_time: int, restaurant_location: str, deliverymen: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    从可用的配送员中选出最优的一个
    :param prepare_time: int, 餐厅准备时间，单位为分钟
    :param restaurant_location: str, 餐厅经纬度，用逗号分隔
    :param deliverymen: List[Dict[str, Any]], 可用的配送员列表
    :return: Dict[str, Any], 最优的配送员
    """
    # 根据餐厅和客户位置计算距离
    client_location = orders_data['costumer_data']['costumer_location']
    restaurant_client_distance = Common.get_distance_information(restaurant_location, client_location)
    # 根据时间和距离计算订单最晚的送达时间
    latest_delivery_time = Common.get_latest_delivery_time(orders_data, restaurant_client_distance)

    # 计算每个配送员在最晚送达时间前能够完成的配送单数
    for deliveryman in deliverymen:
        max_order_count = Common.get_deliveryman_max_order_count(deliveryman, prepare_time, latest_delivery_time, restaurant_client_distance)
        deliveryman['max_order_count'] = max_order_count

    # 按照可配送单数从大到小排序
    deliverymen = sorted(deliverymen, key=lambda x: x['max_order_count'], reverse=True)

    # 选出最优的可配送单数
    max_order_count = deliverymen[0]['max_order_count']
    best_deliverymen = []
    for deliveryman in deliverymen:
        if deliveryman['max_order_count'] == max_order_count:
            best_deliverymen.append(deliveryman)
        else:
            break

    # 选出最优的可配送单数中，距离最近的配送员
    best_deliveryman = None
    best_distance = None
    for deliveryman in best_deliverymen:
        if not deliveryman['orders']:
            best_deliveryman = deliveryman
            break

        distance = Common.get_deliveryman_distance_to_restaurant(deliveryman, restaurant_location)
        if not best_distance or distance < best_distance:
            best_deliveryman = deliveryman
            best_distance = distance

    return best_deliveryman
