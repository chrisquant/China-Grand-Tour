"""中国四大环线。逐日表来自总控版，日期按 2028 年东线起排。"""

import re
from datetime import date, timedelta
from pathlib import Path

MD_PATH = Path(__file__).with_name("00_中国四大环线自驾全书（总控版）.md")
TRIAL_PATH = Path(__file__).with_name("济源到上海_2027春节.md")
JIYUAN = "济源"

# 书中概数。页面上的天数和里程以逐日表为准，这两列只作对照。
LOOP_META = [
    {
        "id": "east", "mark": "🡆", "name": "东线", "theme": "万里海疆·江南名山",
        "start": date(2028, 4, 8), "color": "#2F6F6A",
        "book_days": 43, "book_km": 7000, "budget_low": 28000, "budget_high": 38000,
        "temp_low": 14, "temp_high": 24,
        "blurb": "路网密、补给近，2028 年 4–5 月先走。泰山、胶东海岸、江南和黄山。",
        "shift_note": "",
    },
    {
        "id": "north", "mark": "🡅", "name": "北线", "theme": "长城内外·草原林海",
        "start": date(2028, 7, 15), "color": "#C45C26",
        "book_days": 48, "book_km": 8800, "budget_low": 28000, "budget_high": 38000,
        "temp_low": 12, "temp_high": 28,
        "blurb": "2028 年 7 月 15 日出，9 月 4 日回。壶口、晋北、坝上、呼伦贝尔、漠河、长白山，从山海关入关。",
        "shift_note": "",
    },
    {
        "id": "south", "mark": "🡇", "name": "南线", "theme": "巴山蜀水·彩云秘境",
        "start": date(2028, 9, 12), "color": "#FF4D6D",
        "book_days": 68, "book_km": 12000, "budget_low": 42000, "budget_high": 60000,
        "temp_low": 8, "temp_high": 28,
        "blurb": "北线结束后 9 月 12 日出发。武当、张家界、九寨、稻城、梅里、桂林、海南，粤北回济源。",
        "shift_note": "北线占到 9 月初，南线 9 月 12 日才出发。川西落在 10 月上旬，比书里「9 月底前走完川西」晚一截；遇早雪就从成都或新都桥下撤。",
    },
    {
        "id": "west", "mark": "🡄", "name": "西线", "theme": "丝路戈壁·天山南北",
        "start": date(2029, 8, 25), "color": "#C4A35A",
        "book_days": 49, "book_km": 12000, "budget_low": 32000, "budget_high": 48000,
        "temp_low": 5, "temp_high": 24,
        "blurb": "2029 年 8 月 25 日出。喀纳斯 9 月 17 日到，独库 9 月 26–27 日，额济纳 10 月 3 日，10 月 8 日回济源。",
        "shift_note": "",
    },
]

