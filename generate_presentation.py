from __future__ import annotations

import html
import zipfile
from pathlib import Path


OUT = Path("校园网项目汇报.pptx")
W, H = 12192000, 6858000

NAVY = "102A43"
BLUE = "176B87"
TEAL = "2A9D8F"
ORANGE = "F4A261"
RED = "E76F51"
CREAM = "F7F4ED"
WHITE = "FFFFFF"
INK = "183B56"
MUTED = "627D98"
PALE_BLUE = "EAF4F7"
PALE_TEAL = "E8F5F2"
PALE_ORANGE = "FFF0E1"
PALE_RED = "FCE9E5"
LINE = "C7D8E0"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def runs(text: str, size: int, color: str, bold: bool = False) -> str:
    return (
        f'<a:r><a:rPr lang="zh-CN" sz="{size * 100}" b="{1 if bold else 0}" '
        f'dirty="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        f'<a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/>'
        f'</a:rPr><a:t>{esc(text)}</a:t></a:r>'
    )


def text_box(
    sid: int,
    x: int,
    y: int,
    cx: int,
    cy: int,
    text: str,
    size: int = 20,
    color: str = INK,
    bold: bool = False,
    align: str = "l",
    valign: str = "mid",
    fill: str | None = None,
    line: str | None = None,
    radius: bool = False,
    margin: int = 110000,
) -> str:
    shape = "roundRect" if radius else "rect"
    fill_xml = (
        f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
        if fill
        else "<a:noFill/>"
    )
    line_xml = (
        f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
        if line
        else "<a:ln><a:noFill/></a:ln>"
    )
    paras = []
    for part in text.split("\n"):
        paras.append(
            f'<a:p><a:pPr algn="{align}"/>{runs(part, size, color, bold)}'
            f'<a:endParaRPr lang="zh-CN" sz="{size * 100}"/></a:p>'
        )
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{sid}" name="Text {sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
        <a:prstGeom prst="{shape}"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}
      </p:spPr>
      <p:txBody><a:bodyPr wrap="square" anchor="{valign}" lIns="{margin}" rIns="{margin}"
        tIns="{margin // 2}" bIns="{margin // 2}"/><a:lstStyle/>{''.join(paras)}</p:txBody>
    </p:sp>"""


def line_shape(
    sid: int,
    x: int,
    y: int,
    cx: int,
    cy: int,
    color: str = LINE,
    width: int = 22000,
    arrow: bool = False,
    dash: bool = False,
) -> str:
    tail = '<a:tailEnd type="none"/><a:headEnd type="triangle"/>' if arrow else ""
    dash_xml = '<a:prstDash val="dash"/>' if dash else ""
    return f"""
    <p:cxnSp>
      <p:nvCxnSpPr><p:cNvPr id="{sid}" name="Line {sid}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
        <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
        <a:ln w="{width}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{dash_xml}{tail}</a:ln>
      </p:spPr>
    </p:cxnSp>"""


def circle(sid: int, x: int, y: int, d: int, fill: str, label: str, size: int = 17) -> str:
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{sid}" name="Circle {sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{d}" cy="{d}"/></a:xfrm>
        <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:ln><a:noFill/></a:ln>
      </p:spPr>
      <p:txBody><a:bodyPr anchor="ctr" lIns="50000" rIns="50000" tIns="0" bIns="0"/>
        <a:lstStyle/><a:p><a:pPr algn="ctr"/>{runs(label, size, WHITE, True)}
        <a:endParaRPr lang="zh-CN" sz="{size * 100}"/></a:p></p:txBody>
    </p:sp>"""


def base_shapes(title: str, section: str, page: int) -> list[str]:
    return [
        text_box(2, 480000, 230000, 2300000, 300000, section.upper(), 11, TEAL, True),
        text_box(3, 480000, 530000, 10400000, 560000, title, 27, NAVY, True),
        line_shape(4, 480000, 1160000, 11200000, 0, LINE, 14000),
        text_box(5, 11100000, 6320000, 500000, 220000, f"{page:02d}", 10, MUTED, True, "r"),
    ]


