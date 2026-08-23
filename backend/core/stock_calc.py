# -*- coding: utf-8 -*-


def calc_new_avg_price(old_num: float, old_cost: float, add_num: float, add_cost: float):
    new_num = old_num + add_num
    new_cost = old_cost + add_cost
    if new_num == 0:
        new_avg = 0.0
    else:
        new_avg = new_cost / new_num
    return round(new_num, 6), round(new_cost, 6), round(new_avg, 6)


def calc_out_stock(old_num: float, old_cost: float, out_num: float, avg_price: float):
    remain_num = old_num - out_num
    remain_cost = old_cost - (out_num * avg_price)
    if remain_num < 0:
        remain_num = 0.0
    if remain_cost < 0:
        remain_cost = 0.0
    return round(remain_num, 6), round(remain_cost, 6)