# 过夜点坐标：纬度、经度、海拔（米）。名字与逐日表「住宿」列去掉括号后一致。
COORDS = {
    "济源": (35.09, 112.60, 140),
    "壶口镇": (36.15, 110.45, 450),
    "平遥": (37.20, 112.18, 750),
    "平遥古城外": (37.20, 112.18, 750),
    "绵山/介休": (36.97, 111.95, 900),
    "太原": (37.87, 112.55, 800),
    "台怀镇": (39.02, 113.59, 1700),
    "代县": (39.07, 112.96, 860),
    "应县": (39.56, 113.19, 1000),
    "浑源": (39.70, 113.69, 1100),
    "大同": (40.08, 113.30, 1040),
    "火山附近": (41.57, 113.15, 1400),
    "黄花沟": (41.12, 112.62, 2000),
    "张北": (41.16, 114.72, 1400),
    "张家口": (40.77, 114.89, 720),
    "承德": (40.95, 117.96, 350),
    "达里湖": (43.27, 116.63, 1226),
    "石林": (43.99, 117.62, 1600),
    "乌兰布统": (42.48, 117.22, 1400),
    "乌兰浩特": (46.07, 122.07, 280),
    "阿尔山": (47.18, 119.94, 1000),
    "海拉尔": (49.21, 119.74, 610),
    "额尔古纳": (50.24, 120.18, 580),
    "室韦": (51.35, 120.05, 500),
    "临江": (51.64, 120.72, 550),
    "莫尔道嘎": (51.55, 120.82, 700),
    "满洲里": (49.60, 117.38, 660),
    "黑山头": (50.22, 119.33, 600),
    "满归": (52.03, 122.07, 700),
    "北极村": (53.48, 122.36, 300),
    "北红村": (53.31, 122.36, 300),
    "黑河": (50.25, 127.53, 150),
    "五大连池": (48.65, 126.15, 300),
    "伊春": (47.73, 128.90, 240),
    "哈尔滨": (45.76, 126.64, 150),
    "镜泊湖": (44.05, 128.94, 350),
    "延吉": (42.89, 129.51, 180),
    "沈阳": (41.81, 123.43, 50),
    "本溪/丹东": (41.30, 123.77, 120),
    "丹东": (40.13, 124.39, 10),
    "大连": (38.91, 121.61, 30),
    "北戴河": (39.83, 119.52, 10),
    "曲阜": (35.60, 116.99, 60),
    "泰山山顶": (36.25, 117.10, 1545),
    "济南": (36.65, 117.12, 30),
    "青岛": (36.07, 120.38, 20),
    "威海": (37.51, 122.12, 40),
    "烟台/蓬莱": (37.81, 120.76, 20),
    "连云港": (34.60, 119.22, 10),
    "开封": (34.80, 114.31, 75),
    "徐州": (34.26, 117.18, 40),
    "扬州": (32.39, 119.41, 10),
    "南京": (32.06, 118.80, 20),
    "无锡": (31.49, 120.31, 10),
    "苏州": (31.30, 120.59, 5),
    "上海": (31.23, 121.47, 5),
    "乌镇": (30.75, 120.49, 5),
    "杭州": (30.27, 120.16, 10),
    "千岛湖": (29.60, 119.04, 110),
    "普陀": (29.95, 122.39, 10),
    "普陀山": (30.00, 122.38, 50),
    "天台": (29.14, 121.03, 50),
    "雁荡山": (28.37, 121.06, 200),
    "太姥山": (27.13, 120.18, 50),
    "福州": (26.07, 119.30, 20),
    "泉州": (24.87, 118.68, 20),
    "厦门": (24.48, 118.09, 20),
    "南靖": (24.65, 117.36, 300),
    "武夷山": (27.76, 118.03, 200),
    "三清山": (28.91, 118.07, 1000),
    "婺源": (29.25, 117.86, 120),
    "牯岭": (29.57, 115.98, 1165),
    "庐山": (29.57, 115.98, 1165),
    "汤口": (30.13, 118.17, 450),
    "老君山": (33.75, 111.64, 1200),
    "武当山": (32.40, 111.00, 200),
    "木鱼": (31.47, 110.40, 1200),
    "恩施": (30.28, 109.49, 400),
    "鹤峰/恩施": (29.89, 110.03, 800),
    "武陵源": (29.33, 110.55, 500),
    "凤凰": (27.95, 109.60, 350),
    "江口": (27.70, 108.84, 400),
    "武隆": (29.33, 107.76, 400),
    "重庆": (29.56, 106.55, 240),
    "成都": (30.57, 104.07, 500),
    "峨眉山": (29.52, 103.33, 800),
    "川主寺": (32.79, 103.62, 3000),
    "沟口": (33.26, 103.92, 2000),
    "若尔盖": (33.58, 102.96, 3500),
    "扎尕那": (34.14, 103.18, 3200),
    "四姑娘山": (31.11, 102.85, 3200),
    "丹巴": (30.88, 101.89, 1800),
    "新都桥": (30.05, 101.50, 3460),
    "理塘": (29.99, 100.27, 3950),
    "亚丁": (28.43, 100.35, 3900),
    "得荣": (28.71, 99.29, 2400),
    "飞来寺": (28.44, 98.88, 3400),
    "雨崩/德钦": (28.46, 98.92, 3300),
    "香格里拉": (27.83, 99.71, 3280),
    "丽江": (26.86, 100.23, 2400),
    "泸沽湖": (27.70, 100.78, 2690),
    "大理": (25.61, 100.27, 2000),
    "腾冲": (25.02, 98.49, 1650),
    "昆明": (25.04, 102.71, 1900),
    "普洱": (22.83, 100.97, 1300),
    "景洪": (22.00, 100.80, 550),
    "罗平": (24.88, 104.31, 1500),
    "安顺": (26.25, 105.95, 1400),
    "织金": (26.66, 105.77, 1300),
    "荔波": (25.41, 107.89, 400),
    "西江": (26.50, 108.17, 800),
    "龙脊": (25.80, 110.12, 800),
    "桂林": (25.27, 110.29, 150),
    "阳朔": (24.78, 110.50, 110),
    "大新": (22.85, 106.72, 300),
    "北海": (21.48, 109.12, 20),
    "海口": (20.04, 110.20, 10),
    "博鳌": (19.16, 110.58, 5),
    "陵水": (18.51, 110.04, 10),
    "三亚": (18.25, 109.51, 10),
    "尖峰岭": (18.71, 108.87, 800),
    "儋州": (19.52, 109.58, 20),
    "湛江": (21.27, 110.36, 20),
    "肇庆": (23.05, 112.47, 20),
    "韶关": (24.81, 113.60, 70),
    "南昌": (28.68, 115.86, 25),
    "华阴": (34.57, 110.09, 350),
    "西安": (34.34, 108.94, 400),
    "宝鸡": (34.36, 107.24, 570),
    "天水": (34.58, 105.72, 1100),
    "兰州": (36.06, 103.83, 1520),
    "西宁/湟源": (36.62, 101.78, 2275),
    "黑马河": (36.72, 99.78, 3200),
    "茶卡": (36.70, 99.08, 3050),
    "茶卡/德令哈": (37.20, 98.20, 3000),
    "德令哈": (37.37, 97.36, 2980),
    "大柴旦": (37.85, 95.37, 3100),
    "水上雅丹": (38.42, 93.08, 2750),
    "敦煌": (40.14, 94.66, 1138),
    "哈密": (42.82, 93.52, 750),
    "巴里坤": (43.60, 93.02, 1650),
    "吐鲁番": (42.95, 89.19, 30),
    "乌鲁木齐": (43.83, 87.62, 800),
    "阜康/富蕴": (43.88, 88.12, 1910),
    "可可托海": (47.21, 89.82, 1200),
    "布尔津": (47.70, 86.86, 470),
    "喀纳斯": (48.70, 87.03, 1370),
    "喀纳斯/禾木": (48.70, 87.03, 1370),
    "禾木": (48.57, 87.43, 1120),
    "乌尔禾": (46.09, 85.75, 400),
    "赛湖畔": (44.60, 81.15, 2073),
    "伊宁": (43.92, 81.32, 660),
    "特克斯": (43.22, 81.84, 1200),
    "那拉提": (43.32, 84.02, 1800),
    "巴音布鲁克": (43.03, 84.14, 2500),
    "巴音布鲁克/库车": (43.03, 84.14, 2500),
    "库车": (41.72, 82.96, 1070),
    "阿克苏": (41.17, 80.26, 1100),
    "喀什": (39.47, 75.99, 1280),
    "酒泉/嘉峪关": (39.77, 98.29, 1600),
    "达来呼布": (41.95, 101.07, 930),
    "额济纳": (42.10, 101.15, 930),
    "银川": (38.49, 106.23, 1110),
    "中卫": (37.51, 105.20, 1220),
    "营口": (40.67, 122.24, 10),
    "锦州": (41.10, 121.13, 20),
    "葫芦岛": (40.71, 120.84, 20),
    "山海关": (40.00, 119.75, 20),
    "天津": (39.13, 117.20, 5),
    "白洋淀": (38.84, 116.03, 10),
    "宁波": (29.87, 121.55, 10),
    "宏村": (29.99, 117.99, 200),
    "九华山": (30.48, 117.80, 600),
    "武汉": (30.59, 114.31, 25),
    "南阳": (32.99, 112.53, 130),
    "襄阳": (32.01, 112.14, 70),
    "合肥": (31.82, 117.23, 30),
    "延安": (36.59, 109.49, 960),
    "壶口": (36.15, 110.45, 450),
}

