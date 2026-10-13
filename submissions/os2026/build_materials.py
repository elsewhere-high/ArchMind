#!/usr/bin/env python3
"""Build the Chinese contest PDF and a narrated replay of real CLI output.

Run in the archmind Conda environment. Media tools are optional project extras.
No model calls, live agent execution, or human decisions are simulated as real.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[2]
REPO = "https://github.com/elsewhere-high/ArchMind"
TAG = "v0.1.0-os2026"
RELEASE = f"{REPO}/releases/tag/{TAG}"
DATE = "2026-10-13"
INK = "#153832"
GREEN = "#176B55"
MINT = "#DAEEE5"
PAPER = "#F5F4EF"
GOLD = "#DDA45E"
GRAY = "#51645F"
WHITE = "#FFFFFF"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_and_capture(key, command, display, destination):
    started = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    record = {"key": key, "command": display, "started_at": started, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    if result.returncode:
        raise RuntimeError(f"{display}\n{result.stdout}\n{result.stderr}")
    (destination / f"{key}.txt").write_text(f"$ {display}\n\n{result.stdout}{result.stderr}\nexit_code={result.returncode}\n", encoding="utf-8")
    return record


def capture(destination):
    destination.mkdir(parents=True, exist_ok=True)
    commands = [("verify", ["make", "verify"], "make verify")]
    commands += [(stage, [sys.executable, "-B", "submissions/os2026/demo.py", stage], f"python -B submissions/os2026/demo.py {stage}") for stage in ["input", "review", "evidence", "gate"]]
    commands += [("baseline", ["make", "demo"], "make demo"), ("build", ["make", "build"], "make build")]
    records = {key: run_and_capture(key, command, display, destination) for key, command, display in commands}
    data = {"recorded_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "data_scope": "synthetic fixtures; no model calls; no production review", "commands": list(records.values()), "dataset_sha256": load("evaluation/baseline/result.json")["dataset"]["sha256"]}
    (destination / "commands.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "baseline-result.json").write_text(json.dumps(load("evaluation/baseline/result.json"), ensure_ascii=False, indent=2), encoding="utf-8")
    print("CAPTURE_PASS commands=7", flush=True)
    return records


class PDF:
    def __init__(self, output, font, bold):
        pdfmetrics.registerFont(TTFont("CN", font, subfontIndex=0))
        pdfmetrics.registerFont(TTFont("CNB", bold, subfontIndex=0))
        self.c = canvas.Canvas(str(output), pagesize=(595.28, 841.89))
        self.c.setTitle("ArchMind｜2026 上海开源软件应用创新大赛作品介绍")
        self.c.setAuthor("ArchMind 项目")
        self.c.setSubject("AI+ 工业软件赛道：多专业工程设计预审")
        self.n = 0

    def box(self, x, y, w, h, fill=WHITE, radius=10, stroke=None):
        self.c.setFillColor(HexColor(fill))
        self.c.setStrokeColor(HexColor(stroke or fill))
        self.c.roundRect(x, 841.89-y-h, w, h, radius, fill=1, stroke=bool(stroke))

    def line(self, x1, y1, x2, y2, color=MINT, width=1):
        self.c.setStrokeColor(HexColor(color)); self.c.setLineWidth(width)
        self.c.line(x1, 841.89-y1, x2, 841.89-y2)

    def text(self, text, x, y, size=11, color=INK, bold=False):
        self.c.setFillColor(HexColor(color)); self.c.setFont("CNB" if bold else "CN", size)
        self.c.drawString(x, 841.89-y-size, text)

    def para(self, text, x, y, w, size=10.5, color=GRAY, leading=None, bold=False):
        style = ParagraphStyle("body", fontName="CNB" if bold else "CN", fontSize=size, leading=leading or size*1.6, textColor=HexColor(color), wordWrap="CJK", spaceAfter=0)
        p = Paragraph(escape(text).replace("\n", "<br/>"), style)
        _, h = p.wrap(w, 1000)
        p.drawOn(self.c, x, 841.89-y-h)
        return h

    def arrow(self, x1, y1, x2, y2, color=GREEN):
        self.line(x1,y1,x2,y2,color,1.4)
        a = math.atan2(y2-y1,x2-x1)
        for delta in [-0.5,0.5]:
            self.line(x2,y2,x2-6*math.cos(a+delta),y2-6*math.sin(a+delta),color,1.4)

    def page(self, number, title, subtitle):
        if self.n: self.c.showPage()
        self.n = number
        self.box(0,0,595.28,841.89,PAPER,0)
        self.text("ARCHMIND   /   OS2026",44,25,9,GREEN,True)
        self.text("AI+ 工业软件",448,25,9,GRAY)
        self.line(44,49,551,49,"#D4DED8")
        self.text(title,44,74,25,INK,True)
        self.para(subtitle,44,114,507,10.5)
        self.line(44,787,551,787,"#D4DED8")
        self.text("ArchMind 0.1.0  ·  2026-10-13  ·  合成案例 / 离线验证",44,801,8,GRAY)
        self.text(f"{number:02d} / 07",507,799,9,GREEN,True)

    def node(self,x,y,w,h,title,sub="",fill=WHITE):
        self.box(x,y,w,h,fill)
        self.text(title,x+12,y+9,11,INK,True)
        if sub: self.para(sub,x+12,y+29,w-24,8.8,GRAY,13)

    def source(self,text):
        self.para(text,44,746,507,8,GRAY,11)


def build_pdf(output, font, bold):
    d = PDF(output,font,bold)
    d.page(1,""," ")
    d.box(0,49,595.28,438,INK,0)
    for x in range(30,595,28): d.line(x,49,x,487,"#20453E",0.3)
    for y in range(65,487,28): d.line(0,y,595,y,"#20453E",0.3)
    d.text("2026 上海开源软件应用创新大赛",44,79,12,MINT)
    d.text("ArchMind",41,134,56,WHITE,True)
    d.text("多专业工程设计预审",44,215,28,WHITE,True)
    d.para("让工程意见回到证据，让关键决定留给责任人。",44,268,495,15,MINT,24)
    d.box(44,323,122,29,GOLD,5)
    d.text("AI+ 工业软件赛道",55,329,10,INK,True)
    d.para("建筑工程 · 研发设计 · 签字前内部预审",44,376,490,12,WHITE)
    d.para("面向园建、植物与雨水海绵交界问题，将独立专业审查、跨专业协调、证据核验与人工确认组织为可追溯的工作流。",44,412,494,11.3,MINT,18)
    for x,num,title,body in [(44,"03","专业协作","园建 / 植物 / 雨水海绵"),(216,"05","角色包","协调者、三专业、核验者"),(388,"01","人工责任边界","总工处置关键确认事项")]:
        d.box(x,510,163,112,WHITE)
        d.text(num,x+14,523,26,GREEN,True)
        d.text(title,x+14,559,12,INK,True)
        d.para(body,x+14,582,140,9.2)
    d.text("当前交付",44,649,12,INK,True)
    d.para("v0.1.0 工程原型：角色与技能定义、数据契约、命令行验证及构建工具。附可复现合成样例、中文演示视频与开源源码。",44,675,507,11,GRAY,18)
    d.source("AGPL-3.0-only  |  github.com/elsewhere-high/ArchMind\n本材料不主张生产部署、真实模型审查效果或法定审查资格。")

    d.page(2,"从跨专业接口，切入设计质量","项目背景与应用场景：建筑、景观与海绵城市设计中的签字前内部预审。")
    d.text("问题常常出现在专业之间",44,158,16,INK,True)
    rows=[("01","信息分散","同一节点的铺装标高、树池尺寸和排水参数分布在不同专业资料中，单专业视角难以闭合设计关系。"),("02","结论难以复核","意见若缺少事实编号、图纸引用和缺失资料清单，后续会签难以定位依据，也难以确认该由谁补充。"),("03","责任容易模糊","AI 能组织与检查信息，但工程设计意图、补证和签字仍需要明确的人类责任人。")]
    for i,(num,title,body) in enumerate(rows):
        y=194+i*108
        d.box(44,y,507,94)
        d.text(num,61,y+15,20,GREEN,True)
        d.text(title,108,y+14,13,INK,True)
        d.para(body,108,y+39,418,10.3)
    d.text("优先服务的工作场景",44,539,16,INK,True)
    for x,title,body in [(44,"设计团队内部预审","将授权结构化事实整理为专业意见、跨专业关联与待确认事项，辅助会签准备。"),(305,"项目总工与审查协调","沿意见编号回溯依据；统一收集缺失资料，明确补证、复审或否决的处置路径。")]:
        d.box(x,578,246,117,MINT)
        d.text(title,x+15,592,12,INK,True)
        d.para(body,x+15,620,215,10.1)
    d.source("赛道对应：官网将建筑列入 AI+ 工业软件领域，覆盖研发设计方向；本作品采用自主选题。\n以上为目标应用场景；当前公开验证来自虚构社区公园样例，不代表已有客户部署。")

    d.page(3,"职责清晰的多智能体架构","模型承担受约束的专业推理；数据契约、校验脚本和人工确认协议提供工程边界。")
    d.node(44,163,507,53,"授权结构化输入  /  Drawing Facts","事实编号、来源引用、专业范围、位置与缺失信息",MINT)
    d.arrow(167,217,167,233)
    d.node(44,234,246,57,"Manager","任务分派与完整性检查")
    d.node(305,234,246,57,"review-coordinator","组织专业审查与结果汇集")
    d.arrow(290,262,305,262)
    d.line(428,291,428,307,GREEN,1.3); d.line(125,307,470,307,GREEN,1.3)
    for x,title,sub in [(44,"园建 Reviewer","竖向、坡向与节点资料"),(216,"植物 Reviewer","树池、土球与根系空间"),(388,"雨水海绵 Reviewer","汇水、调蓄与设施接口")]:
        d.arrow(x+81,307,x+81,322); d.node(x,323,163,68,title,sub)
        d.line(x+81,391,x+81,410,GREEN,1.3)
    d.line(125,410,470,410,GREEN,1.3); d.arrow(167,410,167,426)
    d.node(44,426,246,68,"跨专业协调","关联共享构件、相同事实与控制条件")
    d.node(305,426,246,68,"evidence-verifier","核查引用与证据边界，保留上游意见")
    d.arrow(290,460,305,460)
    d.arrow(428,494,428,511)
    d.node(44,512,507,62,"人类总工确认  /  WAITING_HUMAN","补证、复审、接受或拒绝；所有必需事项终结后才能完成",MINT)
    d.box(44,597,507,100,INK)
    d.text("外部运行基础设施",60,610,12,WHITE,True)
    d.para("AgentTeams v1.2.1  +  Docker / Podman\nMatrix 通信  +  对象存储  +  使用者提供的模型服务\nArchMind 交付角色包与配置工具；外部服务须独立部署。",60,636,475,10.1,MINT,17)
    d.source("源码映射：packages/ 与 skills/（角色和指令）；schemas/（数据契约）；scripts/（构建与校验）。\n技能是声明式指令；安装成功不等于已发生模型调用。当前无 CAD/BIM/OCR 解析器或产品图形界面。")

    d.page(4,"一个树池，连接三个专业","演示案例：虚构社区公园北入口。资料为结构化文字事实，不是实际工程图纸。")
    d.box(44,164,251,258,WHITE)
    d.text("平面关系示意",60,180,12,INK,True)
    d.c.setStrokeColor(HexColor(GREEN));d.c.setLineWidth(2)
    d.c.rect(107,841.89-352,126,126,fill=0,stroke=1)
    d.c.setDash(4,3);d.c.circle(170,841.89-289,76,fill=0,stroke=1);d.c.setDash()
    d.c.setFillColor(HexColor(GREEN));d.c.circle(170,841.89-289,4,fill=1,stroke=0)
    d.box(210,278,21,21,GOLD,2)
    d.line(170,311,220,311,GREEN,1.3)
    d.text("0.40 m",174,314,10,GREEN)
    d.text("净开口 1.00 m × 1.00 m",74,371,10,GRAY)
    d.text("虚线：土球直径 1.20 m",79,391,10,GRAY)
    d.text("黄色：雨水篦子（位置示意）",70,408,8.5,GRAY)
    d.text("已知事实",316,177,13,INK,True)
    d.para("P-001  树池净开口 1.00 m × 1.00 m，土球直径 1.20 m。",316,207,221,10.5)
    d.para("P-002 / S-003  篦子距乔木中心 0.40 m，位于土球平面投影内；竖向关系缺失。",316,265,221,10.5)
    d.para("H-002  树池边缘 102.30、东侧铺装 102.26，坡向箭头仍指向树池。",316,340,221,10.5)
    d.text("从事实到协调行动",44,450,16,INK,True)
    for i,(head,body) in enumerate([
        ("植物 + 园建","净开口与土球尺寸存在实施风险；保留 P-001 引用，提交人类确认尺寸或种植方案。"),
        ("植物 + 雨水海绵","PL-002 与 SS-002 指向同一空间接口；先补设施与土球的竖向关系，避免仅凭投影定论。"),
        ("园建 + 雨水海绵","HS-001 与 SS-003 共享 H-002；先确认坡向设计意图，再复核汇水范围。")]):
        y=491+i*72;d.text(head,44,y,11.5,GREEN,True);d.para(body,188,y,363,10.2)
    d.source("数据：samples/case-001/drawing-facts.json；tests/fixtures/review/。\n预写样例包含 11 条专业意见、4 条跨专业核验记录和 7 项人工确认事项；本轮不生成新的模型审查结果。")

    d.page(5,"创新落在可追溯与可处置","以工程审查的责任关系组织 AI 工作流，形成可复用的领域协作协议。")
    cards=[("01  分专业独立输出","以统一 Schema 记录事实引用、风险、建议与人工复核标记。协调者不得代替缺席的专业 Reviewer。"),
           ("02  保留跨专业因果关系","关联不同专业的 issue_id 与共同事实，区分物理冲突、共享前置缺口和修正顺序；避免简单拼接意见。"),
           ("03  证据链可被检查","定义输入和输出引用、技能版本与哈希；工具支持记录及验证。未产生真实调用时，不将准备文件冒充运行证据。"),
           ("04  人工确认进入状态约束","将待确认数量与任务状态联动；未处理事项、缺失决定或待补证状态不能作为完整审查结束。")]
    for i,(title,body) in enumerate(cards):
        x=44+(i%2)*261;y=168+(i//2)*150
        d.box(x,y,246,132,WHITE)
        d.text(title,x+14,y+15,12,INK,True)
        d.para(body,x+14,y+43,218,10.1)
    d.text("演示中的关键拦截",44,490,16,INK,True)
    d.box(44,528,507,108,INK)
    for i,line in enumerate(["WAITING_HUMAN  |  pending=1  |  decisions=0","校验通过：保留待人工确认状态。","COMPLETED  |  pending=1","校验拒绝：COMPLETED has unprocessed Human Items"]):
        d.text(line,59,541+i*22,10,MINT if i<2 else "#FFD39A",i==0 or i==2)
    d.para("这些创新体现为领域工作流、数据契约与校验工具。项目未进行同类产品基准对比，当前不主张算法首创或性能领先。",44,661,507,10.5)
    d.source("依据：skills/、runbooks/human-gate.md、scripts/validate-run002-gate.py。\n状态校验器检查一致性，不连接 Matrix 认证消息；真实人工身份与消息来源须由 Runtime 接收流程验证。")

    d.page(6,"可复现的验证，明确的指标边界","验证日期：2026-10-13。Python 3.11 / Conda archmind；使用仓库自带合成回归数据。")
    d.box(44,164,507,66,MINT)
    d.text("make verify / make demo / make build  均通过",59,176,14,GREEN,True)
    d.para("覆盖数据边界、链接、资源配置、技能证据工具、人工确认约束及 Schema；成功构建 5 个角色 ZIP 包。",59,201,475,9.6)
    d.text("离线样例评估：18 条记录",44,254,16,INK,True)
    metrics=[("必填字段完整性","171 / 171","要求的字段槽位是否有值"),("证据引用完整性","18 / 18","记录是否通过各自声明的引用检查"),("证据不足的可解释性","6 / 6","适用记录是否明确理由与缺失信息"),("人工确认准备度","7 / 7","适用确认项是否具有必要关联与描述"),("Schema 有效性","11 / 11","已有 Schema 覆盖的专业意见是否合法")]
    d.box(44,294,507,31,INK,4)
    for x,t in [(57,"检查项"),(256,"通过 / 适用"),(361,"检查含义")]:d.text(t,x,301,9.5,WHITE,True)
    for i,(name,value,meaning) in enumerate(metrics):
        y=331+i*49;d.box(44,y,507,44,WHITE,4)
        d.text(name,57,y+12,10.1,INK);d.text(value,256,y+11,11,GREEN,True)
        d.para(meaning,361,y+8,177,9,GRAY,13)
    d.box(44,593,507,69,"#F2E4CE")
    d.para("上述结果是预写合成数据的结构与约束检查，不是 AI 审查准确率、工程合规通过率或效率提升。没有专家 Golden Labels，因此不报告 accuracy、precision、recall 或 F1。",58,606,477,10.2,INK,17)
    d.text("复现路径",44,687,11,GREEN,True)
    d.para("创建并激活 Conda 环境 → make verify → make demo → make build",116,686,435,10.3)
    d.source("证据：evaluation/baseline/result.json（由 make demo 生成）；发布附件中的完整命令输出。\n18 条记录由 11 条专业意见和 7 项人工确认构成；4 条跨专业核验记录不计入这 18 条基准记录。")

    d.page(7,"开放交付，沿验证结果持续迭代","公开源码、可复现案例、标准化角色包和材料制品共同组成参赛交付。")
    d.text("开源与贡献机制",44,163,16,INK,True)
    d.para("项目采用 AGPL-3.0-only。第三方平台、模型与服务遵守各自许可；项目不分发外部模型权重。贡献通过 Issue 与 Pull Request 进行，维护者审查测试、数据来源和许可后合并。",44,199,507,10.6)
    d.text("分阶段推进",44,279,16,INK,True)
    for y,label,body in [(318,"当前 / v0.1.0","完成角色包、技能、数据契约、验证工具和合成样例；可本地执行验证与构建。"),(393,"下一步 / 实证验证","接入独立 AgentTeams Runtime 与模型服务，保留真实调用和人工消息证据；组织专家标注，建立检出率与误报基准。"),(482,"后续 / 场景扩展","在授权数据上实现 CAD/BIM 事实适配与审查界面，再逐步开展实际设计项目试点。")]:
        d.text(label,44,y,11.5,GREEN,True);d.para(body,190,y,361,10.4)
    d.line(44,557,551,557,"#D4DED8")
    d.text("评审访问入口",44,578,16,INK,True)
    for y,label,url in [(617,"源码与复现说明",REPO),(649,"PDF、视频与验证记录",RELEASE),(681,"大赛规则（2026-10-13 核对）","https://www.oschina.net/os2026/")]:
        d.text(label,44,y,9.5,GRAY)
        shown=url.replace("https://","")
        d.text(shown,44,y+14,8.5,GREEN)
        d.c.linkURL(url,(44,841.89-y-28,550,841.89-y-12),relative=0)
    d.source("工程边界：仅用于内部预审；AI 预审不替代法定审查、专业工程师判断和人类总工签字。\n当前未提供生产应用效果数据；CAD/BIM 适配、审查界面和专家标注评估均为后续工作。")
    d.c.save()
    print(f"PDF_PASS pages=7 file={output.name}", flush=True)


SCENES = [
    {"kind":"intro","title":"ArchMind","subtitle":"多专业工程设计预审","points":["AI+ 工业软件赛道","建筑工程 / 研发设计","版本 0.1.0 · 开源工程原型"],"voice":["这是 ArchMind，多专业工程设计预审工具，参赛方向是 AI 加工业软件。","它关注建筑设计中园建、植物和雨水海绵专业之间的接口问题。","本视频使用仓库自带的合成样例，回放真实命令输出，不调用模型。"]},
    {"kind":"architecture","title":"从工程事实到人工确认","subtitle":"角色、证据与责任分开记录","points":["专业 Reviewer 独立输出","协调者关联跨专业问题","核验后交人类总工处置"],"voice":["系统先接收授权的结构化工程事实，由任务管理者分派，协调者组织三个专业分别审查。","专业结果通过统一格式汇集，随后建立跨专业关联，再交证据核验者检查。","关键事项必须等待人类总工确认。角色包在外部 Agent Teams 平台运行。"]},
    {"kind":"terminal","key":"input","title":"01  读取工程事实","subtitle":"九条编号事实，保留来源与缺口","points":["虚构社区公园北入口","图纸引用与事实编号对应","尚无 CAD / BIM 自动解析"],"voice":["首先激活 archmind 的 Conda 环境，运行输入检查命令。","样例有九条结构化事实。例如树池净开口为一米乘一米，土球直径为一点二米。","每条事实保留图纸引用和原始陈述；未提供的调蓄、溢流和排空信息也明确记录。"]},
    {"kind":"terminal","key":"review","title":"02  查看三专业意见","subtitle":"预写回归数据展示，保持事实引用","points":["园建 3 条 / 植物 5 条","雨水海绵 3 条","意见编号关联事实与人工复核"],"voice":["接着查看仓库中的预写专业意见。园建三条，植物五条，雨水海绵三条，共十一条。","这里展示植物问题 P L 零零一。它引用事实 P 零零一，保留来源、风险与人工复核标记。","这些是合成回归记录，本次命令不会生成新的 AI 审查意见。"]},
    {"kind":"terminal","key":"evidence","title":"03  关联问题与缺失资料","subtitle":"跨专业协调建立关系，核验保留证据边界","points":["4 条跨专业核验记录","调蓄与溢流信息不足须补证","7 项待人工确认事项"],"voice":["第三步查看跨专业核验和缺失资料。植物与雨水专业的意见指向同一树池接口，园建坡向又影响汇水范围。","资料不足的意见保留证据不足状态，并列出需要补充的参数。","样例包含四条跨专业核验记录、七项人工确认事项。事实引用能被检查，不代表工程结论已经获得批准。"]},
    {"kind":"terminal","key":"gate","title":"04  验证人工确认拦截","subtitle":"调用现有校验器，拒绝带待办事项提前完成","points":["保留待人工确认状态","仍有待办时拒绝完成","临时测试不改变业务状态"],"voice":["现在实际调用人工确认状态校验器。测试仅在临时合成文件上进行。","当一项工作仍待人工确认时，等待人工状态通过校验。","若把同一任务提前标记为完成，校验器立即拒绝。整个演示没有生成任何人工批准，也没有修改真实业务状态。"]},
    {"kind":"terminal","key":"verify","title":"05  执行项目验证","subtitle":"真实命令输出节选，完整日志随 Release 提供","points":["数据边界与静态结构","技能证据工具与人工确认","Schema 和资源配置"],"voice":["运行 make verify，可以执行项目的本地验证。","检查覆盖公共数据边界、文档链接、资源配置、技能证据工具、人工确认约束和数据格式。","画面展示通过标记，完整输出保存在发布附件中，便于评审复核。"]},
    {"kind":"terminal","key":"baseline","title":"06  查看离线评估","subtitle":"18 条合成记录；结果衡量结构与约束","points":["必填字段 171 / 171","证据引用 18 / 18","不报告准确率或效率提升"],"voice":["运行 make demo，会生成十八条合成基准记录并执行离线评估。","必填字段完整性是一百七十一比一百七十一，证据引用完整性是十八比十八。","其余指标分别检查缺失信息解释、人工确认准备度和数据格式。","这些比例只说明合成样例通过结构检查，不是 AI 审查准确率或工程合规率。"]},
    {"kind":"terminal","key":"build","title":"07  构建五个角色包","subtitle":"同一套技能与契约，打包为可部署角色","points":["协调者与 3 个专业 Reviewer","独立 evidence-verifier","每个 ZIP 附许可和校验值"],"voice":["最后运行 make build，生成五个 Agent Teams 角色包和校验值。","角色分别是审查协调者、园建、植物、雨水海绵与证据核验者。","真实模型执行还需要独立部署运行平台、通信和存储服务，并配置自己的模型服务凭据。"]},
    {"kind":"closing","title":"开放源码，逐步验证落地","subtitle":"AGPL-3.0-only · 完整复现说明与发布制品","points":["当前：命令行工具 + 角色包","下一步：真实链路与专家基准","后续：CAD/BIM 适配与界面"],"voice":["ArchMind 采用 A G P L 三点零开源许可，源码、介绍文档、演示视频和验证记录都在项目仓库与 Release 提供。","下一步将完成真实运行链路与专家标注评估，再扩展 CAD 和 BIM 数据适配。","AI 预审辅助工程协作，最终判断与签字责任属于专业人员。"]}
]


def wrap_pixels(text, font, width):
    result=[]
    for paragraph in text.split("\n"):
        line=""
        for char in paragraph:
            if font.getlength(line+char)>width and line:
                result.append(line);line=char
            else:line+=char
        result.append(line)
    return result


def srt_time(sec):
    millis=round(sec*1000);h,millis=divmod(millis,3600000);m,millis=divmod(millis,60000);s,ms=divmod(millis,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def make_audio(scenes, work):
    all_frames=[];rate=24000;clock=0.0;captions=[]
    for idx,scene in enumerate(scenes):
        scene["start"]=clock
        all_frames.append(b"\0\0"*int(rate*0.65));clock+=0.65
        scene["captions"]=[]
        for j,sentence in enumerate(scene["voice"]):
            txt=work/f"voice-{idx}-{j}.txt";txt.write_text(sentence,encoding="utf-8")
            wav=work/f"voice-{idx}-{j}.wav"
            subprocess.run(["say","-v","Tingting","-r","215","--data-format=LEI16@24000","-o",str(wav),"-f",str(txt)],check=True)
            with wave.open(str(wav),"rb") as w:
                if w.getnchannels()!=1 or w.getframerate()!=rate or w.getsampwidth()!=2:raise RuntimeError("Unexpected voice format")
                chunk=w.readframes(w.getnframes());duration=w.getnframes()/rate
            captions.append((clock,clock+duration,sentence))
            scene["captions"].append((clock-scene["start"],clock-scene["start"]+duration,sentence))
            all_frames.append(chunk);clock+=duration
            all_frames.append(b"\0\0"*int(rate*0.18));clock+=0.18
        all_frames.append(b"\0\0"*int(rate*0.9));clock+=0.9
        scene["duration"]=clock-scene["start"]
        print(f"VOICE_PASS scene={idx+1} duration={scene['duration']:.1f}s",flush=True)
    target=work/"narration.wav"
    with wave.open(str(target),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b"".join(all_frames))
    return target,captions,clock


def build_video(output, records, font, bold, work, evidence_dir, reuse_audio=False):
    import imageio_ffmpeg
    scenes=json.loads(json.dumps(SCENES,ensure_ascii=False))
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    if reuse_audio:
        manifest=json.loads((evidence_dir/"video-manifest.json").read_text(encoding="utf-8"))
        if [s['voice'] for s in scenes] != [s['voice'] for s in manifest['scenes']]:
            raise RuntimeError("Narration changed; regenerate audio")
        def seconds(value):
            h,m,s=value.replace(',', '.').split(':');return int(h)*3600+int(m)*60+float(s)
        captions=[]
        for block in output.with_suffix('.srt').read_text(encoding='utf-8').strip().split('\n\n'):
            lines=block.splitlines();start,stop=lines[1].split(' --> ')
            captions.append((seconds(start),seconds(stop),'\n'.join(lines[2:])))
        for scene,old in zip(scenes,manifest['scenes']):
            scene['start']=old['start'];scene['duration']=old['duration']
            scene['captions']=[(a-old['start'],b-old['start'],text) for a,b,text in captions if old['start']<=a<old['start']+old['duration']]
        total=sum(s['duration'] for s in scenes)
        audio=work/'narration.m4a'
        subprocess.run([ffmpeg,'-y','-loglevel','error','-i',str(output),'-vn','-c:a','copy',str(audio)],check=True)
        print('AUDIO_REUSED unchanged narration',flush=True)
    else:
        audio,captions,total=make_audio(scenes,work)
    fonts={k:ImageFont.truetype(bold if k in ["title","brand","pointhead"] else font,s) for k,s in [("brand",27),("title",52),("sub",26),("code",24),("pointhead",27),("body",28),("small",22),("caption",32),("hero",94)]}
    frames=[];chapter_lines=[]

    def base(scene,idx):
        im=Image.new("RGB",(1920,1080),PAPER);dr=ImageDraw.Draw(im)
        dr.rectangle((0,0,1920,83),fill=INK)
        dr.text((64,26),"ARCHMIND  /  OS2026",font=fonts["brand"],fill=WHITE)
        dr.text((1420,28),"AI+ 工业软件  ·  0.1.0",font=fonts["sub"],fill=MINT)
        dr.text((64,114),scene["title"],font=fonts["title"],fill=INK)
        dr.text((66,184),scene["subtitle"],font=fonts["sub"],fill=GRAY)
        dr.rounded_rectangle((1330,258,1858,876),radius=20,fill=MINT)
        dr.text((1364,291),"本章要点",font=fonts["pointhead"],fill=GREEN)
        y=365
        for number,point in enumerate(scene["points"],1):
            dr.text((1364,y),f"0{number}",font=fonts["pointhead"],fill=GREEN)
            yy=y
            for line in wrap_pixels(point,fonts["body"],380):dr.text((1420,yy),line,font=fonts["body"],fill=INK);yy+=41
            y=max(y+125,yy+39)
        dr.text((1364,803),f"{idx+1:02d} / {len(scenes):02d}  ·  中文命令演示",font=fonts["small"],fill=GRAY)
        dr.rectangle((0,916,1920,1080),fill=INK)
        dr.text((64,1038),"真实命令输出回放 · 合成样例 · 未调用模型",font=fonts["small"],fill=MINT)
        dr.text((1390,1038),"github.com/elsewhere-high/ArchMind",font=fonts["small"],fill=MINT)
        return im

    for idx,scene in enumerate(scenes):
        chapter_lines.append(f"{int(scene['start']//60):02d}:{int(scene['start']%60):02d} {scene['title']}")
        bg=base(scene,idx);key=scene.get("key");display=[]
        if key:
            raw=records[key]["stdout"].strip()
            if key=="verify":raw="\n".join(line for line in raw.splitlines() if any(mark in line for mark in ["_PASS","model_calls=","matrix_messages=","docker_calls=","synthetic_fixture"]))
            if key=="baseline":raw="\n".join(line for line in raw.splitlines() if not line.startswith(("PYTHON","DATASET_SHA")))
            if key=="build":raw+="\n\n"+"\n".join(p.name for p in sorted((ROOT/"packages/dist").glob("*.zip")))+"\nSHA256SUMS"
            for line in raw.splitlines():display.extend(wrap_pixels(line,fonts["code"],1160))
            if len(display)>17:raise RuntimeError(f"Video text overflow {key}: {len(display)} lines")
        moments={0.0,scene["duration"]}
        moments.update(a for a,_,_ in scene["captions"])
        if key:
            moments.update([0.4,0.8,1.2,1.6])
            moments.update(2.0+i*0.12 for i in range(len(display)+1))
        moments=sorted(x for x in moments if x<=scene["duration"])
        for t,end in zip(moments,moments[1:]):
            if end-t<0.01:continue
            im=bg.copy();dr=ImageDraw.Draw(im)
            if key:
                dr.rounded_rectangle((64,258,1286,876),radius=18,fill="#112923")
                dr.rectangle((64,306,1286,308),fill="#365249")
                dr.text((91,271),"Conda: archmind  /  actual command replay",font=fonts["small"],fill="#94B8A9")
                command="(archmind) $ "+records[key]["command"]
                chars=min(len(command),int(len(command)*t/1.6))
                for j,line in enumerate(wrap_pixels(command[:chars],fonts["code"],1160)):
                    dr.text((91,326+j*30),line,font=fonts["code"],fill="#9DE2B8")
                visible=max(0,int((t-2.0)/0.12)+1)
                for j,line in enumerate(display[:visible]):
                    color="#E5EEE9"
                    if "INVALID" in line:color="#F1BC77"
                    if "_PASS" in line or "VALID status" in line:color="#9DE2B8"
                    dr.text((91,370+j*27),line,font=fonts["code"],fill=color)
            elif scene["kind"]=="architecture":
                nodes=[(90,281,1170,92,"授权 Drawing Facts / 结构化工程事实"),(90,415,560,97,"Manager / 任务分派"),(690,415,570,97,"协调者 / 专业组织"),(90,557,354,97,"园建 Reviewer"),(493,557,365,97,"植物 Reviewer"),(907,557,353,97,"雨水海绵 Reviewer"),(90,700,560,114,"跨专业协调 + 证据核验"),(690,700,570,114,"人类总工 / 待确认事项")]
                for x,y,w,h,label in nodes:
                    dr.rounded_rectangle((x,y,x+w,y+h),radius=13,fill=WHITE)
                    dr.text((x+24,y+(h-32)/2),label,font=fonts["body"],fill=INK)
                def arrow(x1,y1,x2,y2):
                    dr.line((x1,y1,x2,y2),fill=GREEN,width=3)
                    angle=math.atan2(y2-y1,x2-x1)
                    for delta in [-0.5,0.5]:
                        dr.line((x2,y2,x2-12*math.cos(angle+delta),y2-12*math.sin(angle+delta)),fill=GREEN,width=3)
                arrow(365,373,365,415);arrow(650,464,690,464)
                dr.line((975,512,975,535),fill=GREEN,width=3)
                dr.line((267,535,1084,535),fill=GREEN,width=3)
                for x in [267,676,1084]:
                    arrow(x,535,x,557);dr.line((x,654,x,677),fill=GREEN,width=3)
                dr.line((267,677,1084,677),fill=GREEN,width=3)
                arrow(370,677,370,700);arrow(650,754,690,754)
                dr.text((90,841),"外部运行平台：AgentTeams + Matrix + 存储 + 模型服务",font=fonts["small"],fill=GRAY)
            else:
                dr.rounded_rectangle((64,258,1286,876),radius=20,fill=INK)
                dr.text((105,312),"ArchMind",font=fonts["hero"],fill=WHITE)
                lines=["工程事实  /  专业意见", "跨专业关系  /  证据核验", "人类确认  /  可追溯处置"] if scene["kind"]=="intro" else ["conda activate archmind", "make verify   /   make demo   /   make build", "github.com/elsewhere-high/ArchMind", "releases/tag/v0.1.0-os2026"]
                for j,line in enumerate(lines):dr.text((109,478+j*75),line,font=fonts["body"],fill=MINT)
                dr.text((109,807),"开源 · 可复现 · 保留专业责任",font=fonts["sub"],fill=GOLD)
            caption=next((text for start,stop,text in scene["captions"] if start<=t<stop+0.19),"")
            for j,line in enumerate(wrap_pixels(caption,fonts["caption"],1760)):
                dr.text((80,938+j*44),line,font=fonts["caption"],fill=WHITE)
            progress=(scene["start"]+t)/total
            dr.rectangle((0,911,int(1920*progress),916),fill=GOLD)
            file=work/f"frame-{len(frames):04d}.png";im.save(file)
            frames.append((file,end-t))
        print(f"FRAMES_PASS scene={idx+1}",flush=True)
    concat=work/"frames.txt"
    concat.write_text("".join(f"file '{file.as_posix()}'\nduration {duration:.6f}\n" for file,duration in frames)+f"file '{frames[-1][0].as_posix()}'\n",encoding="utf-8")
    audio_flags=['-c:a','copy'] if reuse_audio else ['-c:a','aac','-b:a','96k']
    subprocess.run([ffmpeg,"-y","-hide_banner","-loglevel","warning","-f","concat","-safe","0","-i",str(concat),"-i",str(audio),"-c:v","libx264","-preset","veryfast","-threads","4","-crf","23","-r","24","-pix_fmt","yuv420p",*audio_flags,"-movflags","+faststart","-t",f"{total:.6f}",str(output)],check=True)
    srt=output.with_suffix(".srt")
    srt.write_text("\n".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n" for i,(a,b,text) in enumerate(captions,1)),encoding="utf-8")
    (evidence_dir/"chapters.txt").write_text("\n".join(chapter_lines)+"\n",encoding="utf-8")
    (evidence_dir/"video-manifest.json").write_text(json.dumps({"duration_seconds":round(total,3),"width":1920,"height":1080,"fps":24,"audio":"Chinese synthesized narration / macOS Tingting","format":"H.264 + AAC / MP4 / faststart","rendering":"Replay of captured CLI stdout; chapter annotations are editorial, not a product GUI","scenes":[{k:v for k,v in scene.items() if k in ["title","start","duration","key","voice"]} for scene in scenes],"sha256":digest(output)},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"VIDEO_PASS seconds={total:.2f} bytes={output.stat().st_size}",flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--font",default="/System/Library/Fonts/STHeiti Light.ttc")
    parser.add_argument("--font-bold",default="/System/Library/Fonts/STHeiti Medium.ttc")
    parser.add_argument("--pdf-only",action="store_true")
    parser.add_argument("--reuse-capture",action="store_true")
    parser.add_argument("--reuse-audio",action="store_true",help="Reuse unchanged narration from the existing video")
    args=parser.parse_args()
    if not os.environ.get("CONDA_PREFIX"):parser.error("Activate the archmind Conda environment")
    pdf=ROOT/"output/pdf/ArchMind-OS2026-Introduction.pdf"
    video=ROOT/"output/video/ArchMind-OS2026-Demo.mp4"
    evidence=ROOT/"output/submission/verification"
    for p in [pdf.parent,video.parent,evidence]:p.mkdir(parents=True,exist_ok=True)
    if args.reuse_capture:
        records={r["key"]:r for r in json.loads((evidence/"commands.json").read_text(encoding="utf-8"))["commands"]}
    else:records=capture(evidence)
    build_pdf(pdf,args.font,args.font_bold)
    if not args.pdf_only:
        with tempfile.TemporaryDirectory(prefix="archmind-os2026-media-") as tmp:
            build_video(video,records,args.font,args.font_bold,Path(tmp),evidence,args.reuse_audio)


if __name__=="__main__":main()
