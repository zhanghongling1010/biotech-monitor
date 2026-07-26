#!/usr/bin/env python3
"""
Biotech Monitor - 每日数据汇总脚本
整合所有数据源，生成网站所需的JSON文件
内容按时间倒序排列（最新在前）
"""
import json
import os
from datetime import datetime
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def sort_by_date_desc(items, date_keys=None):
    """按日期字段倒序排序（最新在前）"""
    if not items:
        return items
    date_keys = date_keys or ['date', 'pub_date', 'timestamp', 'created_at']

    def get_sort_key(item):
        if not isinstance(item, dict):
            return ''
        for key in date_keys:
            if key in item and item[key]:
                return str(item[key])
        return ''

    return sorted(items, key=get_sort_key, reverse=True)


def load_pubmed_data(data_dir):
    """加载PubMed数据"""
    latest_file = os.path.join(data_dir, 'latest.json')
    if os.path.exists(latest_file):
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'papers': {}, 'company_news': [], 'timestamp': None}


def load_company_data(data_dir):
    """加载公司数据"""
    latest_file = os.path.join(data_dir, 'company_latest.json')
    if os.path.exists(latest_file):
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'deals': [], 'clinical': [], 'earnings': [], 'companies': {'international': [], 'china': []}}


def load_bd_news_data(data_dir):
    """加载BD新闻数据"""
    latest_file = os.path.join(data_dir, 'news_latest.json')
    if os.path.exists(latest_file):
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'items': [], 'summary': {'total': 0, 'deals': 0, 'clinical': 0, 'regulatory': 0}}