# 直线会切海或抄近路时，插入这些不过夜的点。
BENDS = {
    ("大连", "北戴河"): ["营口", "锦州", "葫芦岛", "山海关"],
    ("北戴河", "济源"): ["天津", "白洋淀"],
    ("千岛湖", "普陀"): ["杭州", "宁波"],
    ("普陀山", "天台"): ["宁波"],
    ("汤口", "济源"): ["宏村", "九华山"],
    ("南昌", "济源"): ["武汉"],
    ("中卫", "济源"): ["延安", "壶口"],
    ("喀什", "酒泉/嘉峪关"): ["阿克苏", "库车", "吐鲁番", "哈密"],
}
FERRY = {("北海", "海口"), ("海口", "湛江")}

RED_LINES = [
    {"情形": "高原高反", "红线": "头痛、气短明显", "动作": "下撤到低海拔，不硬撑"},
    {"情形": "戈壁/偏远", "红线": "油箱或饮水见底", "动作": "见加油站就加满，备双倍水和食物"},
    {"情形": "台风", "红线": "东南沿海 7–9 月遇预警", "动作": "就地停 2–3 天"},
    {"情形": "雨雪封路", "红线": "独库或山口当天不通", "动作": "等待或绕行，不冒险"},
    {"情形": "车辆故障", "红线": "影响安全或续航", "动作": "当日停驶，用应急金"},
    {"情形": "行程落后", "红线": "超过 3 天", "动作": "取消非必要停留，保主线"},
    {"情形": "无信号", "红线": "川西、戈壁、大兴安岭", "动作": "不单车偏离公路，每日报平安"},
    {"情形": "超支", "红线": "超目标 10%", "动作": "削减住宿、门票和绕行"},
]

