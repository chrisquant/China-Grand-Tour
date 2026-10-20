#!/usr/bin/env python3
"""中国四大环线。分页对齐欧亚自驾：侧栏、深色地图、日期滑块、甘特。"""

import importlib
import json
import math
from datetime import timedelta
from html import escape

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import trip_data as td

td = importlib.reload(td)

KM_NOTE = "里程是逐日表里的约数，坐标是城市点，不是实测轨迹。"


def _bearing(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _arrow(m, a, b, color):
    lat = (a[0] + b[0]) / 2
    lon = (a[1] + b[1]) / 2
    deg = _bearing(a, b) - 90
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24">'
        f'<g transform="rotate({deg:.0f} 12 12)">'
        f'<polygon points="9,7 18,12 9,17" fill="{color}"/></g></svg>'
    )
    folium.Marker(
        [lat, lon],
        icon=folium.DivIcon(icon_size=(18, 18), icon_anchor=(9, 9), html=svg),
    ).add_to(m)


def _line(loop):
    pts = []
    for i, leg in enumerate(loop["legs"]):
        if i == 0:
            pts.append(leg["a"])
        pts.extend(leg["mids"])
        pts.append(leg["b"])
    return pts


def _base_map(lat, lon, zoom):
    m = folium.Map(
        location=[lat, lon], zoom_start=zoom, tiles=None,
        zoom_control=True, scrollWheelZoom=True, width="100%", height="650px",
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, USGS, NOAA", name="base", control=False,
    ).add_to(m)
    m.get_root().header.add_child(folium.Element(
        "<style>html,body{background:#1B2430!important;margin:0;padding:0;height:100%}"
        ".folium-map{height:100%!important;background:#1B2430}"
        ".leaflet-container{background:#1B2430}"
        ".leaflet-div-icon{background:transparent;border:none}"
        ".leaflet-control-attribution{background:rgba(22,27,34,.8)!important;color:#c8c2b8!important}"
        ".leaflet-control-attribution a{color:#e2c7a0!important}"
        ".map-reset{display:block;margin-top:8px;height:30px;padding:0 8px;background:#fff;color:#333;"
        "border:2px solid rgba(0,0,0,.2);border-radius:4px;cursor:pointer;font:12px/26px sans-serif}"
        ".map-reset:hover{background:#f4f4f4}"
        ".map-full{height:30px;padding:0 8px;background:#fff;color:#333;border:2px solid rgba(0,0,0,.2);"
        "border-radius:4px;cursor:pointer;font:12px/26px sans-serif}"
        ".map-full:hover{background:#f4f4f4}"
        ".ov-legend{background:rgba(22,27,34,.82);color:#F2EFE9;padding:6px 8px;border-radius:4px;"
        "font:12px/1.7 sans-serif;margin:0 0 8px 8px}"
        ".ov-swatch{display:inline-block;width:16px;height:3px;margin-right:6px;vertical-align:middle}"
        ".ov-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#F2EFE9;margin-right:6px;vertical-align:middle}"
        ".city-card{position:absolute;z-index:800;top:12px;right:12px;width:min(380px,calc(100% - 70px));"
        "max-height:calc(100% - 24px);overflow:auto;background:#161B22;color:#F2EFE9;"
        "border:1px solid #3A4250;border-radius:8px;padding:12px 14px;box-shadow:0 8px 24px rgba(0,0,0,.35);"
        "font:14px/1.65 sans-serif}"
        ".city-card-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}"
        ".city-card-head b{font-size:16px}"
        ".city-card-close{background:#343B46;color:#F2EFE9;border:none;border-radius:4px;padding:2px 8px;cursor:pointer}"
        ".zlab.zhide{display:none}"
        "</style>"
    ))
    return m


def _fullscreen_control_js():
    return (
        "var Full=L.Control.extend({options:{position:'topright'},onAdd:function(){"
        "var btn=L.DomUtil.create('button','map-full');btn.type='button';btn.title='看大图';btn.textContent='全屏';"
        "L.DomEvent.disableClickPropagation(btn);"
        "L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);window.parent.postMessage({type:'china-loops-fullscreen'},'*');});"
        "window.addEventListener('message',function(ev){if(!ev.data||ev.data.type!=='china-loops-fullscreen-state')return;"
        "btn.textContent=ev.data.on?'退出':'全屏';setTimeout(function(){map.invalidateSize();},200);});"
        "return btn;}});map.addControl(new Full);"
        "window.addEventListener('resize',function(){map.invalidateSize();});"
    )


def _fullscreen_host():
    st.html(
        """
<script>
(function(){
  if (window.__chinaLoopsFs) return;
  window.__chinaLoopsFs = true;
  function tell(iframe){
    var on = document.fullscreenElement === iframe;
    try { iframe.contentWindow.postMessage({type:'china-loops-fullscreen-state', on:on}, '*'); } catch (err) {}
  }
  window.addEventListener('message', function(e){
    if (!e.data || e.data.type !== 'china-loops-fullscreen') return;
    var iframe = null;
    document.querySelectorAll('iframe').forEach(function(f){ if (f.contentWindow === e.source) iframe = f; });
    if (!iframe) return;
    var req = iframe.requestFullscreen || iframe.webkitRequestFullscreen;
    var done = function(){ tell(iframe); };
    if (document.fullscreenElement === iframe) document.exitFullscreen().then(done).catch(done);
    else if (req) req.call(iframe).then(done).catch(done);
  });
  document.addEventListener('fullscreenchange', function(){
    document.querySelectorAll('iframe').forEach(tell);
  });
})();
</script>
""",
        unsafe_allow_javascript=True,
    )


