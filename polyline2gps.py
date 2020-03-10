import requests
import math
import openpyxl
import pandas as pd
import numpy as np
import re
from geopy.distance import geodesic
import os
import time
import datetime
import logging
from functools import wraps

# global src, des, vs_h

def func_time(f):
    """
    简单记录执行时间
    :param f:
    :return:
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time: float = time.time()
        result = f(*args, **kwargs)
        end_time: float = time.time()
        logger.info(f'{f.__name__}总计用时{round((end_time - start_time),2)}')
        return result

    return wrapper


def write_log(name):
    global logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(f'{name}{time.strftime("%Y-%m-%d-%H-%M-%S")}.log')
    fh.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '[%(asctime)s][%(levelname)s] ## %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)



def gcj2wgs(location):
    # location格式如下：locations[1] = "113.923745,22.530824"
    lon = float(location[0:location.find(",")])
    lat = float(location[location.find(",") + 1:len(location)])
    a = 6378245.0  # 克拉索夫斯基椭球参数长半轴a
    ee = 0.00669342162296594323  # 克拉索夫斯基椭球参数第一偏心率平方
    PI = 3.14159265358979324  # 圆周率
    # 以下为转换公式
    x = lon - 105.0
    y = lat - 35.0
    # 经度
    dLon = 300.0 + x + 2.0 * y + 0.1 * x * x + \
        0.1 * x * y + 0.1 * math.sqrt(abs(x))
    dLon += (20.0 * math.sin(6.0 * x * PI) + 20.0 *
             math.sin(2.0 * x * PI)) * 2.0 / 3.0
    dLon += (20.0 * math.sin(x * PI) + 40.0 *
             math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    dLon += (150.0 * math.sin(x / 12.0 * PI) + 300.0 *
             math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    # 纬度
    dLat = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * \
        y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    dLat += (20.0 * math.sin(6.0 * x * PI) + 20.0 *
             math.sin(2.0 * x * PI)) * 2.0 / 3.0
    dLat += (20.0 * math.sin(y * PI) + 40.0 *
             math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    dLat += (160.0 * math.sin(y / 12.0 * PI) + 320 *
             math.sin(y * PI / 30.0)) * 2.0 / 3.0
    radLat = lat / 180.0 * PI
    magic = math.sin(radLat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * PI)
    dLon = (dLon * 180.0) / (a / sqrt_magic * math.cos(radLat) * PI)
    wgsLon = lon - dLon
    wgsLat = lat - dLat
    return wgsLon, wgsLat


# 将地址转化成坐标
@func_time
def get_loc(address):
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
    strategy = '距离最短'
    base_url = "https://restapi.amap.com/v3/direction/driving?"
    parameter = {
        'origin': origin,
        'destination': destination,
        'key': '429a22f69c6320aac18b2aa9b2aef883',
        'strategy': strategy}
    res = requests.get(base_url, parameter)
    json = res.json()
    # 获取steps字段
    steps = json['route']['paths'][0]['steps']
    # 写入excel
    book = openpyxl.Workbook()
    ws = book.active  # ws操作sheet页
    sheet = book.create_sheet('Polyline', 0)
    for i, j in enumerate(steps):
        pol = steps[i]['polyline']
        sheet.cell(i + 1, 1).value = 'polyline'
        sheet.cell(i + 1, 2).value = pol
    book.save(filename)
    book.close()


# 转成十六进制

def to_hex(wgs):
    msarc = wgs * 3600 * 1000
    hexarc = hex(int(msarc)).upper()
    hexarc2 = hexarc[2:]
    output0 = '0' * (8 - len(hexarc2)) + hexarc2
    output = output0[:2] + ' ' + output0[2:4] + \
        ' ' + output0[4:6] + ' ' + output0[6:] + ' '
    return output


# 将获取的gcjLocation数据排成一列

@func_time
def save_poly_to_excel():  # 保存坐标串数据
    coordinates = []
    wb = openpyxl.load_workbook(file_path)
    ws = wb['Polyline']
    second_column = ws['B']
    for x in range(len(second_column)):
        val = second_column[x].value
        poi = val.split(';')
        for i in poi:
            coordinates.append(i)
    ws1 = wb.create_sheet("Coordinates")
    ws1.cell(1, 1).value = "gcjLocation"     # 或写成ws1['A1'] = "gcjLocation"
    ws1.column_dimensions['A'].width = 30  # 设置A列列宽
    for k, v in enumerate(coordinates):
        ws1.cell(k + 2, 1).value = v  # 数据写入excel
    ws1.cell(1, 2).value = "wgsLocation"  # 或写成ws1['A1'] = "gcjLocation"
    ws1.column_dimensions['B'].width = 30
    for x, y in enumerate(coordinates):
        ws1.cell(x +2,2).value = str(gcj2wgs(y)).replace("(", "").replace(")", "")
    df = pd.DataFrame(ws1.values).drop_duplicates()  # 数据去重
    df.to_excel(file_path, sheet_name="Coordinates", index=False, header=False)
    # wb.save(file_path)


# 将坐标差分成经纬度

@func_time
def split_data():
    lon_wgs84 = []
    lat_wgs84 = []
    global col
    wb = openpyxl.load_workbook(file_path)
    ws1 = wb['Coordinates']
    ws1.cell(1, 3).value = "lon_wgs84"
    ws1.cell(1, 4).value = "lat_wgs84"
    col = ws1['B']
    for x in range(1, len(col)):
        vals = col[x].value
        datas = vals.split(',')
        for index, data in enumerate(datas):
            if index == 0:
                lon_wgs84.append(data)
            else:
                lat_wgs84.append(data)
    for a, b in enumerate(lon_wgs84):
        ws1.cell(a + 2, 3).value = b  # 数据写入excel
    for c, d in enumerate(lat_wgs84):
        ws1.cell(c + 2, 4).value = d
    # return lon_wgs84,lat_wgs84
    wb.save(file_path)
    wb.close()



def interpolation(loc1, loc2, a, b, vs_h):
    """
    对两个坐标点之间线性插值
    :param loc1: 坐标1
    :param loc2: 坐标2
    :param a: 坐标1的经/纬度
    :param b: 坐标2的经/纬度
    :param vs_h: 车速(km/h)
    :return: 返回插值后的坐标
    """
    n = (geodesic(loc1, loc2).m) / (vs_h * 1000 * bus_interval_time / 3600)  # m/100ms
    delta = abs((a - b) / n)  # 步长
    if a > b:
        interValue = np.arange(a, b, -delta)
    else:
        interValue = np.arange(a, b, delta)
    return interValue



@func_time
def interval_after_lonlat():  # 将插值后的经纬度值写入表中
    interLonList = []
    interLatList = []
    global vs_h
    # df = pd.read_excel(file_path).drop_duplicates().head(10)
    df = pd.read_excel(file_path).drop_duplicates()
    lat = pd.Series(df['lat_wgs84']).tolist()
    lon = pd.Series(df['lon_wgs84']).tolist()
    loc = list(zip(lat, lon))
    for i in range(len(loc)):
        if i < len(loc) - 1:
            interLon = interpolation(
                loc[i], loc[i + 1], lon[i], lon[i + 1], vs_h)
            interLonList.extend(pd.Series(interLon))
            interLat = interpolation(
                loc[i], loc[i + 1], lat[i], lat[i + 1], vs_h)
            interLatList.extend(pd.Series(interLat))
        else:
            break
    df.drop(df.columns[:], axis=1)
    df = pd.concat([pd.DataFrame({'lonValues': interLonList}), pd.DataFrame(
        {'latValues': interLatList})], axis=1)
    df.to_excel(file_path, sheet_name="Coordinates", index=False)



def heading_angle(lon_a, lat_a, lon_b, lat_b):  # 计算车辆的航向角
    y = math.sin(lon_b - lon_a) * math.cos(lat_b)
    x = math.cos(lat_a) * math.sin(lat_b) - math.sin(lat_a) * \
        math.cos(lat_b) * math.cos(lon_b - lon_a)
    # angle = math.atan2(y,x)
    angle = round(math.degrees(math.atan2(y, x)))
    if angle < 0:
        angle = angle + 360
    return angle


@func_time
def angle_list():  # 航向角列表
    angle = []
    # df = pd.read_excel(file_path).drop_duplicates().head(10)
    df = pd.read_excel(file_path).drop_duplicates()
    latList = pd.Series(df['lonValues']).tolist()
    lonList = pd.Series(df['latValues']).tolist()
    for i in range(len(latList)):
        if i < len(latList) - 1:
            angle.append(heading_angle(
                lonList[i], latList[i], lonList[i + 1], latList[i + 1]))
    angle.append(angle[i - 1])
    return angle
    # print(angle)


def series(lst, length):
    """
    生成序列，序列长度等于各列长
    :param lst: 传[0, 8, 16, 24] 或 [0,1,2,3]
    :param length: 生成序列的长度
    :return: 返回生成的序列
    """
    # 生成dec_byte6序列，列表形式 birst_id
    # a = [0, 8, 16, 24]
    a = []
    for j in range(length):
        if j <= int(length / 4):
            for i in lst:
                a.append(i)
        else:
            break
    return a[0:length]


def to_msg(lhex, can_id):
    """
    :param lhex: 传lat_hex_lon列的hex值
    :param can_id: 纬度为'35C'，经度为'35D'
    :return: msg: 十六进制的报文
    """
    msg = []
    brst_ids = [0, 8, 16, 24]
    for i in range(len(lhex)):
        dec_byte0 = int(lhex[i][0:2], 16)
        dec_byte1 = int(lhex[i][2:5], 16)
        dec_byte2 = int(lhex[i][5:8], 16)
        dec_byte3 = int(lhex[i][8:12], 16)
        # bin_byte6 =[11110000,01000000,00000000,10000000,11000000]
        dec_byte6 = series(brst_ids, len(lhex))[i]
        dec_byte4 = 0
        dec_byte5 = 0
        id = int(int(can_id, 16) / 8)
        # 公式：Checksum =(Byte[0] + Byte[1] + Byte[2] + Byte[3] + Byte[4] +
        # Byte[5] + ((Byte[6] & 0xF8) >> 3) + (CAN_ID / 8))；---01000xxx &
        # 11111000--
        checksum = dec_byte0 + dec_byte1 + dec_byte2 + \
            dec_byte3 + dec_byte4 + dec_byte5 + id + dec_byte6
        bin_lhex = int(lhex[i].replace(' ', ''), 16)
        a = '{:032b}'.format(bin_lhex)  # 补0
        b = '0000000000000000'
        c = '{:05b}'.format(dec_byte6)  # '01000'
        d = '{:011b}'.format(checksum)
        e = a + b + c + d  # 拼接成64个bit字符串
        msg_0x = hex(int(e, 2)).upper()  # 求a,b,c,d,e各二进制字符串
        # msg = '{:016b}'.format(f)
        mg = msg_0x[2:] if len(msg_0x) == 18 else'0' * \
            (18 - len(msg_0x)) + msg_0x[2:]  # 去掉0X
        msg.append(mg)
    return msg


@func_time
def datetime_to_msg(gps_time_can_id):
    signal = []
    brst_ids = [0, 1, 2, 3]
    # basetime = input("请输入当前日期时间：")
    time_series = pd.date_range(
        basetime,
        freq="100ms",
        periods=len(df)).strftime('%Y-%m-%d-%H-%M-%S-%f')
    for index, gpstime in enumerate(time_series):
        # print(index,time_series)
        year = gpstime.split('-')[0][2:]
        month = gpstime.split('-')[1]
        day = gpstime.split('-')[2]
        hour = gpstime.split('-')[3]
        min = gpstime.split('-')[4]
        sec = gpstime.split('-')[5]
        msec = gpstime.split('-')[6][0:3]
        bin_year = '{:09b}'.format(int(year))
        bin_month = '{:05b}'.format(int(month))
        bin_day = '{:06b}'.format(int(day))
        bin_hour = '{:06b}'.format(int(hour))
        bin_min = '{:07b}'.format(int(min))
        bin_sec = '{:07b}'.format(int(sec))
        bin_msec = '{:011b}'.format(int(msec))
        bin_brstid = '{:02b}'.format(series(brst_ids, len(df))[index])
        bin_datetime = bin_year + bin_month + bin_day + bin_hour + bin_min + bin_sec + bin_msec + bin_brstid
        byte0 = bin_datetime[0:8]
        byte1 = bin_datetime[8:16]
        byte2 = bin_datetime[16:24]
        byte3 = bin_datetime[24:32]
        byte4 = bin_datetime[32:40]
        byte5 = bin_datetime[40:48]
        # byte6 = bin_datetime[48:53]
        id = int(int(gps_time_can_id, 16) / 8)
        byte6 = int((bin_datetime[48:53] + '111'), 2) >> 3
        checksum = int(byte0, 2) + int(byte1, 2) + int(byte2, 2) + int(byte3, 2) + int(byte4, 2) + int(byte5, 2) + id + byte6
        bin_checksum = '{:011b}'.format(checksum)
        bin_signal = bin_year + bin_month + bin_day + bin_hour + bin_min + bin_sec + bin_msec + bin_brstid + bin_checksum
        sign_0x = hex(int(bin_signal, 2)).upper()  # 求a,b,c,d,e各二进制字符串
        sg = '0' * (18 - len(sign_0x)) + sign_0x[2:]  # 去掉0X
        signal.append(sg)
    return signal


@func_time
def angle_to_msg(gps_angle_can_id):
    anglemsg = []
    anglels = angle_list()
    # vs_h = 60 #车速
    elevation = 400  # cm,上海的海拔
    brst_ids = [0, 1, 2, 3]
    for item in range(len(anglels)):
        bin_angle = '{:013b}'.format(int((anglels[item] + 90) * 10))
        bin_vs_h = '{:08b}'.format(int(vs_h)) + '0'
        bin_elevation = '{:022b}'.format(int(100000 + elevation)) + '0000'
        bin_brstids = '{:02b}'.format(
            series(brst_ids, len(anglels))[item]) + '000'
        bin_heading = bin_angle + bin_vs_h + bin_elevation + bin_brstids
        byte0 = bin_heading[0:8]
        byte1 = bin_heading[8:16]
        byte2 = bin_heading[16:24]
        byte3 = bin_heading[24:32]
        byte4 = bin_heading[32:40]
        byte5 = bin_heading[40:48]
        id = int(int(gps_angle_can_id, 16) / 8)
        byte6 = int((bin_heading[48:53] + '111'), 2) >> 3
        checksum = int(byte0, 2) + int(byte1, 2) + int(byte2, 2) + \
            int(byte3, 2) + int(byte4, 2) + int(byte5, 2) + id + byte6
        bin_checksum = '{:011b}'.format(checksum)
        bin_anglemsg = bin_angle + bin_vs_h + bin_elevation + bin_brstids + bin_checksum
        anglemsg_0x = hex(int(bin_anglemsg, 2)).upper()  # 求a,b,c,d,e各二进制字符串
        ag = '0' * (18 - len(anglemsg_0x)) + anglemsg_0x[2:]  # 去掉0X
        anglemsg.append(ag)
    # print(anglemsg)
    return anglemsg


@func_time
def insert_col_to_excel():
    global df
    global message
    lon_hex = []
    lat_hex = []
    df = pd.read_excel(file_path, sheet_name="Coordinates")  # Coordinates
    # writer = pd.ExcelWriter(file_path,sheet_name = "Sheet1")
    lon_hex = [to_hex(i) for i in df['lonValues']]  # 返回lon_hex列表
    lat_hex = [to_hex(j) for j in df['latValues']]  # 返回lat_hex列表
    df['time_date'] = [format(i / 10, '0.6f') for i in range(len(df))]  # "351"
    df['time_angle'] = [format((0.001 + i / 10),'0.6f') for i in range(len(df))]  # "353"
    df['time_lat'] = [format((0.002 + i / 10),'0.6f') for i in range(len(df))]  # "35C"
    df['time_lon'] = [format((0.003 + i / 10),'0.6f') for i in range(len(df))]  # "35D"
    df['CAN_number'] = [0] * len(df)
    df['canid_date'] = [gps_date_can_id] * int((len(df)))
    df['canid_angle'] = [gps_angle_can_id] * int((len(df)))
    df['canid_lat'] = [gps_angle_can_id] * int((len(df)))
    df['canid_lon'] = [gps_lat_can_id] * int((len(df)))
    df['Frame_direction'] = ['Rx'] * len(df)
    df['D'] = ['d'] * len(df)
    df['DLC'] = [8] * len(df)
    msg_date = datetime_to_msg(gps_date_can_id)
    msg_angle = angle_to_msg(gps_angle_can_id)
    msg_lat = to_msg(lat_hex, gps_lat_can_id)
    df['msg_lat'] = msg_lat   # print(df['msg_lat'+'i'])
    msg_lon = to_msg(lon_hex, gps_lon_can_id)
    df['msg_lon'] = msg_lon
    msgDate = [(re.sub('(..)', r'\1 ', msg_date[i]).rstrip()) for i in range(len(df))]
    df['MsgDate'] = msgDate
    df['MsgAngle'] = [(re.sub('(..)', r'\1 ',msg_angle[i]).rstrip()) for i in range(len(df))]
    msgLat = [(re.sub('(..)', r'\1 ', msg_lat[i]).rstrip()) for i in range(len(df))]  # 06A1ED0C0000C223处理成06 A1 ED 0C 00 00 C2 23
    df['MsgLat'] = msgLat
    msgLon = [(re.sub('(..)', r'\1 ', msg_lon[i]).rstrip()) for i in range(len(df))]
    df['MsgLon'] = msgLon
    # msgLon= "".join([" " + e if index > 0 and index % 2 == 0 else e for index, e in enumerate(msg_lon[i])])
    # 合并列
    df['Message_date'] = df['time_date'].map(str) + ' ' + df['CAN_number'].map(str) + ' ' + df['canid_date'] + \
        '             ' + df['Frame_direction'] + '  ' + df['D'] + ' ' + df['DLC'].map(str) + ' ' + df['MsgDate']
    df['Message_angle'] = df['time_angle'].map(str) + ' ' + df['CAN_number'].map(str) + ' ' + df['canid_angle'] + \
        '             ' + df['Frame_direction'] + '  ' + df['D'] + ' ' + df['DLC'].map(str) + ' ' + df['MsgAngle']
    df['Message_lat'] = df['time_lat'].map(str) + ' ' + df['CAN_number'].map(str) + ' ' + df['canid_lat'] + \
        '             ' + df['Frame_direction'] + '  ' + df['D'] + ' ' + df['DLC'].map(str) + ' ' + df['MsgLat']
    df['Message_lon'] = df['time_lon'].map(str) + ' ' + df['CAN_number'].map(str) + ' ' + df['canid_lon'] + \
        '             ' + df['Frame_direction'] + '  ' + df['D'] + ' ' + df['DLC'].map(str) + ' ' + df['MsgLon']
    df.to_excel(file_path, sheet_name="Coordinates", index=False)


@func_time
def merge_message():
    # 删除其他列，合并Message_lat 和Message_lon
    df0 = pd.read_excel(file_path)
    df = df0.drop(df0.columns[:-4], axis=1)  # 删除其他列，保留Message_lat 和Message_lon
    df1 = pd.DataFrame(df.values.ravel('c'), columns=['Message'])
    pd.concat([df, df1], axis=1).fillna('')
    df1.to_excel(file_path, index=False)


@func_time
def msg_to_asc():
    msg_file = f'{time.strftime("%Y-%m-%d-%H-%M")}-{src}-{des}-{vs_h}.asc'
    with open(msg_file, 'w') as fw:
        string = "date {0} \nbase hex  timestamps absolute \nno internal events logged".format(
            datetime.datetime.now().ctime())
        fw.write(string)
        fw.write('\n')
        df = pd.read_excel(file_path)
        col = df['Message']
        lst = pd.Series(col).tolist()
        for i, signal in enumerate(lst):
            fw.write(lst[i])
            fw.write('\n')


if __name__ == "__main__":
    filename = "高德地图数据采集.xlsx"
    path = os.getcwd()
    file_path = os.path.join(path, filename)
    start = time.time()
    bus_interval_time = 0.1  # GPS信号帧间隔,单位秒
    gps_angle_can_id = '351'  # GPS航向角CAN ID
    gps_date_can_id = '353'  # GPS日期CAN ID
    gps_lat_can_id = '35C'  # GPS纬度CAN ID
    gps_lon_can_id = '35D'  # GPS经度CAN ID
    vs_h = 60  # 车速, 单位千米/小时
    src = "上海市" + "巨峰路2199号"  # 起点，可以是坐标点，如果是地址需要加上城市
    des = "上海市" + "龙东大道3999号"  # 终点，可以是坐标点，如果是地址需要加上城市
    basetime = "2020-01-17 8:05:50"  # 信号开始时间
    write_log(f'{time.strftime("%Y-%m-%d-%H-%M")}-{src}-{des}-{vs_h}')
    get_polyline(src, des)
    save_poly_to_excel()
    split_data()
    interval_after_lonlat()
    insert_col_to_excel()
    merge_message()
    msg_to_asc()
    logger.info(f'总计用时{round((time.time() - start),4)}')