WEEKLY_RULES = [
    "日均 200–250 公里。草原、戈壁、海岸当天只设一个目标，天黑前 1 小时收车。",
    "每周至少休 1–2 天：洗衣、补给、车检、整理照片。",
    "风景好就多住 2–3 天。落后就砍后面的城市，不砍自然风光。",
    "超过 400 公里的日子提前确认油站、住宿和备用路线。不走夜路。",
    "出发前车辆、证件、保险不达标，不出发。应急金不主动消费。",
]

GEAR = [
    "4 条 AT 胎加 1 条同规格备胎；补胎套装、电动充气泵、胎压计。",
    "机油、变速箱油、刹车油、防冻液；增程器、电池、底盘护板、刹车、悬挂、冷却。",
    "拖车绳、U 形钩、搭电线、保险丝、继电器、防滑链、工具箱、千斤顶。",
    "每人反光背心、灭火器、三角警示牌、急救包、头灯、保温毯。",
    "被褥、睡袋、车载冰箱、便携灶具、储水桶。高原段备常用药和氧气。",
    "离线地图。川西、戈壁、大兴安岭建议卫星电话或北斗短报文。",
    "满载试车不少于 500 公里。证件、保险、行程单：原件、复印件、云端、U 盘四套。",
]

# 相对出发日的倒排。东线 4 月 8 日对应原来的绝对日期。
PREP_STEPS = [
    {"必须完成": "定下出发日、预算和同行人", "验收": "这条线的主线冻结", "start_before": 91, "end_before": 60},
    {"必须完成": "轮胎、油液、底盘和备件", "验收": "满载试车 500 公里", "start_before": 60, "end_before": 43},
    {"必须完成": "保险、装备、常用药", "验收": "证件和装备到位", "start_before": 48, "end_before": 29},
    {"必须完成": "首段住宿和旺季订单", "验收": "订单保存在云端", "start_before": 29, "end_before": 14},
    {"必须完成": "体检、离线地图、四套文件", "验收": "纸质卡片写好紧急号码", "start_before": 14, "end_before": 7},
    {"必须完成": "最终车检、加油、装行李", "验收": "全部达标才出发", "start_before": 3, "end_before": 1},
]
MONTH_HIGH = {1: 7, 2: 10, 3: 16, 4: 22, 5: 27, 6: 31, 7: 33, 8: 32, 9: 27, 10: 21, 11: 14, 12: 8}