def _star(m, pos):
    html = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
        '<polygon points="8,1 10,6 15,6.4 11.2,9.6 12.4,14.6 8,12 3.6,14.6 4.8,9.6 1,6.4 6,6" '
        'fill="#F5C16C" stroke="#161B22" stroke-width="0.6"/></svg>'
    )
    folium.Marker(
        [pos["lat"], pos["lon"]],
        tooltip=f"{pos['status']} · {pos['name']}",
        icon=folium.DivIcon(icon_size=(16, 16), icon_anchor=(8, 8), html=html),
    ).add_to(m)


def _leg_latlon(leg):
    return [(leg["a"]["lat"], leg["a"]["lon"]), *[(p["lat"], p["lon"]) for p in leg["mids"]], (leg["b"]["lat"], leg["b"]["lon"])]


# 住宿名或绕路点 → 总览上写的省会名。西宁住在湟源，图上仍写西宁。
_CAPITALS = {
    "济南": "济南", "南京": "南京", "杭州": "杭州", "合肥": "合肥", "福州": "福州",
    "南昌": "南昌", "郑州": "郑州", "武汉": "武汉", "长沙": "长沙", "广州": "广州",
    "南宁": "南宁", "海口": "海口", "成都": "成都", "贵阳": "贵阳", "昆明": "昆明",
    "西安": "西安", "兰州": "兰州", "西宁/湟源": "西宁", "银川": "银川", "乌鲁木齐": "乌鲁木齐",
    "太原": "太原", "呼和浩特": "呼和浩特", "沈阳": "沈阳", "长春": "长春", "哈尔滨": "哈尔滨",
    "石家庄": "石家庄", "上海": "上海", "重庆": "重庆", "天津": "天津", "北京": "北京",
}


def _route_capitals():
    found = {}
    for loop in td.LOOPS:
        for stop in loop["stops"]:
            label = _CAPITALS.get(stop["name"])
            if label and label not in found:
                found[label] = {"name": label, "lat": stop["lat"], "lon": stop["lon"]}
        for leg in loop["legs"]:
            for mid in leg["mids"]:
                label = _CAPITALS.get(mid["name"])
                if label and label not in found:
                    found[label] = {"name": label, "lat": mid["lat"], "lon": mid["lon"]}
    return list(found.values())


def _capital_shifts(points):
    """在中国全图的比例上把省会名字错开。"""
    if not points:
        return []
    min_lat, max_lat, min_lon, max_lon = 18, 54, 73, 135

    def xy(p):
        x = (p["lon"] - min_lon) / (max_lon - min_lon) * 1000
        y = (max_lat - p["lat"]) / (max_lat - min_lat) * 520
        return x, y

    def box(x, y, shift):
        bw, bh = 58, 22
        dx, dy = _SHIFT_DIR[shift]
        cx = x + dx * bw * 0.7
        cy = y + dy * bh * 0.9
        return (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)

    def hit(a, b):
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

    placed = []
    out = []
    for p in points:
        x, y = xy(p)
        shift = 0
        for candidate in range(4):
            rect = box(x, y, candidate)
            if any(hit(rect, old) for old in placed):
                continue
            shift = candidate
            placed.append(rect)
            break
        else:
            placed.append(box(x, y, 0))
        out.append(shift)
    return out


def _mark_capitals(m):
    points = _route_capitals()
    shifts = _capital_shifts(points)
    for p, shift in zip(points, shifts):
        folium.CircleMarker(
            [p["lat"], p["lon"]], radius=3, color="#F2EFE9", weight=1,
            fill=True, fill_color="#F2EFE9", fill_opacity=0.95,
        ).add_to(m)
        label = (
            f'<div style="transform:{_LABEL_SHIFT[shift]};pointer-events:none;'
            "white-space:nowrap;text-align:center;color:#F2EFE9;background:rgba(22,27,34,0.82);"
            "padding:1px 4px;border-radius:3px;font:12px/1.2 sans-serif;\">"
            f"{escape(p['name'])}</div>"
        )
        folium.Marker(
            [p["lat"], p["lon"]],
            icon=folium.DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=label),
        ).add_to(m)


