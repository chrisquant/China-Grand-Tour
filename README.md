# 四大环线

济源出发的中国四大环线，用 Streamlit 做成可翻页的本地站点。总览看四条线，侧栏按东、北、南、西看停留、路线和地图。

日期是计划，不是天气和封路承诺。逐日表比书里的概数长或短的地方，页面上两套数字都写着。

## 行程

- 东线：2028-04-08 至 2028-05-20，43 天
- 北线：2028-07-15 至 2028-09-04，52 天（书中约 48 天）
- 南线：2028-09-12 至 2028-11-28，78 天（书中约 68 天）。川西在 10 月上旬
- 西线：2029-08-25 至 2029-10-08，45 天（书中约 49 天）。喀纳斯 9 月 17 日，独库 9 月 26–27 日，额济纳 10 月 3 日

空档在济源休整。

## 文件

| 文件 | 作用 |
| --- | --- |
| `app.py` | 站点。总览、四条环线、地图和图表 |
| `trip_data.py` | 日历、坐标、预算。逐日表从总控版 markdown 读 |
| `00_中国四大环线自驾全书（总控版）.md` | 行程原文 |
| `requirements.txt` | Python 依赖 |

## 运行

```bash
cd "growth and love/环游中国"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开终端里给出的地址，默认是 <http://localhost:8501>。

地图全屏用到 `st.html(..., unsafe_allow_javascript=True)`，需要 Streamlit 1.52 或更高。