def _canon(stay):
    return re.sub(r"（.*?）", "", stay).strip()


def _km(text):
    nums = re.findall(r"\d+", text.replace(",", ""))
    return int(nums[0]) if nums else 0


def _blurb_map(block):
    out = {}
    for line in block.splitlines():
        m = re.match(r"^- \*\*(.+?)\*\*[：:](.+)$", line.strip())
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def _parse_md(text):
    body = text.split("# 第二部分", 1)[1]
    chunks = re.split(r"(?=^# [🡅🡆🡇🡄] )", body, flags=re.M)
    found = {}
    for chunk in chunks:
        head = re.match(r"^# ([🡅🡆🡇🡄]) .+?详解 · (.+)$", chunk, re.M)
        if not head:
            continue
        mark = head.group(1)
        notes = []
        note_m = re.search(r"^## .+注意事项\s*$([\s\S]*?)(?=^# |\Z)", chunk, re.M)
        seg_src = chunk
        if note_m:
            notes = [re.sub(r"^\s*-\s*", "", x).strip() for x in note_m.group(1).splitlines() if x.strip().startswith("-")]
            seg_src = chunk[:note_m.start()]
        route_m = re.search(r"## 路线总览\s*```[^\n]*\n([\s\S]*?)```", seg_src)
        route_text = re.sub(r"\s+", " ", route_m.group(1)).strip() if route_m else ""
        segments = []
        for sm in re.finditer(r"^## (第[一二三四五六七八九十]+段)：(.+?)（D(\d+)–D(\d+)）\s*$", seg_src, re.M):
            start = sm.end()
            nxt = re.search(r"^## 第", seg_src[start:], re.M)
            block = seg_src[start:start + nxt.start()] if nxt else seg_src[start:]
            days = []
            for row in re.finditer(r"^\| (D\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|", block, re.M):
                days.append({
                    "n": int(row.group(1)[1:]),
                    "route": row.group(2).strip(),
                    "km": _km(row.group(3)),
                    "stay": _canon(row.group(4).strip()),
                    "plan": row.group(5).strip(),
                })
            segments.append({
                "name": sm.group(2).strip(),
                "d0": int(sm.group(3)),
                "d1": int(sm.group(4)),
                "days": days,
                "blurbs": _blurb_map(block),
            })
        found[mark] = {"route_text": route_text, "notes": notes, "segments": segments}
    return found


def _point(name):
    if name not in COORDS:
        raise KeyError(name)
    lat, lon, elev = COORDS[name]
    return {"name": name, "lat": lat, "lon": lon, "elev": elev}


def _legs(stays, bends=None):
    """stays 是按时间排好的过夜点，含重复。返回不含重复点的折线。"""
    bend_map = BENDS if bends is None else bends
    collapsed = []
    for s in stays:
        if collapsed and collapsed[-1]["name"] == s["name"]:
            collapsed[-1]["until"] = s["date"]
            collapsed[-1]["days"] += 1
            continue
        collapsed.append({**_point(s["name"]), "date": s["date"], "until": s["date"], "days": 1, "plan": s["plan"], "n": s["n"]})
    legs = []
    for a, b in zip(collapsed, collapsed[1:]):
        kind = "ferry" if (a["name"], b["name"]) in FERRY else "road"
        mids = [_point(x) for x in bend_map.get((a["name"], b["name"]), [])]
        legs.append({"a": a, "b": b, "kind": kind, "mids": mids})
    return collapsed, legs