def figure_overview_map(day):
    m = _base_map(36, 105, 4)
    current = td.loop_on(day)
    for loop in td.LOOPS:
        if current and loop["id"] == current["id"]:
            opacity = 0.95
        elif loop["end"] < day:
            opacity = 0.8
        else:
            opacity = 0.28
        for leg in loop["legs"]:
            pair = _leg_latlon(leg)
            if leg["kind"] == "ferry":
                folium.PolyLine(pair, color="#E2C7A0", weight=2.5, opacity=opacity, dash_array="8 8").add_to(m)
            else:
                folium.PolyLine(pair, color=loop["color"], weight=3, opacity=opacity).add_to(m)
    _mark_capitals(m)
    _star(m, td.locate(day))
    legend = "".join(
        f'<div><span class="ov-swatch" style="background:{c["color"]}"></span>{escape(c["name"])} {escape(c["theme"])}</div>'
        for c in td.LOOPS
    )
    script = (
        "<script>(function(){var map=" + m.get_name() + ";"
        "var home=[[18,73],[54,135]];"
        "map.fitBounds(home,{padding:[8,8],animate:false});"
        "var saved=null;try{saved=JSON.parse(localStorage.getItem('china-loops-overview-v1'));}catch(e){}"
        "if(saved&&typeof saved.zoom==='number'){map.setView([saved.lat,saved.lon],saved.zoom,{animate:false});}"
        "map.on('moveend',function(){try{var c=map.getCenter();"
        "localStorage.setItem('china-loops-overview-v1',JSON.stringify({lat:c.lat,lon:c.lng,zoom:map.getZoom()}));}catch(err){}});"
        "var Reset=L.Control.extend({options:{position:'topleft'},onAdd:function(){"
        "var btn=L.DomUtil.create('button','map-reset');btn.type='button';btn.title='回到中国全图';btn.textContent='复位';"
        "L.DomEvent.disableClickPropagation(btn);"
        "L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);try{localStorage.removeItem('china-loops-overview-v1');}catch(err){}"
        "map.fitBounds(home,{padding:[8,8],animate:false});});return btn;}});map.addControl(new Reset());"
        "var Legend=L.Control.extend({options:{position:'bottomleft'},onAdd:function(){"
        "var d=L.DomUtil.create('div','ov-legend');d.innerHTML=" + json.dumps(
            legend + '<div><span class="ov-dot"></span>省会</div><div><span style="color:#F5C16C">★</span> 当晚</div><div><span class="ov-swatch" style="background:#E2C7A0"></span>渡轮</div>',
            ensure_ascii=False,
        ) + ";return d;}});map.addControl(new Legend());" + _fullscreen_control_js() + "})();</script>"
    )
    return m.get_root().render() + script


_LABEL_SHIFT = (
    "translate(-50%,-140%)",
    "translate(8px,-50%)",
    "translate(-108%,-50%)",
    "translate(-50%,8px)",
)
# 相对点的方向：上、右、左、下。用来判断两张标签会不会叠在一起。
_SHIFT_DIR = ((0, -1), (1, 0), (-1, 0), (0, 1))


# 住宿名 → 放大几档才写名字。None 表示和旁边的名字是同一个地方，不再写第二遍。
# 0 打开就显示。2、3、5 分别是放大两档、三档、五档。没写进表的过夜点按 2 档。
_NAME_TIER = {
    "济源": 0,
    "开封": 0, "徐州": 0,
    "济南": 0, "青岛": 0, "扬州": 0, "上海": 0,
    "普陀山": 0, "福州": 0, "厦门": 0, "武夷山": 0, "庐山": 0,
    "太原": 0, "大同": 0, "承德": 0, "阿尔山": 0,
    "北极村": 0, "哈尔滨": 0, "大连": 0,
    "武当山": 0, "武陵源": 0, "凤凰": 0, "重庆": 0, "成都": 0, "峨眉山": 0, "沟口": 0,
    "亚丁": 0, "丽江": 0, "腾冲": 0, "昆明": 0,
    "景洪": 0, "桂林": 0, "北海": 0, "三亚": 0, "南昌": 0,
    "华阴": 0, "西安": 0, "兰州": 0, "西宁/湟源": 0, "茶卡": 0, "敦煌": 0,
    "吐鲁番": 0, "乌鲁木齐": 0, "可可托海": 0, "喀纳斯": 0, "伊宁": 0,
    "喀什": 0, "酒泉/嘉峪关": 0, "银川": 0,
    "泰山山顶": 2, "南京": 2, "杭州": 2, "汤口": 2, "婺源": 2,
    "曲阜": 2, "烟台/蓬莱": 2, "雁荡山": 2, "威海": 2, "连云港": 2, "无锡": 2, "千岛湖": 2,
    "泉州": 2, "三清山": 2,
    "壶口镇": 2, "海拉尔": 2, "满洲里": 2, "沈阳": 2,
    "平遥": 2, "台怀镇": 2, "镜泊湖": 2, "张家口": 2, "乌兰浩特": 2, "额尔古纳": 2,
    "黑河": 2, "五大连池": 2, "伊春": 2, "延吉": 2, "丹东": 2, "北戴河": 2, "乌兰布统": 2,
    "香格里拉": 2, "大理": 2, "泸沽湖": 2,
    "飞来寺": 2, "阳朔": 2, "海口": 2, "老君山": 2, "木鱼": 2, "恩施": 2, "武隆": 2,
    "丹巴": 2, "四姑娘山": 2, "普洱": 2, "安顺": 2, "荔波": 2, "韶关": 2, "肇庆": 2, "湛江": 2,
    "黑马河": 2, "赛湖畔": 2,
    "禾木": 2, "那拉提": 2, "额济纳": 2, "宝鸡": 2, "天水": 2, "德令哈": 2, "哈密": 2,
    "阜康/富蕴": 2, "布尔津": 2, "巴音布鲁克": 2, "库车": 2, "阿克苏": 2, "中卫": 2,
    "苏州": 3, "乌镇": 3, "天台": 3, "太姥山": 3, "南靖": 3, "牯岭": 3,
    "绵山/介休": 3, "代县": 3, "应县": 3, "浑源": 3, "张北": 3, "达里湖": 3, "本溪/丹东": 3,
    "新都桥": 3, "理塘": 3, "罗平": 3, "龙脊": 3, "西江": 3, "大新": 3, "博鳌": 3,
    "陵水": 3, "尖峰岭": 3, "儋州": 3,
    "巴里坤": 3, "特克斯": 3,
    "火山附近": 5, "黄花沟": 5, "石林": 5, "室韦": 5, "临江": 5, "莫尔道嘎": 5,
    "黑山头": 5, "满归": 5, "北红村": 5,
    "鹤峰/恩施": 5, "江口": 5, "川主寺": 5, "若尔盖": 5, "扎尕那": 5, "得荣": 5,
    "雨崩/德钦": 5, "织金": 5,
    "大柴旦": 5, "水上雅丹": 5, "乌尔禾": 5,
    "普陀": None, "平遥古城外": None, "喀纳斯/禾木": None, "茶卡/德令哈": None,
    "巴音布鲁克/库车": None, "达来呼布": None,
}