def merge_data():
    """合并所有数据源"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data', 'daily')

    pubmed_data = load_pubmed_data(data_dir)
    company_data = load_company_data(data_dir)
    bd_news_data = load_bd_news_data(data_dir)

    # 新闻溯源回填:顶刊新闻提到的原论文(可能发表早于7天窗口)补进文献列表
    # extra_news: 上一轮已分离到新闻板块的期刊新闻,继续维护其原论文关联
    try:
        from research_backfill import backfill_from_news
        from collect_pubmed import fetch_article_details
        extra_news = [(n, n.get('source_category') or 'gene_editing')
                      for n in pubmed_data.get('news', [])
                      if n.get('news_type') == 'journal']
        added = backfill_from_news(pubmed_data.get('papers', {}), fetch_article_details,
                                   extra_news=extra_news)
        if added:
            print(f"  新闻溯源: 补充了 {added} 篇原论文")
    except Exception as e:
        print(f"  新闻溯源失败(不影响主流程): {e}")

    # 从BD新闻提取交易和临床数据
    bd_deals = [item for item in bd_news_data.get('items', []) if 'deal' in item.get('categories', [])]
    bd_clinical = [item for item in bd_news_data.get('items', []) if 'clinical' in item.get('categories', [])]
    bd_regulatory = [item for item in bd_news_data.get('items', []) if 'regulatory' in item.get('categories', [])]

    # 标准化新闻数据格式
    def normalize_news_item(item):
        return {
            'title': item.get('title', ''),
            'title_cn': item.get('title_cn', item.get('title', '')),
            'description_cn': item.get('description_cn', ''),
            'description': item.get('description', ''),
            'link': item.get('link', ''),
            'source': item.get('source', ''),
            'date': item.get('date', item.get('pub_date', '')),
            'companies': item.get('companies', []),
            'priority': item.get('priority', 'normal')
        }

    bd_deals = [normalize_news_item(i) for i in bd_deals]
    bd_clinical = [normalize_news_item(i) for i in bd_clinical]
    bd_regulatory = [normalize_news_item(i) for i in bd_regulatory]

    # 按日期倒序排序
    bd_deals = sort_by_date_desc(bd_deals)
    bd_clinical = sort_by_date_desc(bd_clinical)
    bd_regulatory = sort_by_date_desc(bd_regulatory)

    # 标准化公司数据格式
    def normalize_company_deal(item):
        return {
            'title': item.get('title', ''),
            'title_cn': item.get('title_cn', item.get('title', '')),
            'description_cn': item.get('description_cn', item.get('description', '')),
            'description': item.get('description', ''),
            'company': item.get('company', ''),
            'value': item.get('value', ''),
            'date': item.get('date', ''),
            'priority': item.get('priority', 'normal')
        }

    company_deals = [normalize_company_deal(i) for i in company_data.get('deals', [])]
    company_clinical = [normalize_company_deal(i) for i in company_data.get('clinical', [])]

    # 按日期倒序排序
    company_deals = sort_by_date_desc(company_deals)
    company_clinical = sort_by_date_desc(company_clinical)

    # 对PubMed论文按 相关度+影响因子 综合排序(顶刊保证置顶)
    # 同时分离新闻:无摘要的条目(记者报道/行业动态)不进论文板块,单独进新闻板块
    from paper_scoring import sort_papers_by_score, is_top_tier
    sorted_papers = {}
    # 上一轮合并分离出的新闻要继承(latest.json 既是输入又是输出,
    # 不继承的话第二次合并新闻就丢了);按标题去重
    news_items = list(pubmed_data.get('news', []))
    seen_news = {n.get('title', '') for n in news_items}

    def split_news(papers, category):
        research, news = [], []
        for p in papers:
            if (p.get('abstract') or '').strip():
                research.append(p)
            else:
                if p.get('title', '') not in seen_news:
                    p['source_category'] = category
                    p['news_type'] = 'journal'
                    news.append(p)
                    seen_news.add(p.get('title', ''))
        return research, news

    for category, papers in pubmed_data.get('papers', {}).items():
        research, news = split_news(papers, category)
        news_items.extend(news)
        sorted_papers[category] = sort_papers_by_score(research, category)

    # 合并递送系统专题数据（如果存在）
    delivery_file = os.path.join(data_dir, f'delivery_papers_{datetime.now().strftime("%Y%m%d")}.json')
    if os.path.exists(delivery_file):
        try:
            with open(delivery_file, 'r', encoding='utf-8') as f:
                delivery_data = json.load(f)
            delivery_papers = delivery_data.get('papers', [])
            # 为前端统一字段
            for p in delivery_papers:
                p['type'] = 'paper'
                p['companies'] = []
                p['title_cn'] = p.get('title', '')
                p['abstract_cn'] = ''
                p['summary_cn'] = ''
            research, news = split_news(delivery_papers, 'delivery_systems')
            news_items.extend(news)
            sorted_papers['delivery_systems'] = sort_papers_by_score(research, 'delivery_systems')
            print(f"  已合并递送系统专题: {len(research)} 篇")
        except Exception as e:
            print(f"  合并递送数据失败: {e}")

    # 新闻板块:期刊新闻 + 行业新闻(BD/RSS 源),糅合成一个板块
    for item in bd_news_data.get('items', []):
        if item.get('title', '') in seen_news:
            continue
        seen_news.add(item.get('title', ''))
        news_items.append({
            'title': item.get('title', ''),
            'title_cn': item.get('title_cn', item.get('title', '')),
            'summary_cn': item.get('description_cn', ''),
            'abstract': '',
            'journal': item.get('source', '行业新闻'),
            'date': item.get('date', item.get('pub_date', '')),
            'link': item.get('link', ''),
            'authors': [],
            'keywords': item.get('categories', []),
            'source_category': 'industry',
            'news_type': 'industry',
        })
    # 新闻排序:先按日期,再稳定排序把顶刊新闻提到最前
    news_items.sort(key=lambda n: str(n.get('date', '')), reverse=True)
    news_items.sort(key=lambda n: 0 if is_top_tier(n.get('journal')) else 1)
    news_items = news_items[:40]
    print(f"  新闻板块: {len(news_items)} 条")

    # 构建今日重点
    critical = {
        'deals': (company_deals + bd_deals)[:10],
        'clinical': (company_clinical + bd_clinical)[:10],
        'approvals': bd_regulatory[:10]
    }

    # 每日简报
    daily = {
        'deals': company_deals + bd_deals,
        'clinical': company_clinical + bd_clinical,
        'research': []
    }

    # 添加PubMed最新文献到每日简报
    for category, papers in sorted_papers.items():
        if papers:
            for paper in papers[:3]:
                daily['research'].append({
                    'title': paper.get('title', ''),
                    'journal': paper.get('journal', ''),
                    'date': paper.get('date', ''),
                    'authors': paper.get('authors', [])[:3]
                })

    # 对research也排序
    daily['research'] = sort_by_date_desc(daily['research'])

    # 公司列表（带状态标记）
    companies = {
        'international': [],
        'china': []
    }

    for company in company_data.get('companies', {}).get('international', []):
        ticker = company.get('ticker', '')
        updates = company_data.get('company_updates', {}).get(ticker, {})
        companies['international'].append({
            'ticker': ticker,
            'name': company.get('name', ''),
            'type': company.get('type', ''),
            'pipeline': updates.get('has_pipeline_update', False),
            'news': len(updates.get('recent_news', [])) > 0,
            'paper': False
        })

    for company in company_data.get('companies', {}).get('china', []):
        code = company.get('code', '')
        updates = company_data.get('company_updates', {}).get(code, {})
        companies['china'].append({
            'code': code,
            'name': company.get('name', ''),
            'type': company.get('type', ''),
            'pipeline': updates.get('has_pipeline_update', False),
            'news': len(updates.get('recent_news', [])) > 0,
            'paper': False
        })

    # 组装最终数据
    final_data = {
        'timestamp': datetime.now().isoformat(),
        'critical': critical,
        'daily': daily,
        'papers': sorted_papers,
        'news': news_items,
        'companies': companies,
        'earnings': sort_by_date_desc(company_data.get('earnings', []))
    }

    return final_data


def save_combined_data(data, output_dir):
    """保存合并后的数据"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存完整数据
    latest_file = os.path.join(output_dir, 'latest.json')
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 保存压缩版本
    summary = {
        'timestamp': data['timestamp'],
        'critical': data['critical'],
        'daily': data['daily'],
        'papers': {
            'gene_editing': data['papers'].get('gene_editing', [])[:20],
            'cell_therapy': data['papers'].get('cell_therapy', [])[:10],
            'adc': data['papers'].get('adc', [])[:10],
            'glp1': data['papers'].get('glp1', [])[:10],
            'io': data['papers'].get('io', [])[:10]
        },
        'companies': data['companies'],
        'earnings': data['earnings']
    }

    summary_file = os.path.join(output_dir, 'summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"数据已保存到: {output_dir}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '..', 'data', 'daily')

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 合并数据...")

    data = merge_data()
    save_combined_data(data, output_dir)

    # 打印统计
    print("\n数据统计:")
    print(f"  今日重点 - 交易: {len(data['critical']['deals'])}")
    print(f"  今日重点 - 临床: {len(data['critical']['clinical'])}")
    for cat, papers in data['papers'].items():
        print(f"  文献 - {cat}: {len(papers)}")
    print(f"  公司: {len(data['companies']['international'])} 国际 + {len(data['companies']['china'])} 国内")
    print(f"  财报: {len(data['earnings'])}")

    print("\n完成!")


if __name__ == '__main__':
    main()
