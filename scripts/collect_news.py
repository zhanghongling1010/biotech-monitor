#!/usr/bin/env python3
"""
Biotech Monitor - 临床试验和公司新闻抓取
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os
import re

# ===== Companies to Track =====
COMPANIES = {
    'international': [
        {'ticker': 'BEAM', 'name': 'Beam Therapeutics', 'type': 'Base/Prime Editing'},
        {'ticker': 'VERV', 'name': 'Verve Therapeutics', 'type': 'In Vivo Gene Editing'},
        {'ticker': 'NTLA', 'name': 'Intellia Therapeutics', 'type': 'In Vivo CRISPR'},
        {'ticker': 'EDIT', 'name': 'Editas Medicine', 'type': 'In Vivo CRISPR'},
        {'ticker': 'CRSP', 'name': 'CRISPR Therapeutics', 'type': 'Ex Vivo CRISPR'},
        {'ticker': 'PRME', 'name': 'Prime Medicine', 'type': 'Prime Editing'},
        {'ticker': 'SGMO', 'name': 'Sangamo Therapeutics', 'type': 'Zinc Finger'},
        {'ticker': 'QURE', 'name': 'uniQure', 'type': 'AAV Gene Therapy'},
        {'ticker': 'BMRN', 'name': 'BioMarin', 'type': 'AAV Gene Therapy'},
        {'ticker': 'PTCT', 'name': 'PTC Therapeutics', 'type': 'Gene Therapy'},
        {'ticker': 'RGRX', 'name': 'REGENXBIO', 'type': 'AAV Vector'},
        {'ticker': 'TESS', 'name': 'Tessera Therapeutics', 'type': 'Gene Writing'},
        {'ticker': 'ARBT', 'name': 'Arbor Biotechnologies', 'type': 'CRISPR Discovery'},
        {'ticker': 'SCRIBE', 'name': 'Scribe Therapeutics', 'type': 'CRISPR Delivery'},
        {'ticker': 'MGEN', 'name': 'Metagenomi', 'type': 'In Vivo Gene Editing'},
    ],
    'china': [
        {'code': '688265', 'name': '博雅基因', 'type': 'CRISPR/Cas9'},
        {'code': '688321', 'name': '邦耀生物', 'type': 'Gene Editing'},
        {'code': '688180', 'name': '君实生物', 'type': 'Cell Therapy/IO'},
        {'code': '688235', 'name': '百济神州', 'type': 'Cell Therapy'},
        {'code': '688061', 'name': '瑞风生物', 'type': 'Gene Editing'},
        {'code': '688222', 'name': '纽福斯', 'type': 'Ophthalmology Gene Therapy'},
        {'code': '301080', 'name': '中因科技', 'type': 'Ophthalmology Gene Therapy'},
        {'code': '301073', 'name': '本导基因', 'type': 'Viral Vector'},
        {'code': '301047', 'name': '信念医药', 'type': 'AAV Gene Therapy'},
    ]
}

# ===== Earnings Calendar =====
def get_upcoming_earnings():
    """获取即将发布的财报"""
    # 使用已知的大型biotech公司财报日期
    earnings = [
        # Q4 2023 / Q1 2024
        {'company': 'Beam Therapeutics', 'ticker': 'BEAM', 'date': '2024-02-15', 'exchange': 'NASDAQ'},
        {'company': 'Intellia Therapeutics', 'ticker': 'NTLA', 'date': '2024-02-22', 'exchange': 'NASDAQ'},
        {'company': 'Editas Medicine', 'ticker': 'EDIT', 'date': '2024-02-29', 'exchange': 'NASDAQ'},
        {'company': 'CRISPR Therapeutics', 'ticker': 'CRSP', 'date': '2024-02-27', 'exchange': 'NASDAQ'},
        {'company': 'Verve Therapeutics', 'ticker': 'VERV', 'date': '2024-03-01', 'exchange': 'NASDAQ'},
        {'company': 'uniQure', 'ticker': 'QURE', 'date': '2024-02-28', 'exchange': 'NASDAQ'},
        {'company': 'BioMarin', 'ticker': 'BMRN', 'date': '2024-02-27', 'exchange': 'NASDAQ'},
        # 恒瑞医药 (上交所)
        {'company': '恒瑞医药', 'ticker': '600276', 'date': '2024-04-25', 'exchange': 'SSE'},
        # 百济神州 (科创板)
        {'company': '百济神州', 'ticker': '688235', 'date': '2024-03-28', 'exchange': 'SSE'},
    ]

    # 过滤掉已过期的财报
    today = datetime.now()
    upcoming = [e for e in earnings if datetime.strptime(e['date'], '%Y-%m-%d') >= today]
    return sorted(upcoming, key=lambda x: x['date'])[:20]

# ===== Clinical Trials API =====
def search_clinical_trials(condition, max_results=10):
    """搜索临床试验"""
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        'query.cond': condition,
        'pageSize': max_results,
        'fields': 'NCTId,BriefTitle,OverallStatus,LeadSponsorName,Phase,StartDate',
        'format': 'json'
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            studies = data.get('studies', [])
            return [{
                'nct_id': s.get('nctId'),
                'title': s.get('briefTitle'),
                'status': s.get('overallStatus'),
                'sponsor': s.get('leadSponsorName', {}).get('name') if isinstance(s.get('leadSponsorName'), dict) else s.get('leadSponsorName'),
                'phase': s.get('phase'),
            } for s in studies]
    except Exception as e:
        print(f"Clinical trials API error: {e}")
    return []

# ===== News Sources =====
def scrape_bio_space():
    """抓取BioSpace新闻"""
    url = "https://www.biospace.com/search/?q=gene+therapy&t=article"
    # BioSpace可能需要登录，改用RSS
    return []

def scrape_endpoints_news():
    """抓取Endpoints News"""
    # Endpoints News 通常有RSS feed
    url = "https://endpts.com/feed/"
    try:
        response = requests.get(url, timeout=10)
        # 解析RSS
        # 实现略过，返回空列表
    except:
        pass
    return []

def get_deals_from_news():
    """从新闻汇总BD交易"""
    # 这是一个简化版本，实际应该爬取多个来源
    deals = [
        # 示例数据，需要替换为真实抓取
        {
            'type': 'BD Deal',
            'title': 'BMS与Prime Medicine达成25亿美元合作',
            'company': 'Bristol Myers Squibb / Prime Medicine',
            'value': '$2.5B total',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'priority': 'critical'
        }
    ]
    return deals

# ===== Data Collection =====
def collect_clinical_data():
    """收集临床试验数据"""
    print("[Clinical] 搜索基因编辑相关临床试验...")

    conditions = [
        'gene therapy hemophilia',
        'CRISPR sickle cell',
        'gene editing beta thalassemia',
        'AAV gene therapy',
        'CAR-T lymphoma'
    ]

    all_trials = []
    for condition in conditions:
        trials = search_clinical_trials(condition, max_results=5)
        all_trials.extend(trials)

    # 去重
    seen = set()
    unique_trials = []
    for trial in all_trials:
        if trial['nct_id'] not in seen:
            seen.add(trial['nct_id'])
            unique_trials.append(trial)

    return unique_trials[:20]

def collect_company_updates():
    """收集公司动态"""
    updates = {}

    for company in COMPANIES['international'] + COMPANIES['china']:
        # 简化版：实际应该爬取公司官网/新闻
        updates[company['ticker'] if 'ticker' in company else company['code']] = {
            'name': company['name'],
            'recent_news': [],
            'has_pipeline_update': False,
            'has_clinical': False
        }

    return updates

# ===== Main Collection =====
def collect_all():
    """收集所有数据"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Biotech Monitor Data Collection")
    print("=" * 50)

    data = {
        'deals': get_deals_from_news(),
        'clinical': collect_clinical_data(),
        'earnings': get_upcoming_earnings(),
        'companies': {
            'international': COMPANIES['international'],
            'china': COMPANIES['china']
        },
        'company_updates': collect_company_updates(),
        'timestamp': datetime.now().isoformat()
    }

    return data

def save_data(data, output_dir):
    """保存数据"""
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    today_file = os.path.join(output_dir, f'company_data_{today}.json')

    with open(today_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 更新latest
    latest_file = os.path.join(output_dir, 'company_latest.json')
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n公司数据已保存到: {today_file}")

def main():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'daily')

    data = collect_all()
    save_data(data, output_dir)

    print("\n完成!")

if __name__ == '__main__':
    main()