def _name_tier(name, override=None):
    if override and name in override:
        return override[name]
    if name in _NAME_TIER:
        return _NAME_TIER[name]
    return 2


def _label_layout(stops, override=None):
    """档位按名单定死。同一档里只把标签错开，不再因为挤而改档。"""
    if not stops:
        return []
    lats = [s["lat"] for s in stops]
    lons = [s["lon"] for s in stops]
    span_lat = max(max(lats) - min(lats), 0.5)
    span_lon = max(max(lons) - min(lons), 0.5)
    min_lat, max_lat = min(lats), max(lats)
    min_lon = min(lons)

    def xy(s):
        x = (s["lon"] - min_lon) / span_lon * 1000
        y = (max_lat - s["lat"]) / span_lat * 520
        return x, y

    def box(x, y, shift, tier):
        scale = 2 ** tier
        bw, bh = 150 / scale, 56 / scale
        dx, dy = _SHIFT_DIR[shift]
        cx = x + dx * bw * 0.62
        cy = y + dy * bh * 0.75
        return (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)

    def hit(a, b):
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

    tiers = [_name_tier(s["name"], override) for s in stops]
    rank = sorted((i for i in range(len(stops)) if tiers[i] is not None), key=lambda i: (tiers[i], stops[i]["n"]))
    placed = []
    out = [{"tier": tiers[i], "shift": 0} for i in range(len(stops))]
    for i in rank:
        x, y = xy(stops[i])
        tier = tiers[i]
        shift = i % 4
        for candidate in range(4):
            rect = box(x, y, candidate, tier)
            if any(hit(rect, box(px, py, pshift, tier)) for ptier, pshift, px, py in placed if ptier <= tier):
                continue
            shift = candidate
            break
        placed.append((tier, shift, x, y))
        out[i] = {"tier": tier, "shift": shift}
    return out


def _city_card_script(m, clickables):
    if not clickables:
        return ""
    binds = []
    for handles, name, text in clickables:
        card = (
            "<div class='city-card-head'><b>" + escape(name) + "</b>"
            "<button type='button' class='city-card-close'>收起</button></div>"
            "<div class='city-card-body'>" + escape(text) + "</div>"
        )
        targets = ",".join(handles)
        binds.append(
            f"[{targets}].forEach(function(layer){{layer.on('click',function(e){{"
            f"L.DomEvent.stopPropagation(e);toggle({json.dumps(name, ensure_ascii=False)},{json.dumps(card, ensure_ascii=False)});}});}});"
        )
    return (
        "<script>(function(){var map=" + m.get_name() + ";var current=null;var card=null;"
        "function hide(){if(card)card.style.display='none';current=null;}"
        "function toggle(name,html){"
        "if(!card){card=L.DomUtil.create('div','city-card',map.getContainer());"
        "L.DomEvent.disableClickPropagation(card);L.DomEvent.disableScrollPropagation(card);}"
        "if(current===name&&card.style.display!=='none'){hide();return;}"
        "card.innerHTML=html;card.style.display='block';current=name;"
        "var btn=card.querySelector('.city-card-close');"
        "if(btn)L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);hide();});"
        "}" + "".join(binds) + "})();</script>"
    )


def _mark_sights(m, loop, segment, clickables, focus):
    """景点始终是小点。名字用 5 档，放大五档才出现。"""
    for s in loop.get("sights") or []:
        if segment and s["segment"] != segment:
            continue
        circle = folium.CircleMarker(
            [s["lat"], s["lon"]], radius=3, color="#E2C7A0", weight=1,
            fill=True, fill_color="#E2C7A0", fill_opacity=0.95,
        )
        circle.add_to(m)
        label = (
            '<div class="zlab zhide" data-tier="5" style="transform:translate(-50%,-140%);pointer-events:none;'
            "white-space:nowrap;text-align:center;color:#F2EFE9;background:rgba(22,27,34,0.82);"
            "padding:1px 4px;border-radius:3px;font:11px/1.2 sans-serif;\">"
            f"{escape(s['name'])}</div>"
        )
        marker = folium.Marker(
            [s["lat"], s["lon"]],
            icon=folium.DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=label),
        )
        marker.add_to(m)
        clickables.append(([circle.get_name(), marker.get_name()], s["name"], s["text"]))
        focus.append((s["lat"], s["lon"]))