def _parse_trip(text):
    notes = []
    note_m = re.search(r"^## .+注意事项\s*$([\s\S]*?)(?=^# |\Z)", text, re.M)
    seg_src = text
    if note_m:
        notes = [re.sub(r"^\s*-\s*", "", x).strip() for x in note_m.group(1).splitlines() if x.strip().startswith("-")]
        seg_src = text[:note_m.start()]
    route_m = re.search(r"## 路线总览\s*```[^\n]*\n([\s\S]*?)```", seg_src)
    route_text = re.sub(r"\s+", " ", route_m.group(1)).strip() if route_m else ""
    segments = []
    for sm in re.finditer(r"^## (第[一二三四五六七八九十]+段)：(.+?)（D(\d+)–D(\d+)）\s*$", seg_src, re.M):
        start = sm.end()
        nxt = re.search(r"^## 第", seg_src[start:], re.M)
        block = seg_src[start:start + nxt.start()] if nxt else seg_src[start:]
        days = []
        for row in re.finditer(r"^\| (D\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|", block, re.M):
            days.append({
                "n": int(row.group(1)[1:]),
                "route": row.group(2).strip(),
                "km": _km(row.group(3)),
                "stay": _canon(row.group(4).strip()),
                "plan": row.group(5).strip(),
            })
        segments.append({
            "name": sm.group(2).strip(),
            "d0": int(sm.group(3)),
            "d1": int(sm.group(4)),
            "days": days,
            "blurbs": _blurb_map(block),
        })
    return {"route_text": route_text, "notes": notes, "segments": segments}


def _assemble(meta, src, bends=None):
    days = []
    for seg in src["segments"]:
        for row in seg["days"]:
            item = {**row, "date": meta["start"] + timedelta(days=row["n"] - 1), "segment": seg["name"]}
            item.update(_point(row["stay"]))
            days.append(item)
    if not days or days[0]["n"] != 1:
        raise ValueError(meta["name"])
    if [d["n"] for d in days] != list(range(1, len(days) + 1)):
        raise ValueError(meta["name"] + " 天数不连续")
    for seg in src["segments"]:
        got = [d["n"] for d in seg["days"]]
        if got != list(range(seg["d0"], seg["d1"] + 1)):
            raise ValueError(f"{meta['name']} {seg['name']} 日序 {got}")
    stay_rows = [{"name": JIYUAN, "date": meta["start"], "plan": "出发", "n": 0}]
    if days[0]["stay"] != JIYUAN:
        stay_rows.extend(days)
    else:
        stay_rows = days
    if stay_rows[0]["name"] != JIYUAN:
        stay_rows.insert(0, {"name": JIYUAN, "date": meta["start"], "plan": "出发", "n": 0})
    stops, legs = _legs(stay_rows, bends)
    return {
        **meta,
        "end": days[-1]["date"],
        "days": days,
        "segments": src["segments"],
        "notes": src["notes"],
        "route_text": src["route_text"],
        "stops": stops,
        "legs": legs,
        "km": sum(d["km"] for d in days),
    }


def _build():
    parsed = _parse_md(MD_PATH.read_text(encoding="utf-8"))
    return [_assemble(meta, parsed[meta["mark"]]) for meta in LOOP_META]


def _build_trial():
    meta = {
        "id": "jiyuan-shanghai", "mark": "", "name": "春节出游", "theme": "济源到上海",
        "start": date(2027, 2, 6), "color": "#5B8DEF",
        "book_days": 8, "book_km": 1680, "budget_low": 8650, "budget_high": 8650,
        "temp_low": 2, "temp_high": 12,
        "blurb": "2027 年正月初一下午出发，初八在上海结束。南下经武汉，合肥只吃饭。",
        "shift_note": "初五武汉经合肥到南京，大约 580 公里。遇雪就在襄阳或多停武汉，苏州改成当天路过，仍初八到上海。",
        "label_tier": {"济源": 0, "南阳": 0, "襄阳": 0, "武汉": 0, "合肥": 0, "南京": 0, "苏州": 0, "上海": 0},
        "list_sights": True,
        "budget_note": "一人一车，都是大约数。另留 2000 元应急，不放进合计。",
        "budget_rows": [
            {"项目": "油费", "大约": 1300, "说明": "1680 公里，百公里约 8 升"},
            {"项目": "南阳 1 晚", "大约": 400, "说明": "市区，方便第二天早上去卧龙岗"},
            {"项目": "襄阳 1 晚", "大约": 400, "说明": "古城附近"},
            {"项目": "武汉 2 晚", "大约": 1300, "说明": "江边或江汉路一带"},
            {"项目": "南京 2 晚", "大约": 1500, "说明": "城南，晚上能走路去夫子庙、老门东"},
            {"项目": "苏州 1 晚", "大约": 700, "说明": "平江路或拙政园附近"},
            {"项目": "上海 1 晚", "大约": 1000, "说明": "人民广场或外滩附近，车停酒店"},
            {"项目": "吃饭 8 天", "大约": 1200, "说明": "每天约 150 元，含合肥那顿午饭"},
            {"项目": "门票", "大约": 450, "说明": "卧龙岗、古隆中、城墙、黄鹤楼、总统府、拙政园、豫园。省博和中山陵免费"},
            {"项目": "市内和停车", "大约": 400, "说明": "酒店停车，南京出租，上海地铁或出租"},
        ],
    }
    loop = _assemble(meta, _parse_trip(TRIAL_PATH.read_text(encoding="utf-8")), {("武汉", "南京"): ["合肥"]})
    loop["sights"] = _trial_sights(loop)
    return loop


