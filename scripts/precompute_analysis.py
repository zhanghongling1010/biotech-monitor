#!/usr/bin/env python3
"""
Biotech Monitor - AI 解读预生成脚本
每天运行一次，为所有内容预生成 AI 深度解读
结果保存到 data/daily/analysis_cache.json
"""
import json
import os
import sys
import time
import requests
from datetime import datetime

# 配置
PROXY_URL = "http://localhost:3000/v1/chat/completions"
MODEL = "MiniMax-M3"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'daily')
OUTPUT_FILE = os.path.join(DATA_DIR, 'analysis_cache.json')

# 系统 prompt
SYSTEM_PROMPT = '你是一位资深的生物医药行业分析师，专注于基因编辑、细胞治疗、抗体药物偶联物(ADC)、GLP-1和肿瘤免疫领域。你的分析风格专业、深入、量化，具备产业视角。'


def call_ai(prompt, max_retries=3):
    """调用 AI API，带重试"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                PROXY_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.7
                },
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                print(f"  Attempt {attempt+1} failed: HTTP {response.status_code}")
                time.sleep(2)
        except Exception as e:
            print(f"  Attempt {attempt+1} error: {e}")
            time.sleep(2)
    return None


def generate_prompt(item, content_type):
    """根据内容类型生成 prompt"""
    if content_type == 'paper':
        return f"""请为以下生物医学论文提供中文深度解读（800字以内）：

【论文】
标题: {item.get('title', 'N/A')}
期刊: {item.get('journal', 'N/A')}
日期: {item.get('date', 'N/A')}

【摘要】
{item.get('abstract', 'N/A')}

请输出以下结构（用【】标记各部分）：
【研究背景】2-3句
【实验设计】方法、模型、技术
【关键数据】量化结果
【核心发现】主要结论
【产业意义】对biotech行业的价值"""
    elif content_type in ('deal', 'approval'):
        return f"""请为以下BD交易/监管动态提供中文分析（500字以内）：

【标题】{item.get('title', 'N/A')}
【公司】{item.get('company', 'N/A')}
【金额】{item.get('value', '未披露')}
【日期】{item.get('date', 'N/A')}

【详情】
{item.get('description_cn', item.get('description', 'N/A'))}

请输出：
【交易概况】简要说明
【战略意义】双方公司价值
【行业影响】对生物医药行业
【风险提示】潜在风险"""
    elif content_type == 'clinical':
        return f"""请为以下临床进展提供中文分析（500字以内）：

【标题】{item.get('title', 'N/A')}
【公司】{item.get('company', 'N/A')}
【适应症】{item.get('indication', 'N/A')}
【阶段】{item.get('stage', 'N/A')}

【详情】
{item.get('description_cn', item.get('description', 'N/A'))}

请输出：
【临床概况】试验信息
【数据解读】关键数据
【竞争格局】同类对比
【上市前景】获批可能性"""
    return None


def main():
    # 加载现有缓存
    cache = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            try:
                cache = json.load(f)
            except:
                cache = {}

    # 加载最新数据
    latest_file = os.path.join(DATA_DIR, 'latest.json')
    if not os.path.exists(latest_file):
        print("latest.json 不存在，请先运行 daily_update.py")
        return

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 收集需要分析的项目
    items_to_analyze = []

    # 论文 - 每个分类只取前3篇（限制数量避免超时）
    for category, papers in data.get('papers', {}).items():
        for paper in papers[:3]:
            pmid = paper.get('pmid') or paper.get('title', '')[:50]
            key = f"paper_{pmid}"
            if key not in cache or not cache[key].get('analysis'):
                items_to_analyze.append((key, paper, 'paper'))

    # 今日重点交易
    for deal in (data.get('critical', {}).get('deals') or []):
        if deal:
            key = f"deal_{(deal.get('title') or '')[:50]}_{deal.get('date') or ''}"
            if key not in cache or not cache[key].get('analysis'):
                items_to_analyze.append((key, deal, 'deal'))

    # 今日重点临床
    for clinical in (data.get('critical', {}).get('clinical') or []):
        if clinical:
            key = f"clinical_{(clinical.get('title') or '')[:50]}_{clinical.get('date') or ''}"
            if key not in cache or not cache[key].get('analysis'):
                items_to_analyze.append((key, clinical, 'clinical'))

    # 监管批准
    for approval in (data.get('critical', {}).get('approvals') or []):
        if approval:
            key = f"approval_{(approval.get('title') or '')[:50]}_{approval.get('date') or ''}"
            if key not in cache or not cache[key].get('analysis'):
                items_to_analyze.append((key, approval, 'approval'))

    print(f"需要分析的项目: {len(items_to_analyze)}")
    print(f"已有缓存: {len(cache)}")

    if not items_to_analyze:
        print("所有项目已缓存，无需重新生成")
        return

    # 生成分析
    success = 0
    failed = 0
    for i, (key, item, content_type) in enumerate(items_to_analyze):
        print(f"[{i+1}/{len(items_to_analyze)}] {key[:60]}...")
        prompt = generate_prompt(item, content_type)
        if not prompt:
            continue

        analysis = call_ai(prompt)
        if analysis:
            cache[key] = {
                'analysis': analysis,
                'item': {
                    'title': item.get('title', ''),
                    'date': item.get('date', ''),
                    'pmid': item.get('pmid', ''),
                    'company': item.get('company', ''),
                },
                'type': content_type,
                'timestamp': datetime.now().isoformat()
            }
            success += 1
            print(f"  ✓ 成功 ({len(analysis)} 字)")
        else:
            failed += 1
            print(f"  ✗ 失败")

        # 每条间隔1秒，避免速率限制
        time.sleep(1)

        # 每10条保存一次
        if (i + 1) % 10 == 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            print(f"  [已保存进度]")

    # 最终保存
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"\n完成: 成功 {success}, 失败 {failed}")
    print(f"缓存总数: {len(cache)}")
    print(f"已保存到: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