def figure_loop_map(loop, segment):
    m = _base_map(loop["stops"][0]["lat"], loop["stops"][0]["lon"], 5)
    focus = []
    clickables = []
    dates = None
    if segment:
        dates = {d["date"] for d in loop["days"] if d["segment"] == segment}
    for leg in loop["legs"]:
        pair = _leg_latlon(leg)
        in_seg = dates is None or leg["a"]["date"] in dates or leg["b"]["date"] in dates
        color = loop["color"] if in_seg else "#5C6570"
        opacity = 0.95 if in_seg else 0.35
        if leg["kind"] == "ferry":
            folium.PolyLine(pair, color="#E2C7A0", weight=3, opacity=opacity, dash_array="8 8",
                            tooltip=f"渡轮 · {leg['a']['name']} → {leg['b']['name']}").add_to(m)
        else:
            folium.PolyLine(pair, color=color, weight=3, opacity=opacity).add_to(m)
        if in_seg:
            mid = max(len(pair) // 2, 1)
            _arrow(m, pair[mid - 1], pair[mid], "#E2C7A0" if leg["kind"] == "ferry" else color)
            focus.extend(pair)
    visible = []
    for stop in loop["stops"]:
        if not stop["n"] and any(s["n"] and s["name"] == stop["name"] for s in loop["stops"]):
            continue
        on = dates is None or stop["date"] in dates or (stop.get("until") and any(stop["date"] <= d <= stop["until"] for d in dates))
        if not on:
            continue
        covered = [d for d in loop["days"] if stop["date"] <= d["date"] <= stop["until"] and d["stay"] == stop["name"]]
        seg = covered[0]["segment"] if covered else ""
        visible.append({**stop, "segment": seg})
    if loop.get("list_sights"):
        seen = {s["name"] for s in visible}
        for leg in loop["legs"]:
            in_seg = dates is None or leg["a"]["date"] in dates or leg["b"]["date"] in dates
            if not in_seg:
                continue
            for mid in leg["mids"]:
                if mid["name"] in seen:
                    continue
                seen.add(mid["name"])
                visible.append({
                    **mid, "date": leg["b"]["date"], "until": leg["b"]["date"], "days": 0,
                    "plan": "路过", "n": leg["b"]["n"], "segment": "", "pass": True,
                })
    _mark_sights(m, loop, segment, clickables, focus)
    layout = _label_layout(visible, loop.get("label_tier"))
    for stop, place in zip(visible, layout):
        tier = place["tier"]
        circle = folium.CircleMarker(
            [stop["lat"], stop["lon"]], radius=7 if tier == 0 else 5, color="#F2EFE9", weight=1,
            fill=True, fill_color=loop["color"], fill_opacity=0.95,
        )
        circle.add_to(m)
        handles = [circle.get_name()]
        if tier is not None:
            if stop.get("pass"):
                span = f"{stop['date'].month}月{stop['date'].day}日 · 路过"
            else:
                span = f"{stop['date'].month}月{stop['date'].day}日"
                if stop["days"] > 1:
                    span += f" · {stop['days']}天"
            klass = "zlab" if tier == 0 else "zlab zhide"
            label = (
                f'<div class="{klass}" data-tier="{tier}" style="transform:{_LABEL_SHIFT[place["shift"]]};'
                "white-space:nowrap;text-align:center;color:#F2EFE9;background:rgba(22,27,34,0.82);"
                "padding:2px 6px;border-radius:4px;font-size:12px;line-height:1.25;font-family:sans-serif;\">"
                f"{escape(stop['name'])}<br>{span}</div>"
            )
            marker = folium.Marker(
                [stop["lat"], stop["lon"]],
                icon=folium.DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=label),
            )
            marker.add_to(m)
            handles.append(marker.get_name())
        text = td.card_text(loop, stop["name"], stop["plan"])
        clickables.append((handles, stop["name"], text))
        focus.append((stop["lat"], stop["lon"]))
    home = ",".join(f"[{lat},{lon}]" for lat, lon in focus)
    script = (
        f"<script>(function(){{var map={m.get_name()};var home=[{home}];"
        "if(home.length>=2){map.fitBounds(home,{padding:[70,70],animate:false});}"
        "else if(home.length===1){map.setView(home[0],8);}"
        "var baseZoom=map.getZoom();"
        "function syncLab(){var extra=map.getZoom()-baseZoom;"
        "map.getContainer().querySelectorAll('.zlab').forEach(function(el){"
        "var t=+el.getAttribute('data-tier')||0;el.classList.toggle('zhide',t>extra);});}"
        "map.on('zoomend',syncLab);syncLab();"
        "var Reset=L.Control.extend({options:{position:'topleft'},onAdd:function(){"
        "var btn=L.DomUtil.create('button','map-reset');btn.type='button';btn.title='回到这段';btn.textContent='复位';"
        "L.DomEvent.disableClickPropagation(btn);"
        "L.DomEvent.on(btn,'click',function(e){L.DomEvent.stop(e);"
        "if(home.length>=2){map.fitBounds(home,{padding:[70,70],animate:false});}"
        "else if(home.length===1){map.setView(home[0],8);}});return btn;}});map.addControl(new Reset());"
        + _fullscreen_control_js() + "})();</script>"
    )
    return m.get_root().render() + script + _city_card_script(m, clickables)