def slide_xml(shapes: list[str]) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
 <p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{CREAM}"/></a:solidFill>
 <a:effectLst/></p:bgPr></p:bg><p:spTree>
 <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
 <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
 <a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
 {''.join(shapes)}
 </p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"""


def slide1() -> str:
    s = [
        text_box(2, 0, 0, W, H, "", fill=NAVY),
        text_box(3, 650000, 670000, 3100000, 370000, "COMPUTER NETWORK · TEAM 12", 12, ORANGE, True),
        text_box(4, 650000, 1350000, 7500000, 1000000, "基于 Mininet 的\n校园网构建", 36, WHITE, True, valign="mid"),
        text_box(5, 680000, 2700000, 6500000, 520000, "从分层架构到安全边界的可运行仿真", 20, "D9EAF0"),
        text_box(6, 680000, 5100000, 3100000, 620000, "5–6 MINUTES", 13, NAVY, True, fill=ORANGE, radius=True, align="ctr"),
        text_box(7, 680000, 5850000, 5500000, 300000, "核心 · 汇聚 · 接入  /  VLAN  /  DMZ  /  VPN", 12, "B7CFD8"),
    ]
    # Decorative topology constellation
    s += [
        circle(10, 8550000, 1200000, 900000, ORANGE, "fw1", 18),
        circle(11, 7450000, 2750000, 780000, TEAL, "cs1", 17),
        circle(12, 9600000, 2750000, 780000, BLUE, "DMZ", 15),
        circle(13, 10700000, 1400000, 700000, RED, "公网", 14),
        circle(14, 7900000, 4450000, 620000, "5B8FA3", "接入", 13),
        circle(15, 9400000, 4450000, 620000, "5B8FA3", "接入", 13),
        line_shape(20, 7900000, 2050000, 850000, 700000, "6D91A0", 26000),
        line_shape(21, 9450000, 2050000, -500000, 700000, "6D91A0", 26000),
        line_shape(22, 9450000, 1600000, 1250000, 0, "6D91A0", 26000),
        line_shape(23, 7800000, 3500000, 300000, 1000000, "6D91A0", 22000),
        line_shape(24, 7850000, 3350000, 1750000, 1100000, "6D91A0", 22000),
    ]
    return slide_xml(s)


def slide2() -> str:
    s = base_shapes("我们构建的，不只是一张能 Ping 通的拓扑", "01 / 项目定位", 2)
    cards = [
        ("2", "核心交换机", BLUE),
        ("4", "汇聚交换机", TEAL),
        ("18", "接入交换机", ORANGE),
        ("31", "主机与服务器", RED),
    ]
    for i, (num, label, color) in enumerate(cards):
        x = 520000 + i * 2850000
        s.append(text_box(10 + i, x, 1510000, 2480000, 1130000, "", fill=WHITE, line=LINE, radius=True))
        s.append(text_box(20 + i, x + 180000, 1620000, 650000, 520000, num, 30, color, True))
        s.append(text_box(30 + i, x + 180000, 2190000, 2000000, 270000, label, 13, MUTED, True))
    s += [
        text_box(40, 520000, 3040000, 3500000, 420000, "课程基础要求", 15, NAVY, True),
        text_box(41, 520000, 3510000, 3500000, 1450000,
                 "VLAN 二层隔离\n跨网段三层路由\n服务器区访问\nACL 访问控制",
                 18, INK, False, fill=PALE_BLUE, radius=True, margin=230000),
        text_box(42, 4350000, 3040000, 3500000, 420000, "面向真实业务扩展", 15, NAVY, True),
        text_box(43, 4350000, 3510000, 3500000, 1450000,
                 "主 / 分校区互联\n公网与 DMZ 隔离\nGRE 远程安全接入\n边界出入站控制",
                 18, INK, False, fill=PALE_TEAL, radius=True, margin=230000),
        text_box(44, 8180000, 3040000, 3500000, 420000, "最终呈现", 15, NAVY, True),
        text_box(45, 8180000, 3510000, 3500000, 1450000,
                 "真实网络运行\n真实策略执行\n真实数据采集\n可视化反馈闭环",
                 18, INK, False, fill=PALE_ORANGE, radius=True, margin=230000),
        text_box(46, 520000, 5430000, 11150000, 610000,
                 "目标：把课本中的 VLAN、路由、ACL、DMZ，落成一套可运行、可验证、可观察的系统。",
                 18, WHITE, True, fill=NAVY, radius=True, align="ctr"),
    ]
    return slide_xml(s)


def slide3() -> str:
    s = base_shapes("整体框架：分层组织，边界统一收口", "02 / 网络架构", 3)
    s += [
        text_box(10, 500000, 1450000, 1500000, 360000, "校园内网", 15, TEAL, True),
        text_box(11, 500000, 1870000, 7300000, 3500000, "", fill=PALE_TEAL, line=TEAL, radius=True),
        text_box(12, 8200000, 1450000, 1450000, 360000, "DMZ", 15, ORANGE, True),
        text_box(13, 8100000, 1870000, 1650000, 3500000, "", fill=PALE_ORANGE, line=ORANGE, radius=True),
        text_box(14, 10200000, 1450000, 1450000, 360000, "模拟公网", 15, RED, True),
        text_box(15, 10100000, 1870000, 1650000, 3500000, "", fill=PALE_RED, line=RED, radius=True),
        circle(20, 3700000, 2100000, 850000, BLUE, "cs1", 18),
        text_box(21, 2650000, 3020000, 3000000, 480000, "核心层 · 高速交换与全网汇聚", 16, NAVY, True, fill=WHITE, radius=True, align="ctr"),
        text_box(22, 850000, 3890000, 1850000, 620000, "as1\n办公 / 教学", 15, INK, True, fill=WHITE, radius=True, align="ctr"),
        text_box(23, 2850000, 3890000, 1850000, 620000, "as2\n生活 / 无线", 15, INK, True, fill=WHITE, radius=True, align="ctr"),
        text_box(24, 4850000, 3890000, 1850000, 620000, "as3\n数据中心", 15, INK, True, fill=WHITE, radius=True, align="ctr"),
        text_box(25, 6850000, 3890000, 850000, 620000, "as4\n分校区", 13, INK, True, fill=WHITE, radius=True, align="ctr"),
        text_box(26, 850000, 4740000, 6650000, 480000,
                 "接入层：sw1–sw18 将终端按业务区域接入对应 VLAN",
                 15, MUTED, True, fill=WHITE, radius=True, align="ctr"),
        circle(30, 7550000, 2570000, 850000, NAVY, "fw1", 18),
        text_box(31, 8320000, 2670000, 1200000, 600000, "sw15\n公开服务", 14, INK, True, fill=WHITE, radius=True, align="ctr"),
        text_box(32, 10300000, 2670000, 1250000, 600000, "sw18\n外部节点", 14, INK, True, fill=WHITE, radius=True, align="ctr"),
        text_box(33, 8050000, 4360000, 3600000, 720000,
                 "所有跨区流量必须经过 fw1\n拓扑路径与安全策略保持一致",
                 16, WHITE, True, fill=NAVY, radius=True, align="ctr"),
        line_shape(40, 4500000, 2520000, 3050000, 400000, BLUE, 30000, True),
        line_shape(41, 8300000, 2950000, 200000, 0, ORANGE, 30000, True),
        line_shape(42, 9530000, 2950000, 750000, 0, RED, 30000, True),
        line_shape(43, 4120000, 2950000, -2300000, 920000, LINE, 19000),
        line_shape(44, 4120000, 2950000, -350000, 920000, LINE, 19000),
        line_shape(45, 4120000, 2950000, 1650000, 920000, LINE, 19000),
    ]
    return slide_xml(s)


def slide4() -> str:
    s = base_shapes("IP 与 VLAN：按业务域、安全域分配", "03 / 地址规划", 4)
    s += [
        text_box(10, 520000, 1460000, 4200000, 700000, "统一规则", 15, NAVY, True),
        text_box(11, 520000, 2020000, 4200000, 1040000,
                 "每个业务区域独立 /24\nVLAN ID 与第三段尽量对应\n网关统一使用 .1",
                 20, WHITE, True, fill=NAVY, radius=True, margin=240000),
        text_box(12, 520000, 3330000, 4200000, 620000,
                 "示例：VLAN 20 → 10.0.20.0/24 → 10.0.20.1",
                 15, BLUE, True, fill=WHITE, line=BLUE, radius=True, align="ctr"),
        text_box(13, 520000, 4260000, 4200000, 1170000,
                 "为什么这样分？\n地址有语义，ACL 易编写，故障易定位，未来扩展不打架。",
                 17, INK, False, fill=PALE_BLUE, radius=True, margin=240000),
    ]
    zones = [
        ("校园内网", "10.0.0.0/8", "宿舍 10/11/12 · 办公 20\n人事 50 · 财务 60 · 服务器 100", TEAL, PALE_TEAL),
        ("DMZ 隔离区", "10.0.110.0/24", "vpn_srv  .10\ndmz_web  .20", ORANGE, PALE_ORANGE),
        ("模拟公网", "203.0.113.0/24", "网关  .1\next_web  .10", RED, PALE_RED),
        ("VPN 隧道", "172.16.0.0/30", "服务端  .1\n客户端  .2", BLUE, PALE_BLUE),
    ]
    for i, (name, net, detail, color, pale) in enumerate(zones):
        x = 5050000 + (i % 2) * 3300000
        y = 1500000 + (i // 2) * 2150000
        s.append(text_box(20 + i, x, y, 3000000, 1850000, "", fill=pale, line=color, radius=True))
        s.append(text_box(30 + i, x + 180000, y + 150000, 2650000, 300000, name, 15, color, True))
        s.append(text_box(40 + i, x + 180000, y + 520000, 2650000, 390000, net, 22, NAVY, True))
        s.append(text_box(50 + i, x + 180000, y + 1020000, 2650000, 560000, detail, 14, MUTED, False))
    s.append(text_box(60, 5050000, 5860000, 6300000, 370000,
                      "地址规划直接服务于路由、隔离和安全策略，而不是单纯“编号”。",
                      16, NAVY, True, align="ctr"))
    return slide_xml(s)


def slide5() -> str:
    s = base_shapes("转发与安全：各做擅长的事", "04 / 核心机制", 5)
    s += [
        text_box(10, 520000, 1450000, 11150000, 600000,
                 "终端流量 → OVS 二层交换 → fw1 边界收口 → Linux 内核路由 → 目标 VLAN",
                 19, WHITE, True, fill=NAVY, radius=True, align="ctr"),
    ]
    steps = [
        ("01", "OVS", "Access / Trunk\n完成 VLAN 二层隔离", BLUE, PALE_BLUE),
        ("02", "Veth Pair", "连接 fw1 与\nLinux root 命名空间", TEAL, PALE_TEAL),
        ("03", "802.1Q 子接口", "为每个 VLAN 配置\n虚拟网关 .1", ORANGE, PALE_ORANGE),
        ("04", "IP Forward", "Linux 内核承担\n跨 VLAN 三层转发", RED, PALE_RED),
    ]
    for i, (no, title, detail, color, pale) in enumerate(steps):
        x = 520000 + i * 2850000
        s.append(text_box(20 + i, x, 2390000, 2500000, 1720000, "", fill=pale, line=color, radius=True))
        s.append(circle(30 + i, x + 180000, 2560000, 470000, color, no, 12))
        s.append(text_box(40 + i, x + 180000, 3160000, 2100000, 350000, title, 19, NAVY, True))
        s.append(text_box(50 + i, x + 180000, 3560000, 2100000, 470000, detail, 14, MUTED))
        if i < 3:
            s.append(line_shape(60 + i, x + 2500000, 3240000, 350000, 0, color, 30000, True))
    s += [
        text_box(70, 520000, 4580000, 5350000, 1120000,
                 "iptables · 有状态边界防火墙\n允许返回流量，拒绝外部主动入侵与 DMZ 横向移动",
                 17, INK, True, fill=PALE_TEAL, line=TEAL, radius=True, margin=240000),
        text_box(71, 6240000, 4580000, 5430000, 1120000,
                 "OVS OpenFlow ACL · 高性能精确匹配\n按源 / 目的网段与优先级控制宿舍、访客、敏感部门",
                 17, INK, True, fill=PALE_ORANGE, line=ORANGE, radius=True, margin=240000),
        text_box(72, 520000, 5940000, 11150000, 350000,
                 "设计取舍：OVS 专注二层转发与 ACL，Linux 专注成熟稳定的三层协议栈。",
                 15, NAVY, True, align="ctr"),
    ]
    return slide_xml(s)


def slide6() -> str:
    s = base_shapes("四个最值得展示的亮点", "05 / 项目亮点", 6)
    highlights = [
        ("01", "三臂防火墙 + DMZ", "公网、DMZ、内网三区分离\n所有跨区流量统一经过 fw1", NAVY, PALE_BLUE),
        ("02", "GRE VPN 安全接入", "开启后通过隧道访问授权资源\n关闭后公网不能直达内网", BLUE, PALE_TEAL),
        ("03", "双层安全防护", "iptables 有状态策略 + OVS ACL\n兼顾状态判断与高优先级阻断", RED, PALE_RED),
        ("04", "真实数据驱动前端", "Ping、路径、吞吐、策略命中均来自后端\n形成指令—执行—反馈闭环", ORANGE, PALE_ORANGE),
    ]
    for i, (no, title, detail, color, pale) in enumerate(highlights):
        x = 520000 + (i % 2) * 5700000
        y = 1510000 + (i // 2) * 2300000
        s.append(text_box(10 + i, x, y, 5300000, 1950000, "", fill=pale, line=color, radius=True))
        s.append(circle(20 + i, x + 230000, y + 230000, 550000, color, no, 13))
        s.append(text_box(30 + i, x + 970000, y + 210000, 4000000, 430000, title, 20, NAVY, True))
        s.append(text_box(40 + i, x + 970000, y + 760000, 4000000, 760000, detail, 15, INK))
    s.append(text_box(50, 520000, 6120000, 11000000, 300000,
                      "亮点不在“功能堆叠”，而在架构、安全、验证和展示形成了完整闭环。",
                      16, NAVY, True, align="ctr"))
    return slide_xml(s)


def slide7() -> str:
    s = [
        text_box(2, 0, 0, W, H, "", fill=NAVY),
        text_box(3, 650000, 650000, 2500000, 350000, "06 / 总结", 12, ORANGE, True),
        text_box(4, 650000, 1250000, 7200000, 700000, "让校园网真正跑起来", 34, WHITE, True),
        text_box(5, 650000, 2130000, 7000000, 480000,
                 "从结构设计，到策略执行，再到运行观测", 20, "D9EAF0"),
        text_box(6, 650000, 3300000, 2650000, 1120000,
                 "设计出来\n分层架构与地址规划", 18, NAVY, True, fill=ORANGE, radius=True, align="ctr"),
        text_box(7, 3450000, 3300000, 2650000, 1120000,
                 "运行起来\n路由、ACL、DMZ、VPN", 18, NAVY, True, fill=WHITE, radius=True, align="ctr"),
        text_box(8, 6250000, 3300000, 2650000, 1120000,
                 "看得见\n真实测量与路径反馈", 18, NAVY, True, fill=TEAL, radius=True, align="ctr"),
        text_box(9, 650000, 5350000, 9200000, 560000,
                 "把课本中的网络原理，变成一套可运行、可验证、可扩展的工程系统。",
                 20, WHITE, True),
        text_box(10, 10200000, 5350000, 1250000, 560000, "谢谢", 24, ORANGE, True, align="r"),
    ]
    return slide_xml(s)


def content_types(count: int) -> str:
    slide_overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="xml" ContentType="application/xml"/>
 <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
 <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
 <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
 <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
 <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
 <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
 {slide_overrides}
</Types>"""


