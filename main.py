import requests
import json
from typing import List, Tuple


class Common:
    @staticmethod
    def get_distance_information(from_address: str, to_address: str) -> Tuple[str, int, int]:
        """获取两点间距离信息"""
        url = 'https://apis.map.qq.com/ws/distance/v1/'
        params = {
            'mode': 'driving',
            'from': from_address,
            'to': to_address,
            'key': '您的腾讯地图Key'
        }
        try:
            response = requests.get(url, params=params)
            res_json = json.loads(response.text)
            if res_json['status'] == 0:
                results = res_json['result']['elements'][0]
                return (results['distance'], results['duration'], results['duration_traffic'])
            else:
                return ('', 0, 0)
        except:
            return ('', 0, 0)


class Deliveryman:
    def __init__(self, name: str, current_location: str, max_capacity: int):
        self.name = name
        self.current_location = current_location
        self.max_capacity = max_capacity
        self.current_capacity = 0

    def __str__(self):
        return f"Name: {self.name}, Current Location: {self.current_location}, Max Capacity: {self.max_capacity}, Current Capacity: {self.current_capacity}"

    def assign_order(self, order: dict) -> bool:
        """Assign order to deliveryman"""
        if order['capacity'] + self.current_capacity <= self.max_capacity:
            self.current_capacity += order['capacity']
            return True
        else:
            return False


def get_available_deliveryman(deliverymen: List[Deliveryman]) -> List[Deliveryman]:
    """Get available deliveryman"""
    available_deliverymen = []
    for deliveryman in deliverymen:
        if deliveryman.current_capacity < deliveryman.max_capacity:
            available_deliverymen.append(deliveryman)
    return available_deliverymen


def sort_deliveryman(deliverymen: List[Deliveryman], order: dict, restaurant_location: str) -> List[Tuple[Deliveryman, float]]:
    """Sort deliveryman by priority"""
    priority_list = []
    for deliveryman in deliverymen:
        distance = Common.get_distance_information(deliveryman.current_location, order['destination'])[0]
        priority = 1 / distance
        priority_list.append((deliveryman, priority))

    # Sort deliveryman by priority
    priority_list.sort(key=lambda x: x[1], reverse=True)
    return priority_list


def choose_deliveryman(deliverymen: List[Deliveryman], order: dict, prepare_time: int, restaurant_location: str) -> Deliveryman:
    """Choose the optimal deliveryman for the order"""
    priority_list = sort_deliveryman(deliverymen, order, restaurant_location)

    for deliveryman, _ in priority_list:
        # Calculate time to deliver the order
        delivery_time = Common.get_distance_information(deliveryman.current_location, order['destination'])[2] + prepare_time

        # Check if the deliveryman can deliver the order before the deadline
        if delivery_time <= order['deadline']:
            # Assign the order to the deliveryman
            if deliveryman.assign_order(order):
                return deliveryman

    # No available deliveryman can deliver the order before the deadline
    return None


def delivery(orders, deliverymen, restaurant_location, prepare_time=10):
    """将订单分配给配送员，返回每个订单的配送员和配送时间"""
    # 为每个订单计算最早的可配送时间
    for order in orders:
        order["earliest_delivery_time"] = order["order_time"] + timedelta(minutes=prepare_time)
    
    # 计算每个配送员的最早出发时间
    for deliveryman in deliverymen:
        deliveryman["earliest_departure_time"] = max(deliveryman["last_delivery_time"], datetime.now())
        deliveryman["available"] = True
    
    # 找到可用的配送员并按照优先级排序
    available_deliveryman = get_available_deliveryman(deliverymen)
    if not available_deliveryman:
        print("No deliveryman is available right now!")
        return
    
    # 为订单选择最优的配送员
    for order in orders:
        deliveryman = choose_deliveryman(order["earliest_delivery_time"], restaurant_location, available_deliveryman)
        if not deliveryman:
            print(f"No available deliveryman for order {order['order_id']}")
            continue
        deliveryman["available"] = False
        order["deliveryman_id"] = deliveryman["deliveryman_id"]
        delivery_time = Common.get_distance_information(deliveryman["location"], restaurant_location) / deliveryman["speed"]
        order["delivery_time"] = delivery_time
        order["delivery_start_time"] = max(deliveryman["earliest_departure_time"], order["earliest_delivery_time"])
        order["delivery_end_time"] = order["delivery_start_time"] + timedelta(minutes=delivery_time)
        deliveryman["earliest_departure_time"] = order["delivery_end_time"]
        deliveryman["last_delivery_time"] = order["delivery_end_time"]
    
    return orders, deliverymen

if __name__ == '__main__':
    orders_data = [
        {"order_id": "1", "user_location": [39.903371, 116.409367], "restaurant_location": [39.908736, 116.395173], "delivery_time": 40, "deadline": 60},
        {"order_id": "2", "user_location": [39.900584, 116.401318], "restaurant_location": [39.908805, 116.397291], "delivery_time": 30, "deadline": 90},
        {"order_id": "3", "user_location": [39.914509, 116.404737], "restaurant_location": [39.90856, 116.399477], "delivery_time": 50, "deadline": 70},
        {"order_id": "4", "user_location": [39.907463, 116.397144], "restaurant_location": [39.907463, 116.397144], "delivery_time": 60, "deadline": 80},
        {"order_id": "5", "user_location": [39.914623, 116.404369], "restaurant_location": [39.903497, 116.406238], "delivery_time": 20, "deadline": 40},
        {"order_id": "6", "user_location": [39.905358, 116.407537], "restaurant_location": [39.908901, 116.391711], "delivery_time": 70, "deadline": 90},
    ]
    available_deliveryman = get_available_deliveryman(orders_data)
    prepare_time = 10
    max_delivery_time = 60
    max_delivery_count = 3
    restaurant_location = [39.908736, 116.395173]
    chosen_deliveryman = choose_deliveryman(prepare_time, restaurant_location, available_deliveryman, max_delivery_time, max_delivery_count)
    if chosen_deliveryman:
        delivery(orders_data, chosen_deliveryman, prepare_time)