def _dark(fig, height):
    fig.update_layout(
        height=height, paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        font=dict(color="#F2EFE9"), margin=dict(l=0, r=8, t=28, b=0),
    )
    fig.update_xaxes(tickfont=dict(color="#F2EFE9"), gridcolor="#3A4250")
    fig.update_yaxes(tickfont=dict(color="#F2EFE9"), gridcolor="#3A4250")
    return fig


def figure_km():
    rows = []
    for d in td.daterange(td.TRIP_START, td.TRIP_END):
        pos = td.locate(d)
        rows.append({"日期": d, "累计里程": pos["along_km"], "所在": pos["status"]})
    fig = px.line(pd.DataFrame(rows), x="日期", y="累计里程", hover_data=["所在"])
    fig.update_traces(line=dict(color="#C45C26", width=2))
    return _dark(fig, 300)


def figure_budget():
    names = [c["name"] for c in td.LOOPS]
    lows = [c["budget_low"] for c in td.LOOPS]
    highs = [c["budget_high"] for c in td.LOOPS]
    x = list(range(len(names)))
    fig = go.Figure()
    fig.add_bar(
        x=x, y=lows, name="参考下限", marker_color="#C45C26", width=0.55,
        text=[f"{v/10000:.1f}万" for v in lows], textposition="outside", cliponaxis=False,
        textfont=dict(color="#F2EFE9", size=12),
        customdata=list(zip(names, highs)),
        hovertemplate="%{customdata[0]}<br>下限 %{y:,.0f} 元<br>上限 %{customdata[1]:,.0f} 元<extra></extra>",
    )
    xs, ys = [], []
    for i, cap in enumerate(highs):
        xs += [i - 0.32, i + 0.32, None]
        ys += [cap, cap, None]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="参考上限", line=dict(color="#E8D5C4", width=2, dash="dash"), hoverinfo="skip"))
    fig.update_layout(
        height=380, bargap=0.28, paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        font=dict(color="#F2EFE9"), margin=dict(l=0, r=8, t=36, b=24),
        legend=dict(orientation="h", y=1.12, x=0),
        yaxis=dict(title="元", range=[0, max(highs) * 1.25], gridcolor="#3A4250", tickfont=dict(color="#F2EFE9")),
        xaxis=dict(tickmode="array", tickvals=x, ticktext=names, tickfont=dict(color="#F2EFE9")),
    )
    return fig


def figure_temp():
    df = pd.DataFrame([{"环线": c["name"], "低": c["temp_low"], "高": c["temp_high"]} for c in td.LOOPS])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["环线"], y=df["高"] - df["低"], base=df["低"],
        marker=dict(color=df["高"], colorscale=[[0, "#6BA3C7"], [0.45, "#E2B84A"], [1, "#D4532B"]], cmin=8, cmax=32, line=dict(width=0)),
        customdata=df[["低", "高"]].to_numpy(),
        hovertemplate="%{x}<br>白天 %{customdata[0]}–%{customdata[1]} ℃<extra></extra>",
        text=[f"{lo}–{hi}" for lo, hi in zip(df["低"], df["高"])],
        textposition="outside", textfont=dict(color="#F2EFE9", size=12), cliponaxis=False, showlegend=False,
    ))
    fig.update_layout(
        height=320, bargap=0.4, paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        font=dict(color="#F2EFE9"), margin=dict(l=0, r=8, t=28, b=0),
        yaxis=dict(title="℃", range=[0, 40], gridcolor="#3A4250", tickfont=dict(color="#F2EFE9")),
        xaxis=dict(tickfont=dict(color="#F2EFE9")),
    )
    return fig


def _night_stops(loop):
    return [s for s in loop["stops"] if s["n"]]


def _place_label(stop, counts):
    if counts[stop["name"]] > 1:
        return f"{stop['name']} {stop['date'].month}/{stop['date'].day}"
    return stop["name"]


def figure_place_gantt(loop):
    stops = _night_stops(loop)
    counts = {}
    for s in stops:
        counts[s["name"]] = counts.get(s["name"], 0) + 1
    rows = []
    for stop in stops:
        seg = next((d["segment"] for d in loop["days"] if d["date"] == stop["date"] and d["stay"] == stop["name"]), "")
        rows.append({
            "地点": _place_label(stop, counts),
            "开始": stop["date"],
            "结束": stop["until"] + timedelta(days=1),
            "分段": seg,
            "天数": f"{stop['days']} 天",
        })
    fig = px.timeline(pd.DataFrame(rows), x_start="开始", x_end="结束", y="地点", color="分段", hover_data=["天数"])
    fig.update_layout(showlegend=False)
    fig = _dark(fig, max(320, 20 * len(rows) + 50))
    fig.update_yaxes(
        categoryorder="array", categoryarray=[r["地点"] for r in rows], autorange=True,
        title=None, tickfont=dict(size=11, color="#F2EFE9"),
    )
    return fig


def figure_loop_km(loop):
    cum = 0
    rows = []
    for d in loop["days"]:
        cum += d["km"]
        rows.append({"日期": d["date"], "本线累计": cum, "当晚": d["stay"]})
    fig = px.line(pd.DataFrame(rows), x="日期", y="本线累计", hover_data=["当晚"])
    fig.update_traces(line=dict(color=loop["color"], width=2))
    return _dark(fig, 300)


