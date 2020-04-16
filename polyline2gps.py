import linecache

import requests
import math
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import os
import time
import datetime
import logging
from functools import wraps
import webbrowser


def func_time(f):
    """
    记录每个函数执行时间
    :param f: 函数
    :return: 运行时间
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time: float = time.time()
        result = f(*args, **kwargs)
        end_time: float = time.time()
        logger.info(f'{f.__name__}总计用时{round((end_time - start_time),2)}')
        return result
    return wrapper


@func_time
def open_gps_html(html_name):
    """
    打开前端页面
    :param html_name: html文件名
    :return: None
    """
    data_func = linecache.getlines('gps.js')
    base = linecache.getlines('base.html')
    with open(html_name, "w") as f:
        f.write(''.join(base[0:24] + list(line_array) + data_func + list(vs_js) + base[24:27]))
    webbrowser.open_new_tab(html_name)


def write_log(log_name):
    """
    :param：log_name 设置log名称
    :return: 本地log文件、terminal log流
    """
    global logger

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(f'{log_name}{time.strftime("%Y-%m-%d-%H-%M-%S")}.log')
    fh.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('[%(asctime)s][%(levelname)s] ## %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)


def gcj2wgs(location):
    """
    :param location:GJC02格式GPS坐标 as 113.923745,22.530824
    :return: WGS84格式GPS坐标
    """
    lon_gcj = float(location[0:location.find(",")])
    lat_gcj = float(location[location.find(",") + 1:len(location)])
    a = 6378245.0  # 克拉索夫斯基椭球参数长半轴a
    ee = 0.00669342162296594323  # 克拉索夫斯基椭球参数第一偏心率平方
    pi = 3.14159265358979324  # 圆周率
    # 以下为转换公式
    x = lon_gcj - 105.0
    y = lat_gcj - 35.0
    # 经度
    d_lon = 300.0 + x + 2.0 * y + 0.1 * x * x + \
        0.1 * x * y + 0.1 * math.sqrt(abs(x))
    d_lon += (20.0 * math.sin(6.0 * x * pi) + 20.0 *
             math.sin(2.0 * x * pi)) * 2.0 / 3.0
    d_lon += (20.0 * math.sin(x * pi) + 40.0 *
             math.sin(x / 3.0 * pi)) * 2.0 / 3.0
    d_lon += (150.0 * math.sin(x / 12.0 * pi) + 300.0 *
             math.sin(x / 30.0 * pi)) * 2.0 / 3.0
    # 纬度
    d_lat = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * \
        y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    d_lat += (20.0 * math.sin(6.0 * x * pi) + 20.0 *
             math.sin(2.0 * x * pi)) * 2.0 / 3.0
    d_lat += (20.0 * math.sin(y * pi) + 40.0 *
             math.sin(y / 3.0 * pi)) * 2.0 / 3.0
    d_lat += (160.0 * math.sin(y / 12.0 * pi) + 320 *
             math.sin(y * pi / 30.0)) * 2.0 / 3.0
    rad_lat = lat_gcj / 180.0 * pi
    magic = math.sin(rad_lat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * pi)
    d_lon = (d_lon * 180.0) / (a / sqrt_magic * math.cos(rad_lat) * pi)
    lon_wgs = lon_gcj - d_lon
    lat_wgs = lat_gcj - d_lat
    return lon_wgs, lat_wgs


# 将地址转化成坐标
@func_time
def get_loc(address):
    """
    :param address:自然语言地址
    :return: address对应的GCJ02格式经纬度坐标
    """
    parameters = {
        'key': '429a22f69c6320aac18b2aa9b2aef883',
        'address': address}
    base = 'https://restapi.amap.com/v3/geocode/geo'
    response = requests.get(base, parameters)
    answer = response.json()
    lon = answer['geocodes'][0]['location'].split(',')[0]
    lat = answer['geocodes'][0]['location'].split(',')[1]
    return lon + "," + lat


# 获取polyline坐标串接口：https://restapi.amap.com/v3/direction/driving?origin=116.45925,39.910031&destination=116.587922,40.081577&output=xml&key=429a22f69c6320aac18b2aa9b2aef883
@func_time
def get_polyline(src, des):
    """
    :param src:始发地
    :param des:目的地
    :return:
    """
    origin = get_loc(src)
    destination = get_loc(des)
    base_url = "https://restapi.amap.com/v3/direction/driving?"
    parameter = {
        'origin': origin,
        'destination': destination,
        'key': '429a22f69c6320aac18b2aa9b2aef883',
        'strategy': strategy}
    res = requests.get(base_url, parameter)
    json = res.json()
    steps = json['route']['paths'][0]['steps']
    polyline_list = []
    pol_list = [steps[i]['polyline'] for i in range(len(steps))]
    for pol in pol_list:
        lst = pol.split(';')
        for i in lst:
            polyline_list.append(i)
    return polyline_list


@func_time
def gcj_location_to_wgs(src,des):
    """
    :param src:始发地
    :param des:目的地
    :return:
    """
    wgs_location = []
    gcj_location = get_polyline(src,des)
    wgs_location = [str(gcj2wgs(gcj_location[i])).replace("(", "").replace(")", "") for i in range(len(gcj_location))]
    return wgs_location


@func_time
def get_wgs84_location(src,des):
    """
    获取原始经纬度坐标dataframe
    :param src:
    :param des:
    :return:
    """
    global df_wgs84
    wgs_location = gcj_location_to_wgs(src, des)
    a = pd.DataFrame(wgs_location, columns=['wgsLocation']).drop_duplicates()
    df_wgs84 = a['wgsLocation'].str.split(',', expand=True).rename(columns={0: 'lon_wgs84', 1: 'lat_wgs84'})
    # wgs84_df.to_excel(file_path, index=False)
    # print(df_wgs84)


@func_time
def get_gcj02_location(src, des):
    """
    保存原始经纬度坐标至excel
    :param src:
    :param des:
    :return:
    """
    global df_gcj02
    polyline = get_polyline(src, des)
    polyline_df = pd.DataFrame(polyline, columns=['polyline']).drop_duplicates()
    df_gcj02 = polyline_df['polyline'].str.split(',', expand=True).rename(columns={0: 'lon_gcj02', 1: 'lat_gcj02'})
    # orig_df.to_excel(orig_file, index=False)
    # print(df_gcj02)


def interpolation(loc1, loc2, a, b, v_speed):
    """
    对两个坐标点之间进行线性插值
    :param v_speed: 车速
    :param loc1: 坐标1
    :param loc2: 坐标2
    :param a: 坐标1的经/纬度
    :param b: 坐标2的经/纬度
    :param vs_h: 车速(km/h)
    :return: 返回插值后的坐标list
    """
    inter_value = []
    n = geodesic(loc1, loc2).m / (v_speed * 1000 * bus_interval_time / 3600)  # m/100ms
    delta = abs((a - b) / n)  # 步长
    if a > b:
        inter_value = np.arange(a, b, -delta)
    elif a < b:
        inter_value = np.arange(a, b, delta)
    elif a == b:
        inter_value = np.linspace(a, b, n+1)
    return inter_value


@func_time
def interval_after_orig_lonlat():
    """
    将插值后的原始经纬度值写入表中
    :return: 返回插值后的gcj02序列
    """
    global df_gcj02_new
    inter_origlonlist = []
    inter_origlatlist = []
    orig_lat = df_gcj02['lat_gcj02'].astype('float').tolist()
    orig_lon = df_gcj02['lon_gcj02'].astype('float').tolist()
    orig_loc = list(zip(orig_lat, orig_lon))
    for i in range(len(orig_loc)):
        if i < len(orig_loc) - 1:
            inter_origlon = interpolation(
                orig_loc[i], orig_loc[i + 1], orig_lon[i], orig_lon[i + 1], vs_h)
            inter_origlonlist.extend(pd.Series(inter_origlon))
            inter_origlat = interpolation(
                orig_loc[i], orig_loc[i + 1], orig_lat[i], orig_lat[i + 1], vs_h)
            inter_origlatlist.extend(pd.Series(inter_origlat))
        else:
            break
    df_gcj02_new = pd.concat([pd.DataFrame({'origlonvalues': inter_origlonlist}), pd.DataFrame(
        {'origlatvalues': inter_origlatlist})], axis=1)
    # print(df_gcj02_new)


@func_time
def get_linearr():
    """
    将lineArr数组，车速传入js脚本。
    :return: 返回生成的序列
    """
    global line_array, vs_js
    lon_list = pd.Series(df_gcj02_new['origlonvalues']).tolist()
    lat_list = pd.Series(df_gcj02_new['origlatvalues']).tolist()
    line_arr = [[lon_list[i], lat_list[i]] for i in range(len(lon_list))]
    line_str = [(str(i)+',') for i in line_arr]
    a = ''
    b = a.join(line_str)
    line_array = ('var lineArr = ' + '[' + b[:-1] + ']; \n')
    vs_js = "function startAnimation () {\n marker.moveAlong(lineArr, " + str(vs_h) + "); \n}\n"


@func_time
def interval_after_lonlat():
    """
    将插值后的wgs84格式经纬度值写入表中
    :return: 返回生成的序列
    """
    global final_df
    inter_lon_list = []
    inter_lat_list = []
    # final_df = pd.read_excel(file_path).drop_duplicates()
    lat = pd.Series(df_wgs84['lat_wgs84'].astype('float')).tolist()
    lon = pd.Series(df_wgs84['lon_wgs84'].astype('float')).tolist()
    loc = list(zip(lat, lon))
    for i in range(len(loc)):
        if i < len(loc) - 1:
            interLon = interpolation(
                loc[i], loc[i + 1], lon[i], lon[i + 1], vs_h)
            inter_lon_list.extend(pd.Series(interLon))
            interLat = interpolation(
                loc[i], loc[i + 1], lat[i], lat[i + 1], vs_h)
            inter_lat_list.extend(pd.Series(interLat))
        else:
            break
    final_df = pd.concat([pd.DataFrame({'lonValues': inter_lon_list}), pd.DataFrame(
        {'latValues': inter_lat_list})], axis=1)
    # print(final_df)


def series(lst, length):
    """
    生成burstID序列，序列长度等于各列长
    :param lst: 传[0,1,2,3]
    :param length: 生成序列的长度
    :return: 返回生成的序列
    """
    a = []
    for j in range(length):
        if j <= int(length / 4):
            for i in lst:
                a.append(i)
        else:
            break
    return a[0:length]


def heading_angle(lon_a, lat_a, lon_b, lat_b):
    """
    :return: angle list: 算法生成每两个点之间的航向角
    """
    y = math.sin(lon_b - lon_a) * math.cos(lat_b)
    x = math.cos(lat_a) * math.sin(lat_b) - math.sin(lat_a) * \
        math.cos(lat_b) * math.cos(lon_b - lon_a)
    angle = round(math.degrees(math.atan2(y, x)))
    if angle < 0:
        angle = angle + 360
    return angle


@func_time
def angle_list():
    """
    :return: angle list: 算法合成生成航向角list
    """
    angle = []
    lat_list = final_df['lonValues'].values.tolist()
    lon_list = final_df['latValues'].values.tolist()
    for i in range(len(lat_list)):
        if i < len(lat_list) - 1:
            angle.append(heading_angle(lon_list[i], lat_list[i], lon_list[i + 1], lat_list[i + 1]))
    angle.append(angle[i - 1])
    # print(len(angle))
    return angle


@func_time
def datetime_to_msg(can_id):
    """
    :param can_id: GPS date 351
    :return: date-msg: 十六进制的报文
    """
    global date
    brst_ids = [0, 1, 2, 3]
    id = int(int(can_id, 16) / 8)
    time_list = pd.date_range(
        basetime,
        freq="100ms",
        periods=len(final_df)).strftime('%Y-%m-%d-%H-%M-%S-%f')
    a = time_list.str.split('-', expand=True)
    b = pd.Series(5., a)
    date = b.reset_index()
    date.columns = ['YY', 'MM', 'DD', 'H', 'M', 'S', 'MS', '0']
    date['YY'] = date['YY'].str[2:]
    date['MS'] = date['MS'].str[:3]
    date['ID'] = series(brst_ids, len(final_df))
    date['BIN-YY'] = date['YY'].apply(lambda x: '{:09b}'.format(int(x)))
    date['BIN-MM'] = date['MM'].apply(lambda x: '{:05b}'.format(int(x)))
    date['BIN-DD'] = date['DD'].apply(lambda x: '{:06b}'.format(int(x)))
    date['BIN-H'] = date['H'].apply(lambda x: '{:06b}'.format(int(x)))
    date['BIN-M'] = date['M'].apply(lambda x: '{:07b}'.format(int(x)))
    date['BIN-S'] = date['S'].apply(lambda x: '{:07b}'.format(int(x)))
    date['BIN-MS'] = date['MS'].apply(lambda x: '{:011b}'.format(int(x)))
    date['BIN-ID'] = date['ID'].apply(lambda x: '{:02b}'.format(int(x)))
    date['BIN-53'] = date['BIN-YY']+date['BIN-MM']+date['BIN-DD']+date['BIN-H']+date['BIN-M']+date['BIN-S']+date['BIN-MS']+date['BIN-ID']
    date['B0'] = date['BIN-53'].str[0:8]
    date['B1'] = date['BIN-53'].str[8:16]
    date['B2'] = date['BIN-53'].str[16:24]
    date['B3'] = date['BIN-53'].str[24:32]
    date['B4'] = date['BIN-53'].str[32:40]
    date['B5'] = date['BIN-53'].str[40:48]
    date['B6-temp'] = date['BIN-53'].str[48:53] + '000'
    # checksum = int(byte0, 2) + int(byte1, 2) + int(byte2, 2) + int(byte3, 2) + int(byte4, 2) + int(byte5, 2) + id + byte6                                                                                        2) + id + byte6
    date['B0-int'] = date['B0'].apply(lambda x: int(x, 2))
    date['B1-int'] = date['B1'].apply(lambda x: int(x, 2))
    date['B2-int'] = date['B2'].apply(lambda x: int(x, 2))
    date['B3-int'] = date['B3'].apply(lambda x: int(x, 2))
    date['B4-int'] = date['B4'].apply(lambda x: int(x, 2))
    date['B5-int'] = date['B5'].apply(lambda x: int(x, 2))
    date['B6-temp-int'] = date['B6-temp'].apply(lambda x: int(x, 2))
    date['B6&F8'] = np.bitwise_and(date['B6-temp-int'], 248)
    date['B6&F8 >>3'] = np.right_shift(date['B6&F8'], 3)
    date['CHKSUM'] = date['B0-int']+date['B1-int']+date['B2-int']+date['B3-int']+date['B4-int']+date['B5-int']+date['B6&F8 >>3']+id
    date['BIN-CHKSUM'] = date['CHKSUM'].apply(lambda x: '{:011b}'.format(int(x)))
    date['BIN-64'] = date['BIN-53']+date['BIN-CHKSUM']
    date['B6'] = date['BIN-64'].str[48:56]
    date['B7'] = date['BIN-64'].str[56:64]
    date['B6-int'] = date['B6'].apply(lambda x: int(x, 2))
    date['B7-int'] = date['B7'].apply(lambda x: int(x, 2))
    date['B0-hex'] = date['B0-int'].apply(lambda x: '{0:02X}'.format(x))
    date['B1-hex'] = date['B1-int'].apply(lambda x: '{0:02X}'.format(x))
    date['B2-hex'] = date['B2-int'].apply(lambda x: '{0:02X}'.format(x))
    date['B3-hex'] = date['B3-int'].apply(lambda x: '{0:02X}'.format(x))
    date['B4-hex'] = date['B4-int'].apply(lambda x: '{0:02X}'.format(x))
    date['B5-hex'] = date['B5-int'].apply(lambda x: '{0:02X}'.format(x))
    date['B6-hex'] = date['B6-int'].apply(lambda x: '{0:02X}'.format(x))
    date['B7-hex'] = date['B7-int'].apply(lambda x: '{0:02X}'.format(x))
    date['time'] = [format((0.001 + i / 10), '0.6f') for i in range(len(final_df))]
    date['channel'] = 0
    date['asc-msg'] = date['time'] + " 0 " + can_id + '             Rx  d 8 ' + \
                     date['B0-hex'] + ' ' + date['B1-hex'] + ' ' + date['B2-hex'] + ' ' + date['B3-hex'] + ' ' \
                     + date['B4-hex'] + ' ' + date['B5-hex'] + ' ' + date['B6-hex'] + ' ' + date['B7-hex'] + ' '
    # print(date['asc-msg'])
    # ang.to_csv("date.csv", index = False)  # 按指定列名顺序输出df
    return date[['time', 'asc-msg']]


@func_time
def angle_to_msg(can_id):
    """
    :param can_id: 航向角353
    :return: ang-msg: 十六进制的报文
    """
    global ang
    brst_ids = [0, 1, 2, 3]
    id = int(int(can_id, 16) / 8)
    ang = pd.DataFrame()
    ang['angle'] = angle_list()
    ang['speed'] = vs_h
    ang['elevation'] = elevation+1000000
    ang['ID'] = series(brst_ids, len(final_df))
    ang['blank'] = 0
    ang['BIN-angle'] = ang['angle'].apply(lambda x: '{:013b}'.format((int(x) + 90) * 10))
    ang['BIN-speed'] = ang['speed'].apply(lambda x: '{:08b}'.format(int(x))) + '0'
    ang['BIN-elevation'] = ang['elevation'].apply(lambda x: '{:023b}'.format(int(x)))
    ang['BIN-ID'] = ang['ID'].apply(lambda x: '{:06b}'.format(int(x)))
    ang['BIN-blank'] = ang['blank'].apply(lambda x: '{:03b}'.format(int(x)))
    ang['BIN-53'] = ang['BIN-angle'] + ang['BIN-speed'] + ang['BIN-elevation'] + ang['BIN-ID'] + ang['BIN-blank']
    ang['B0'] = ang['BIN-53'].str[0:8]
    ang['B1'] = ang['BIN-53'].str[8:16]
    ang['B2'] = ang['BIN-53'].str[16:24]
    ang['B3'] = ang['BIN-53'].str[24:32]
    ang['B4'] = ang['BIN-53'].str[32:40]
    ang['B5'] = ang['BIN-53'].str[40:48]
    ang['B6-temp'] = ang['BIN-53'].str[48:53] + '000'
    ang['B0-int'] = ang['B0'].apply(lambda x: int(x, 2))
    ang['B1-int'] = ang['B1'].apply(lambda x: int(x, 2))
    ang['B2-int'] = ang['B2'].apply(lambda x: int(x, 2))
    ang['B3-int'] = ang['B3'].apply(lambda x: int(x, 2))
    ang['B4-int'] = ang['B4'].apply(lambda x: int(x, 2))
    ang['B5-int'] = ang['B5'].apply(lambda x: int(x, 2))
    ang['B6-temp-int'] = ang['B6-temp'].apply(lambda x: int(x, 2))
    ang['B6&F8'] = np.bitwise_and(ang['B6-temp-int'], 248)  # 248=0xF8
    ang['B6&F8 >>3'] = np.right_shift(ang['B6&F8'], 3)
    ang['CHKSUM'] = ang['B0-int']+ang['B1-int']+ang['B2-int']+ang['B3-int']+ang['B4-int']+ang['B5-int']+ang['B6&F8 >>3']+id
    ang['BIN-CHKSUM'] = ang['CHKSUM'].apply(lambda x: '{:011b}'.format(int(x)))
    ang['BIN-64'] = ang['BIN-53']+ang['BIN-CHKSUM']
    ang['B6'] = ang['BIN-64'].str[48:56]
    ang['B7'] = ang['BIN-64'].str[56:64]
    ang['B6-int'] = ang['B6'].apply(lambda x: int(x, 2))
    ang['B7-int'] = ang['B7'].apply(lambda x: int(x, 2))
    ang['B0-hex'] = ang['B0-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['B1-hex'] = ang['B1-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['B2-hex'] = ang['B2-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['B3-hex'] = ang['B3-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['B4-hex'] = ang['B4-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['B5-hex'] = ang['B5-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['B6-hex'] = ang['B6-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['B7-hex'] = ang['B7-int'].apply(lambda x: '{0:02X}'.format(x))
    ang['time'] = [format((0.000 + i / 10), '0.6f') for i in range(len(final_df))]
    ang['channel'] = 0
    ang['asc-msg'] = ang['time'] + " 0 " + can_id + '             Rx  d 8 ' + \
                     ang['B0-hex'] + ' ' + ang['B1-hex'] + ' ' + ang['B2-hex'] + ' ' + ang['B3-hex'] + ' ' \
                     + ang['B4-hex'] + ' ' + ang['B5-hex'] + ' ' + ang['B6-hex'] + ' ' + ang['B7-hex'] + ' '
    # print(ang['asc-msg'])
    # ang.to_csv("ang.csv", index = False)  # 按指定列名顺序输出df
    return ang[['time', 'asc-msg']]


@func_time
def lat_to_msg(can_id):
    """
    :param can_id: lat纬度为'35C'，lon经度为'35D'
    :return: msg: 十六进制的报文
    """
    global lat
    msg = []
    brst_ids = [0, 1, 2, 3]
    id = int(int(can_id, 16) / 8)
    # print('数据总长度为', len(final_df))
    lat = pd.DataFrame()
    lat['BIN-lon'] = final_df['latValues'].apply(lambda x: '{:032b}'.format(int(x*3600*1000)))
    lat['BIN-spare'] = '0000000000000000' #16位
    lat['ID'] = series(brst_ids, len(final_df))
    lat['BIN-ID'] = lat['ID'].apply(lambda x: '{:05b}'.format(int(x)))
    lat['BIN-53'] = lat['BIN-lon'] + lat['BIN-spare'] + lat['BIN-ID']
    lat['B0'] = lat['BIN-53'].str[0:8]
    lat['B1'] = lat['BIN-53'].str[8:16]
    lat['B2'] = lat['BIN-53'].str[16:24]
    lat['B3'] = lat['BIN-53'].str[24:32]
    lat['B4'] = lat['BIN-53'].str[32:40]
    lat['B5'] = lat['BIN-53'].str[40:48]
    lat['B6-temp'] = lat['BIN-53'].str[48:53] + '000'
    lat['B0-int'] = lat['B0'].apply(lambda x: int(x, 2))
    lat['B1-int'] = lat['B1'].apply(lambda x: int(x, 2))
    lat['B2-int'] = lat['B2'].apply(lambda x: int(x, 2))
    lat['B3-int'] = lat['B3'].apply(lambda x: int(x, 2))
    lat['B4-int'] = lat['B4'].apply(lambda x: int(x, 2))
    lat['B5-int'] = lat['B5'].apply(lambda x: int(x, 2))
    lat['B6-temp-int'] = lat['B6-temp'].apply(lambda x: int(x, 2))
    lat['B6&F8'] = np.bitwise_and(lat['B6-temp-int'], 248)
    lat['B6&F8 >>3'] = np.right_shift(lat['B6&F8'], 3)
    lat['CHKSUM'] = lat['B0-int']+lat['B1-int']+lat['B2-int']+lat['B3-int']+lat['B4-int']+lat['B5-int']+lat['B6&F8 >>3']+id
    lat['BIN-CHKSUM'] = lat['CHKSUM'].apply(lambda x: '{:011b}'.format(int(x)))
    lat['BIN-64'] = lat['BIN-53']+lat['BIN-CHKSUM']
    lat['B6'] = lat['BIN-64'].str[48:56]
    lat['B7'] = lat['BIN-64'].str[56:64]
    lat['B6-int'] = lat['B6'].apply(lambda x: int(x, 2))
    lat['B7-int'] = lat['B7'].apply(lambda x: int(x, 2))
    lat['B0-hex'] = lat['B0-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['B1-hex'] = lat['B1-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['B2-hex'] = lat['B2-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['B3-hex'] = lat['B3-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['B4-hex'] = lat['B4-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['B5-hex'] = lat['B5-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['B6-hex'] = lat['B6-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['B7-hex'] = lat['B7-int'].apply(lambda x: '{0:02X}'.format(x))
    lat['time'] = [format((0.002 + i / 10),'0.6f') for i in range(len(final_df))]
    lat['channel'] = 0
    lat['asc-msg'] = lat['time'] + " 0 " + can_id + '             Rx  d 8 ' + \
                     lat['B0-hex'] + ' ' + lat['B1-hex'] + ' ' + lat['B2-hex'] + ' ' + lat['B3-hex'] + ' ' \
                     + lat['B4-hex'] + ' ' + lat['B5-hex'] + ' ' + lat['B6-hex'] + ' ' + lat['B7-hex'] + ' '
    # print(lat['asc-msg'])
    # lat.to_csv("lat.csv", index=False)  # 按指定列名顺序输出df
    return lat[['time', 'asc-msg']]


@func_time
def lon_to_msg(can_id):
    """
    :param can_id: lat纬度为'35C'，lon经度为'35D'
    :return: msg: 十六进制的报文
    """
    global lon
    msg = []
    brst_ids = [0, 8, 16, 24]
    id = int(int(can_id, 16) / 8)
    # print('数据总长度为', len(final_df))
    lon = pd.DataFrame()
    lon['BIN-lon'] = final_df['lonValues'].apply(lambda x: '{:032b}'.format(int(x*3600*1000)))
    lon['BIN-spare'] = '0000000000000000' #16位
    lon['ID'] = series(brst_ids, len(final_df))
    lon['BIN-ID'] = lon['ID'].apply(lambda x: '{:05b}'.format(int(x)))
    lon['BIN-53'] = lon['BIN-lon'] + lon['BIN-spare'] + lon['BIN-ID']
    lon['B0'] = lon['BIN-53'].str[0:8]
    lon['B1'] = lon['BIN-53'].str[8:16]
    lon['B2'] = lon['BIN-53'].str[16:24]
    lon['B3'] = lon['BIN-53'].str[24:32]
    lon['B4'] = lon['BIN-53'].str[32:40]
    lon['B5'] = lon['BIN-53'].str[40:48]
    lon['B6-temp'] = lon['BIN-53'].str[48:53] + '000'
    lon['B0-int'] = lon['B0'].apply(lambda x: int(x, 2))
    lon['B1-int'] = lon['B1'].apply(lambda x: int(x, 2))
    lon['B2-int'] = lon['B2'].apply(lambda x: int(x, 2))
    lon['B3-int'] = lon['B3'].apply(lambda x: int(x, 2))
    lon['B4-int'] = lon['B4'].apply(lambda x: int(x, 2))
    lon['B5-int'] = lon['B5'].apply(lambda x: int(x, 2))
    lon['B6-temp-int'] = lon['B6-temp'].apply(lambda x: int(x, 2))
    lon['B6&F8'] = np.bitwise_and(lon['B6-temp-int'], 248)
    lon['B6&F8 >>3'] = np.right_shift(lon['B6&F8'], 3)
    lon['CHKSUM'] = lon['B0-int']+lon['B1-int']+lon['B2-int']+lon['B3-int']+lon['B4-int']+lon['B5-int']+lon['B6&F8 >>3']+id
    lon['BIN-CHKSUM'] = lon['CHKSUM'].apply(lambda x: '{:011b}'.format(int(x)))
    lon['BIN-64'] = lon['BIN-53']+lon['BIN-CHKSUM']
    lon['B6'] = lon['BIN-64'].str[48:56]
    lon['B7'] = lon['BIN-64'].str[56:64]
    lon['B6-int'] = lon['B6'].apply(lambda x: int(x, 2))
    lon['B7-int'] = lon['B7'].apply(lambda x: int(x, 2))
    lon['B0-hex'] = lon['B0-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['B1-hex'] = lon['B1-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['B2-hex'] = lon['B2-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['B3-hex'] = lon['B3-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['B4-hex'] = lon['B4-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['B5-hex'] = lon['B5-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['B6-hex'] = lon['B6-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['B7-hex'] = lon['B7-int'].apply(lambda x: '{0:02X}'.format(x))
    lon['time'] = [format((0.003 + i / 10), '0.6f') for i in range(len(final_df))]
    lon['channel'] = 0
    lon['asc-msg'] = lon['time'] + " 0 " + can_id + '             Rx  d 8 ' + \
                     lon['B0-hex'] + ' ' + lon['B1-hex'] + ' ' + lon['B2-hex'] + ' ' + lon['B3-hex'] + ' ' \
                     + lon['B4-hex'] + ' ' + lon['B5-hex'] + ' ' + lon['B6-hex'] + ' ' + lon['B7-hex'] + ' '
    # print(lon['asc-msg'])
    # ang.to_csv("lon.csv", index = False)  # 按指定列名顺序输出df
    return lon[['time', 'asc-msg']]


@func_time
def merge_message():
    """
    :return: msg: 合并后的十六进制的报文
    """
    global msg_all
    msg_all = pd.DataFrame()
    msg_all = pd.concat([date[['time', 'asc-msg']], ang[['time', 'asc-msg']], lat[['time', 'asc-msg']],
                         lon[['time', 'asc-msg']]])
    msg_all['time'] = msg_all['time'].astype('float')
    msg_all.sort_values(by=['time'], ascending=True, inplace=True)
    return msg_all
    # print(msg_all)


@func_time
def msg_to_asc():
    """
    :return: asc文件:
    """
    msg_file = f'{time.strftime("%Y_%m_%d_%H_%M")}_{src}_{des}_{vs_h}.asc'
    with open(msg_file, 'w') as fw:
        string = "date {0} \nbase hex  timestamps absolute \nno internal events logged".format(
            datetime.datetime.now().ctime())
        fw.write(string)
        fw.write('\n')
        lst = msg_all['asc-msg'].values.tolist()
        for i, signal in enumerate(lst):
            fw.write(lst[i])
            fw.write('\n')


if __name__ == "__main__":
    path = os.getcwd()
    start = time.time()
    bus_interval_time = 0.1  # GPS信号帧间隔,单位秒
    gps_date_can_id = '351'  # GPS日期CAN ID
    gps_angle_can_id = '353'  # GPS航向角CAN ID
    gps_lat_can_id = '35C'  # GPS纬度CAN ID
    gps_lon_can_id = '35D'  # GPS经度CAN ID
    vs_h = 8000  # 车速, 单位千米/小时
    src = "北京市" + "奥林匹克公园"  # 起点，可以是坐标点，如果是地址需要加上城市
    des = "上海市" + "上海市档案馆"  # 终点，可以是坐标点，如果是地址需要加上城市
    strategy = '不走高速' #高速优先  躲避拥堵  不走高速  避免收费
    elevation = 400 #海拔m
    basetime = "2020-01-17 8:05:50"  # 信号开始时间
    write_log(f'{time.strftime("%Y_%m_%d_%H_%M")}_{src}_{des}_{vs_h}')
    get_polyline(src, des)
    get_wgs84_location(src, des)
    get_gcj02_location(src, des)
    interval_after_orig_lonlat()
    get_linearr()
    open_gps_html("gps.html")
    interval_after_lonlat()
    datetime_to_msg(gps_date_can_id)
    angle_to_msg(gps_angle_can_id)
    lon_to_msg(gps_lon_can_id)
    lat_to_msg(gps_lat_can_id)
    merge_message()
    msg_to_asc()
    logger.info(f'总计用时{round((time.time() - start),4)}')