# 景点名 → 坐标。名字要和春节出游 markdown 的地点介绍一致。0 档只画点，放大五档才写名字。
_SIGHT_COORDS = {
    "白河": (32.997, 112.548),
    "府衙": (33.003, 112.530),
    "卧龙岗": (32.981, 112.505),
    "古隆中": (31.999, 112.076),
    "临汉门": (32.016, 112.154),
    "夫人城": (32.026, 112.160),
    "北街": (32.019, 112.151),
    "长江大桥": (30.549, 114.288),
    "黄鹤楼": (30.546, 114.303),
    "户部巷": (30.547, 114.299),
    "省博物馆": (30.562, 114.364),
    "东湖听涛": (30.555, 114.371),
    "黎黄陂路": (30.592, 114.301),
    "江汉路": (30.584, 114.294),
    "夫子庙": (32.022, 118.790),
    "中山陵": (32.061, 118.848),
    "总统府": (32.044, 118.797),
    "玄武门": (32.070, 118.797),
    "老门东": (32.014, 118.788),
    "拙政园": (31.324, 120.629),
    "平江路": (31.317, 120.633),
    "豫园": (31.227, 121.492),
    "外滩": (31.240, 121.490),
}


def _trial_sights(loop):
    sights = []
    for seg in loop["segments"]:
        for name, text in seg["blurbs"].items():
            if name not in _SIGHT_COORDS:
                continue
            lat, lon = _SIGHT_COORDS[name]
            sights.append({"name": name, "lat": lat, "lon": lon, "segment": seg["name"], "text": text})
    missing = [name for name in _SIGHT_COORDS if name not in {s["name"] for s in sights}]
    if missing:
        raise ValueError("景点没有写进介绍：" + "、".join(missing))
    return sights


LOOPS = _build()
TRIAL = _build_trial()
BY_ID = {c["id"]: c for c in LOOPS}
TRIP_START = LOOPS[0]["start"]
TRIP_END = LOOPS[-1]["end"]


def prep_for(loop):
    """这条线出发前的倒排，最后一项落在出发前一天。"""
    depart = loop["start"]
    rows = []
    for step in PREP_STEPS:
        start = depart - timedelta(days=step["start_before"])
        end = depart - timedelta(days=step["end_before"])
        rows.append({
            "必须完成": step["必须完成"],
            "验收": step["验收"],
            "start": start,
            "end": end,
            "截止": f"{end.month}月{end.day}日",
        })
    return rows


def daytime_range(lat, lon, elev, month):
    """这一月、这一海拔的白天大致区间，不是预报。"""
    high = MONTH_HIGH[month] - (lat - 33) * 0.55 - max(elev, 0) / 1000 * 4.0
    if lat < 23:
        high += (23 - lat) * 0.7
    if elev < 200 and lon > 118:
        high += 1.5
    if lon < 96 and elev < 1600 and month in (7, 8, 9):
        high += 3
    high = int(max(-5, min(38, round(high))))
    span = 6 if elev >= 2500 else 7 if elev >= 800 else 6
    return max(-8, high - span), high