def figure_city_temp(loop):
    stops = _night_stops(loop)
    counts = {}
    for s in stops:
        counts[s["name"]] = counts.get(s["name"], 0) + 1
    rows = []
    for stop in stops:
        lo, hi = td.daytime_range(stop["lat"], stop["lon"], stop["elev"], stop["date"].month)
        rows.append({"城市": _place_label(stop, counts), "低": lo, "高": hi})
    df = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["城市"], y=df["高"] - df["低"], base=df["低"],
        marker=dict(color=df["高"], colorscale=[[0, "#6BA3C7"], [0.45, "#E2B84A"], [1, "#D4532B"]], cmin=0, cmax=36, line=dict(width=0)),
        customdata=df[["低", "高"]].to_numpy(),
        hovertemplate="%{x}<br>白天 %{customdata[0]}–%{customdata[1]} ℃<extra></extra>",
        text=[f"{lo}–{hi}" for lo, hi in zip(df["低"], df["高"])],
        textposition="outside", textfont=dict(color="#F2EFE9", size=10), cliponaxis=False, showlegend=False,
    ))
    fig.update_layout(
        height=420, bargap=0.25, paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        font=dict(color="#F2EFE9"), margin=dict(l=0, r=8, t=28, b=80),
        yaxis=dict(title="℃", range=[-10, 48], gridcolor="#3A4250", tickfont=dict(color="#F2EFE9")),
        xaxis=dict(tickfont=dict(color="#F2EFE9", size=10), tickangle=-50),
    )
    return fig


def figure_prep_rows(steps):
    rows = [{
        "事项": p["必须完成"],
        "开始": p["start"],
        "结束": p["end"] + timedelta(days=1),
        "验收": p["验收"],
    } for p in steps]
    fig = px.timeline(pd.DataFrame(rows), x_start="开始", x_end="结束", y="事项", color="事项", hover_data=["验收"])
    fig = _dark(fig, 320)
    fig.update_yaxes(
        categoryorder="array", categoryarray=[r["事项"] for r in rows], autorange=True, title=None,
    )
    return fig


def figure_prep():
    return figure_prep_rows(td.PREP)


def page_overview():
    st.title("祖国大好河山")
    st.caption("济源出发，济源结束。2028 年 4 月先走东线，7 月 15 日走北线，9 月 12 日接南线，2029 年 8 月 25 日走西线。空档在济源休整。")
    days = sum(len(c["days"]) for c in td.LOOPS)
    table_km = sum(c["km"] for c in td.LOOPS)
    book_km = sum(c["book_km"] for c in td.LOOPS)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("出发", td.TRIP_START.isoformat())
    c1.caption("东线，2028 年春")
    c2.metric("走完", td.TRIP_END.isoformat())
    c2.caption("西线回到济源")
    c3.metric("逐日表", f"{days} 天")
    c3.caption("书中概数约 208 天")
    c4.metric("逐日里程", f"{table_km/10000:.2f} 万 km")
    c4.caption(f"书中约 {book_km/10000:.2f} 万 km")

    st.subheader("路线")
    day = st.slider(
        "拖动日期，看当晚住在哪",
        min_value=td.TRIP_START, max_value=td.TRIP_END, value=td.TRIP_START,
        format="YYYY-MM-DD", key="loop_day",
    )
    pos = td.locate(day)
    st.components.v1.html(figure_overview_map(day), height=676, scrolling=False)
    where = f"**{day.isoformat()} · {pos['status']} · {pos['name']}**"
    if pos.get("route"):
        where += f" · {pos['route']}"
    where += f" · 累计约 **{pos['along_km']:,}** 公里。{pos['plan']}。"
    st.info(where + KM_NOTE)
    st.plotly_chart(figure_km(), width="stretch")
    st.caption("四条线分开走，中间的平台是济源休整。横轴是计划日期。")

    st.subheader("白天气温")
    st.plotly_chart(figure_temp(), width="stretch")
    st.caption("这一段实际经过月份的大致白天区间，不是逐日预报。")

    st.subheader("预算")
    st.plotly_chart(figure_budget(), width="stretch")
    st.caption("柱子是参考下限，虚线是参考上限。含油、宿、门票和景区交通，不含买车和折旧。每条另留 1–2 万应急，不画进柱子。日均按 500–800 元准备。")
    low = sum(c["budget_low"] for c in td.LOOPS)
    high = sum(c["budget_high"] for c in td.LOOPS)
    b1, b2, b3 = st.columns(3)
    b1.metric("四线合计", f"{low/10000:.1f}–{high/10000:.1f} 万")
    b2.metric("应急金", "4–8 万")
    b2.caption("每条 1–2 万，不主动花")
    b3.metric("日花费", "500–800 元")
    b3.caption("油、宿、门票、杂费")

    st.subheader("红线")
    st.dataframe(pd.DataFrame(td.RED_LINES), width="stretch", hide_index=True)
    st.markdown("**每周**")
    for rule in td.WEEKLY_RULES:
        st.markdown(f"- {rule}")

    st.subheader("出发前")
    st.plotly_chart(figure_prep(), width="stretch")
    st.caption("这张倒排对着东线出发日。北线、南线、西线在各自页面上按自己的出发日重排同一张清单。")
    with st.expander("车辆和装备"):
        for line in td.GEAR:
            st.markdown(f"- {line}")
    with st.expander("书里的四条线"):
        for c in td.LOOPS:
            st.markdown(f"**{c['mark']} {c['name']} · {c['theme']}**")
            st.markdown(c["blurb"])
            st.markdown(c["route_text"])