def package_files(slides: list[str]) -> dict[str, str]:
    count = len(slides)
    slide_ids = "".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i + 2}"/>' for i in range(1, count + 1)
    )
    pres_rels = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    ]
    pres_rels += [
        f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, count + 1)
    ]
    files = {
        "[Content_Types].xml": content_types(count),
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
 <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
 <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""",
        "docProps/core.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <dc:title>基于 Mininet 的校园网构建</dc:title><dc:creator>第十二组</dc:creator>
 <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
 <dcterms:created xsi:type="dcterms:W3CDTF">2026-06-11T00:00:00Z</dcterms:created>
</cp:coreProperties>""",
        "docProps/app.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
 <Application>Microsoft Office PowerPoint</Application><Slides>{count}</Slides>
 <PresentationFormat>宽屏</PresentationFormat>
</Properties>""",
        "ppt/presentation.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
 <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
 <p:sldIdLst>{slide_ids}</p:sldIdLst>
 <p:sldSz cx="{W}" cy="{H}" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>""",
        "ppt/_rels/presentation.xml.rels": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 {''.join(pres_rels)}
</Relationships>""",
        "ppt/slideMasters/slideMaster1.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
 <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
 <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
 </p:spTree></p:cSld><p:clrMap accent1="{BLUE}" accent2="{TEAL}" accent3="{ORANGE}" accent4="{RED}"
 accent5="5B8FA3" accent6="829AB1" bg1="{CREAM}" bg2="EAF4F7" dk1="{NAVY}" dk2="{INK}"
 folHlink="954F72" hlink="0563C1" lt1="{WHITE}" lt2="D9EAF0" tx1="{NAVY}" tx2="{MUTED}"/>
 <p:sldLayoutIdLst><p:sldLayoutId id="1" r:id="rId1"/></p:sldLayoutIdLst>
 <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>""",
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
 <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>""",
        "ppt/slideLayouts/slideLayout1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
 <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
 <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" cy="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
 </p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>""",
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>""",
        "ppt/theme/theme1.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Campus Blueprint">
 <a:themeElements><a:clrScheme name="Campus">
 <a:dk1><a:srgbClr val="{NAVY}"/></a:dk1><a:lt1><a:srgbClr val="{WHITE}"/></a:lt1>
 <a:dk2><a:srgbClr val="{INK}"/></a:dk2><a:lt2><a:srgbClr val="{CREAM}"/></a:lt2>
 <a:accent1><a:srgbClr val="{BLUE}"/></a:accent1><a:accent2><a:srgbClr val="{TEAL}"/></a:accent2>
 <a:accent3><a:srgbClr val="{ORANGE}"/></a:accent3><a:accent4><a:srgbClr val="{RED}"/></a:accent4>
 <a:accent5><a:srgbClr val="5B8FA3"/></a:accent5><a:accent6><a:srgbClr val="829AB1"/></a:accent6>
 <a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink>
 </a:clrScheme><a:fontScheme name="Microsoft YaHei">
 <a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Arial"/></a:majorFont>
 <a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface="Arial"/></a:minorFont>
 </a:fontScheme><a:fmtScheme name="Campus"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
 <a:lnStyleLst><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
 <a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
 <a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
 </a:themeElements></a:theme>""",
    }
    for i, xml in enumerate(slides, 1):
        files[f"ppt/slides/slide{i}.xml"] = xml
        files[f"ppt/slides/_rels/slide{i}.xml.rels"] = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>"""
    return files


def main() -> None:
    slides = [slide1(), slide2(), slide3(), slide4(), slide5(), slide6(), slide7()]
    files = package_files(slides)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data.encode("utf-8"))
    print(f"Generated {OUT} ({OUT.stat().st_size} bytes, {len(slides)} slides)")


if __name__ == "__main__":
    main()