PREP = prep_for(LOOPS[0])


def loop_by_id(lid):
    if lid == TRIAL["id"]:
        return TRIAL
    return BY_ID[lid]


def loop_on(day):
    for c in LOOPS:
        if c["start"] <= day <= c["end"]:
            return c
    return None


def day_row(loop, day):
    for row in loop["days"]:
        if row["date"] == day:
            return row
    return None


def locate(day):
    """当晚位置。空档和出发前都在济源。"""
    home = {**_point(JIYUAN), "loop": None, "loop_name": "济源", "status": "休整", "plan": "人在济源", "along_km": 0}
    if day < TRIP_START:
        home["status"] = "尚未出发"
        return home
    if day > TRIP_END:
        home["status"] = "四线走完"
        home["along_km"] = sum(c["km"] for c in LOOPS)
        return home
    passed = sum(c["km"] for c in LOOPS if c["end"] < day)
    loop = loop_on(day)
    if loop is None:
        nxt = next(c for c in LOOPS if c["start"] > day)
        home["status"] = "休整"
        home["plan"] = f"下一程是{nxt['name']}，{nxt['start'].isoformat()}出发"
        home["along_km"] = passed
        return home
    row = day_row(loop, day)
    return {
        "name": row["stay"],
        "lat": row["lat"],
        "lon": row["lon"],
        "elev": row["elev"],
        "loop": loop["id"],
        "loop_name": loop["name"],
        "status": loop["name"],
        "plan": row["plan"],
        "route": row["route"],
        "along_km": passed + sum(d["km"] for d in loop["days"] if d["date"] <= day),
        "n": row["n"],
        "segment": row["segment"],
    }


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def segment_blurbs(loop, segment_name=None):
    out = []
    for seg in loop["segments"]:
        if segment_name and seg["name"] != segment_name:
            continue
        for name, text in seg["blurbs"].items():
            out.append({"分段": seg["name"], "地点": name, "介绍": text})
    return out


def card_text(loop, stay, plan):
    hits = []
    for seg in loop["segments"]:
        for name, text in seg["blurbs"].items():
            if name in stay or stay.split("/")[0] in name or any(part and part in name for part in re.split(r"[/→]", stay)):
                hits.append(text if loop.get("list_sights") else f"{name}：{text}")
    if loop.get("list_sights"):
        day_plans = [d["plan"] for d in loop["days"] if d["stay"] == stay]
        if not day_plans:
            day_plans = [d["plan"] for d in loop["days"] if stay in d["route"]]
        lines = []
        for text in hits:
            head, _, tail = text.partition("。")
            if head.startswith("景点："):
                lines.append(head)
                if tail:
                    lines.append(tail)
            else:
                lines.append(text)
        lines.extend(day_plans)
        if not lines:
            lines.append("从家里出发，不安排景点。" if stay == "济源" else plan)
        return " ".join(lines)
    if hits:
        return plan + " " + " ".join(hits[:2])
    return plan


if __name__ == "__main__":
    for c in LOOPS:
        print(f"{c['name']} {c['start']} → {c['end']} 表{len(c['days'])}天/{c['km']}km 书{c['book_days']}天/{c['book_km']}km 段{len(c['segments'])}")
        kans = [d for d in c["days"] if "喀纳斯" in d["stay"] or "禾木" in d["stay"]]
        duku = [d for d in c["days"] if "巴音布鲁克" in d["stay"] or d["segment"].startswith("独库")]
        ej = [d for d in c["days"] if "额济纳" in d["stay"] or d["stay"] == "达来呼布"]
        cx = [d for d in c["days"] if d["segment"] == "川西大环线"]
        if kans:
            print("  喀纳斯/禾木", kans[0]["date"], kans[-1]["date"])
        if duku:
            print("  独库段", duku[0]["date"], duku[-1]["date"])
        if ej:
            print("  额济纳", ej[0]["date"], ej[-1]["date"])
        if cx:
            print("  川西", cx[0]["date"], cx[-1]["date"])