def page_loop(loop):
    title = f"{loop['name']} · {loop['theme']}"
    if loop["mark"]:
        title = f"{loop['mark']} {title}"
    st.title(title)
    st.caption(
        f"{loop['start'].isoformat()} – {loop['end'].isoformat()} · 逐日表 {len(loop['days'])} 天、{loop['km']:,} 公里"
        f" · 书中约 {loop['book_days']} 天、{loop['book_km']:,} 公里 · {loop['blurb']}"
    )
    if loop["shift_note"]:
        st.warning(loop["shift_note"])
    elevs = [d["elev"] for d in loop["days"]]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("逐日", f"{len(loop['days'])} 天")
    m2.metric("海拔", f"{min(elevs):,} – {max(elevs):,} 米")
    m3.metric("白天", f"{loop['temp_low']}–{loop['temp_high']} ℃")
    if loop.get("budget_rows"):
        total = sum(r["大约"] for r in loop["budget_rows"])
        m4.metric("预算", f"约 {total:,} 元")
        st.dataframe(pd.DataFrame(loop["budget_rows"]), width="stretch", hide_index=True)
        st.caption(loop["budget_note"])
    else:
        m4.metric("预算", f"{loop['budget_low']/10000:.1f}–{loop['budget_high']/10000:.1f} 万")
        st.caption("预算是整条线的参考区间，含油、宿、门票和景区交通。另留 1–2 万应急。没有拆到每个城市。")

    names = ["全程"] + [s["name"] for s in loop["segments"]]
    pick = st.selectbox("分段", names, key=f"seg_{loop['id']}")
    segment = None if pick == "全程" else pick
    st.components.v1.html(figure_loop_map(loop, segment), height=676, scrolling=False)
    st.caption("实线是公路，浅金色虚线是渡轮。打开只写隔得开的省会、一线和著名景区；苏州这类贴着大城市的要放大三档才写出来。放大两档看地级市和降下来的景区，三档看县城，五档看村镇。"
               + ("金色小点是这趟要去的景点，放大五档才写出名字。" if loop.get("sights") else "")
               + "点圆点可以看这一站在做什么。" + KM_NOTE)

    st.subheader("地点甘特")
    st.plotly_chart(figure_place_gantt(loop), width="stretch")
    st.caption("每根柱是连续住在这个地方的日子。同一座城隔开再住，会分成两根。")

    st.subheader("路线")
    st.plotly_chart(figure_loop_km(loop), width="stretch")
    st.caption("只累计这一条线的逐日里程，从出发当天算起。")

    st.subheader("城市气温")
    st.plotly_chart(figure_city_temp(loop), width="stretch")
    st.caption("按停留月份、纬度和海拔估的白天区间，用来备衣服，不是天气预报。")

    st.subheader("出发前准备")
    prep = td.prep_for(loop)
    st.plotly_chart(figure_prep_rows(prep), width="stretch")
    st.caption(f"倒排到 {loop['start'].isoformat()} 出发。最后一项在出发前一天收尾。")
    with st.expander("车辆和装备"):
        for line in td.GEAR:
            st.markdown(f"- {line}")

    st.subheader("历程")
    if loop["route_text"]:
        st.markdown(f"**总路线** {loop['route_text']}")
    rows = loop["days"] if segment is None else [d for d in loop["days"] if d["segment"] == segment]
    st.dataframe(pd.DataFrame([{
        "日期": d["date"].isoformat(),
        "天": f"D{d['n']}",
        "分段": d["segment"],
        "路段": d["route"],
        "里程": d["km"],
        "住宿": d["stay"],
        "安排": d["plan"],
    } for d in rows]), width="stretch", hide_index=True)

    st.subheader("地点")
    blurbs = td.segment_blurbs(loop, segment)
    if segment is None:
        for seg in loop["segments"]:
            chunk = [b for b in blurbs if b["分段"] == seg["name"]]
            with st.expander(f"{seg['name']}（D{seg['d0']}–D{seg['d1']}）"):
                for b in chunk:
                    st.markdown(f"**{b['地点']}** {b['介绍']}")
    else:
        for b in blurbs:
            st.markdown(f"**{b['地点']}** {b['介绍']}")

    st.subheader("注意事项")
    for line in loop["notes"]:
        st.markdown(f"- {line}")


def _loop_page(lid):
    def _run():
        page_loop(td.loop_by_id(lid))
    _run.__name__ = f"page_loop_{lid}"
    return _run


def main():
    st.set_page_config(page_title="环游中国", layout="wide", initial_sidebar_state="expanded")
    _fullscreen_host()
    st.sidebar.markdown("**济源出发**")
    pages = [st.Page(page_overview, title="总览", icon="🗺️", url_path="overview", default=True)]
    for c in td.LOOPS:
        pages.append(st.Page(_loop_page(c["id"]), title=f"{c['name']} {c['theme']}", icon="📍", url_path=c["id"]))
    pages.append(st.Page(_loop_page(td.TRIAL["id"]), title="春节出游", icon="🚗", url_path=td.TRIAL["id"]))
    st.navigation(pages, position="sidebar", expanded=True).run()


if __name__ == "__main__":
    main()
