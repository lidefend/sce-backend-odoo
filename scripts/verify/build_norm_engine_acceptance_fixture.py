#!/usr/bin/env python3
"""Build a deterministic Sichuan 2015 norm workbook for browser acceptance."""
from pathlib import Path
import sys

from openpyxl import Workbook


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/norm-engine-local-acceptance/sc-demo-norm-upsert.xlsx")
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    index = workbook.active
    index.title = "专业章节"
    index.append(["章节", "名称"])
    index.append(["", "A 土建与装饰定额"])
    index.append(["AA", "A.A 土石方工程"])
    index.append(["AB", "A.B 砌筑工程"])
    index.append(["AC", "A.C 混凝土及钢筋混凝土工程"])

    sheet = workbook.create_sheet("A 土建与装饰定额")
    sheet.append([
        "序号", "定额名称", "项目名称", "单位", "综合单价", "直接费",
        "人工费", "材料费", "机械费", "费率", "综合费", "工作内容",
    ])
    rows = [
        (1, "AA0001", "人工挖沟槽土方 一、二类土 深度2m以内", "m³", 38.52, 31.28, 28.10, 0, 3.18, 0, 7.24, "挖土、修边、清底"),
        (2, "AA0002", "人工挖基坑土方 一、二类土 深度2m以内", "m³", 42.76, 34.90, 31.20, 0, 3.70, 0, 7.86, "挖土、修边、清底"),
        (3, "AA0010", "机械挖土方 装车", "m³", 9.84, 8.25, 0.62, 0, 7.63, 0, 1.59, "机械挖土、装车"),
        (4, "AB0001", "砖基础 水泥砂浆 M5", "m³", 512.30, 438.20, 96.80, 326.40, 15, 0, 74.10, "调运砂浆、砌砖"),
        (5, "AB0012", "实心砖墙 240mm", "m³", 548.66, 466.40, 112.50, 338.20, 15.70, 0, 82.26, "砌砖墙、勾缝"),
        (6, "AC0001", "现浇混凝土基础 垫层", "m³", 486.20, 418.90, 52.30, 351.60, 15, 0, 67.30, "混凝土浇筑、养护"),
        (7, "AC0015", "现浇混凝土矩形柱", "m³", 596.75, 511.20, 86.40, 397.80, 27, 0, 85.55, "混凝土浇筑、振捣、养护"),
        (8, "AC0101", "现浇构件钢筋 圆钢 HPB300", "t", 4865, 4210, 1230, 2870, 110, 0, 655, "钢筋制作、绑扎、安装"),
    ]
    for row in rows:
        sheet.append(row)
    workbook.save(output)
    print(output)


if __name__ == "__main__":
    main()
