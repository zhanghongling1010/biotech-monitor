#!/usr/bin/env python3
"""
Biotech Monitor - PubMed文献抓取
追踪基因编辑、细胞治疗等领域的最新文献
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import os
import re

# ===== Configuration =====
PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
SEARCH_TERMS = {
    'gene_editing': [
        'CRISPR[Title/Abstract] OR Cas9[Title/Abstract] OR base editing[Title/Abstract] OR prime editing[Title/Abstract]',
        'gene therapy[Title/Abstract] OR in vivo gene editing[Title/Abstract]',
        'AAV gene therapy[Title/Abstract] OR lentiviral vector[Title/Abstract]'
    ],
    'cell_therapy': [
        'CAR-T[Title/Abstract] OR cell therapy[Title/Abstract]',
        'iPSC[Title/Abstract] OR stem cell therapy[Title/Abstract]',
        'TCR-T[Title/Abstract] OR NK cell[Title/Abstract]'
    ],
    'adc': [
        'ADC[Title/Abstract] OR antibody drug conjugate[Title/Abstract]',
        'bispecific antibody[Title/Abstract]'
    ],
    'glp1': [
        'GLP-1[Title/Abstract] OR semaglutide[Title/Abstract]',
        'obesity[Title/Abstract] AND metabolic[Title/Abstract]'
    ],
    'io': [
        'checkpoint inhibitor[Title/Abstract] OR PD-1[Title/Abstract] OR PD-L1[Title/Abstract]',
        'tumor immunotherapy[Title/Abstract] OR IO combo[Title/Abstract]'
    ]
}

# 公司相关关键词
COMPANY_KEYWORDS = [
    'Beam', 'Verve', 'Tessera', 'Intellia', 'Editas', 'CRISPR Therapeutics',
    'Prime Medicine', 'Arbor', 'Scribe', 'Metagenomi', 'Sangamo', 'uniQure',
    '博雅', '邦耀', '纽福斯', '信念医药', '本导基因', '瑞风生物'
]

JOURNALS = {
    'nature': 'Nature',
    'science': 'Science',
    'cell': 'Cell',
    'nat_biotechnol': 'Nature Biotechnology',
    'nat_med': 'Nature Medicine',
    'mol THER': 'Molecular Therapy',
    'jci': 'Journal of Clinical Investigation',
    'blood': 'Blood',
    'jco': 'Journal of Clinical Oncology',
    'lancet': 'Lancet',
    'nejm': 'New England Journal of Medicine'
}

# 论文关键词翻译
PAPER_TRANSLATIONS = {
    'CRISPR': 'CRISPR基因编辑',
    'Cas9': 'Cas9基因编辑工具',
    'base editing': '碱基编辑',
    'prime editing': '先导编辑',
    'gene editing': '基因编辑',
    'gene therapy': '基因治疗',
    'gene therapy': '基因疗法',
    'in vivo': '体内',
    'ex vivo': '体外',
    'CAR-T': 'CAR-T细胞疗法',
    'cell therapy': '细胞治疗',
    'iPSC': '诱导多能干细胞',
    'stem cell': '干细胞',
    'ADC': '抗体偶联药物',
    'bispecific': '双特异性抗体',
    'GLP-1': 'GLP-1受体激动剂',
    'semaglutide': '司美格鲁肽',
    'ozempic': ' Ozempic（降糖减重药）',
    'wegovy': 'Wegovy（减重药）',
    'PD-1': 'PD-1免疫检查点',
    'PD-L1': 'PD-L1免疫检查点',
    'checkpoint inhibitor': '免疫检查点抑制剂',
    'immunotherapy': '免疫治疗',
    'tumor': '肿瘤',
    'cancer': '癌症',
    'metastasis': '转移',
    'clinical trial': '临床试验',
    'phase 1': 'I期临床',
    'phase 2': 'II期临床',
    'phase 3': 'III期临床',
    'efficacy': '有效性',
    'safety': '安全性',
    'efficacy and safety': '有效性和安全性',
    'randomized': '随机对照',
    'double-blind': '双盲',
    'placebo': '安慰剂',
    'overall survival': '总生存期',
    'progression-free survival': '无进展生存期',
    'objective response rate': '客观缓解率',
    'patient': '患者',
    'cohort': '队列',
    'study': '研究',
    'data': '数据',
    'results': '结果',
    'showed': '显示',
    'demonstrated': '表明',
    'significantly': '显著',
    'improved': '改善',
    'reduced': '降低',
    'increased': '增加',
    'knockout': '敲除',
    'knock-in': '敲入',
    'delivery': '递送',
    'AAV': '腺相关病毒',
    'lentiviral': '慢病毒载体',
    'mRNA': '信使RNA',
    'siRNA': '小干扰RNA',
    'novel': '新型',
    'new': '新',
    'potential': '潜在',
    'therapeutic': '治疗性',
    'target': '靶点',
    'mechanism': '机制',
    'pathway': '通路',
    'inflammation': '炎症',
    'autoimmune': '自身免疫',
    'rare disease': '罕见病',
    'genetic disease': '遗传病',
    'hematopoietic': '造血干细胞',
    'liver': '肝脏',
    'lung': '肺',
    'brain': '脑',
    'kidney': '肾脏',
    'heart': '心脏',
    'muscle': '肌肉',
    'mouse model': '小鼠模型',
    'non-human primate': '非人灵长类',
    'preclinical': '临床前',
    'translational': '转化医学',
}

def translate_paper_keywords(text):
    """翻译论文关键词"""
    if not text:
        return ''
    result = text
    # 按长度排序，优先匹配长词
    sorted_keywords = sorted(PAPER_TRANSLATIONS.keys(), key=len, reverse=True)
    for kw in sorted_keywords:
        result = result.replace(kw, PAPER_TRANSLATIONS[kw])
        result = result.replace(kw.lower(), PAPER_TRANSLATIONS[kw])
    return result

def generate_paper_summary(article):
    """为论文生成详细的中文摘要 - 包含背景、方法、结果、意义"""
    title = article.get('title', '')
    abstract = article.get('abstract', '')
    text_lower = (title + ' ' + abstract).lower()

    # 标题保持英文
    cn_title = title

    # ===== 1. 研究背景 =====
    background_parts = []

    # 识别疾病/适应症
    disease_map = {
        'melanoma': '黑色素瘤',
        'cancer': '肿瘤',
        'tumor': '肿瘤',
        'oncology': '肿瘤',
        'carcinoma': '癌细胞',
        'breast cancer': '乳腺癌',
        'lung cancer': '肺癌',
        'leukemia': '白血病',
        'lymphoma': '淋巴瘤',
        'hematologic': '血液系统疾病',
        'diabetes': '糖尿病',
        'obesity': '肥胖',
        'metabolic': '代谢性疾病',
        'genetic disease': '遗传病',
        'rare disease': '罕见病',
        'alzheimer': '阿尔茨海默病',
        'parkinson': '帕金森病',
        'neurodegenerative': '神经退行性疾病',
        'cardiovascular': '心血管疾病',
        'liver': '肝脏疾病',
        'kidney': '肾脏疾病',
    }

    diseases = []
    for eng, cn in disease_map.items():
        if eng in text_lower:
            diseases.append(cn)
    diseases = list(dict.fromkeys(diseases))  # 去重保持顺序

    # 识别临床阶段
    phase = ''
    if 'phase 3' in text_lower or 'phase iii' in text_lower:
        phase = 'III期临床试验'
    elif 'phase 2' in text_lower or 'phase ii' in text_lower:
        phase = 'II期临床试验'
    elif 'phase 1' in text_lower or 'phase i' in text_lower:
        phase = 'I期临床试验'

    # 识别研究问题
    if 'resistance' in text_lower or 'resistant' in text_lower:
        background_parts.append('针对治疗耐药性问题')
    if 'metastasis' in text_lower or 'metastatic' in text_lower:
        background_parts.append('针对肿瘤转移机制')
    if 'recurrent' in text_lower:
        background_parts.append('针对复发性疾病')
    if 'refractory' in text_lower or 'relapsed' in text_lower:
        background_parts.append('针对难治性/复发性疾病')

    # 构建背景
    if phase:
        background_parts.insert(0, f'本研究为{phase}')
    elif 'preclinical' in text_lower or 'mouse model' in text_lower:
        background_parts.insert(0, '本研究为临床前动物实验')
    elif 'vivo' in text_lower:
        background_parts.insert(0, '本研究为体内实验')
    elif 'vitro' in text_lower:
        background_parts.insert(0, '本研究为体外实验')

    if diseases:
        background_parts.append(f'研究聚焦{"、".join(diseases[:2])}领域')

    background = '；'.join(background_parts) if background_parts else ''

    # ===== 2. 实验方法 =====
    method_parts = []

    # 技术平台
    tech_map = {
        'crispr': 'CRISPR基因编辑',
        'cas9': 'Cas9基因编辑',
        'base editing': '碱基编辑',
        'prime editing': '先导编辑',
        'car-t': 'CAR-T细胞治疗',
        'car t': 'CAR-T细胞治疗',
        'chimeric antigen receptor': 'CAR-T细胞治疗',
        'adc': '抗体偶联药物(ADC)',
        'antibody-drug conjugate': '抗体偶联药物(ADC)',
        'bispecific': '双特异性抗体',
        'mrna': 'mRNA技术',
        'rna sequencing': 'RNA测序',
        'rnaseq': 'RNA测序',
        'rn-a seq': 'RNA测序',
        'ipsc': '诱导多能干细胞(iPSC)',
        'stem cell': '干细胞技术',
        'gene therapy': '基因治疗',
        'vivio crispr': '体内CRISPR基因编辑',
        'knockout': '基因敲除',
        'knock-in': '基因敲入',
        'sirna': 'siRNA干扰',
        'mirna': 'miRNA研究',
    }

    techs = []
    for eng, cn in tech_map.items():
        if eng in text_lower:
            techs.append(cn)
    techs = list(dict.fromkeys(techs))

    if techs:
        method_parts.append(f"采用{'/'.join(techs[:2])}技术")

    # 实验模型
    if 'patient-derived' in text_lower or 'pdx' in text_lower:
        method_parts.append('使用患者来源肿瘤移植模型(PDX)')
    if 'organoid' in text_lower:
        method_parts.append('使用类器官模型')
    if 'mouse model' in text_lower or 'murine' in text_lower:
        method_parts.append('使用小鼠模型')
    if 'non-human primate' in text_lower or 'primate' in text_lower:
        method_parts.append('使用非人灵长类动物模型')
    if 'single-cell' in text_lower:
        method_parts.append('单细胞测序分析')

    # 检测方法
    if 'rna-seq' in text_lower or 'rnaseq' in text_lower:
        method_parts.append('RNA-seq转录组分析')
    if 'proteomics' in text_lower:
        method_parts.append('蛋白质组学分析')
    if 'bioinformatics' in text_lower:
        method_parts.append('生物信息学分析')
    if 'screening' in text_lower:
        method_parts.append('高通量筛选')

    method = '；'.join(method_parts) if method_parts else '常规实验方法'

    # ===== 3. 实验结果 =====
    result_parts = []

    # 关键发现
    if 'identified' in text_lower or 'discovery' in text_lower:
        result_parts.append('鉴定出关键基因/靶点')
    if 'inhibit' in text_lower or 'suppress' in text_lower or 'repression' in text_lower:
        result_parts.append('发现抑制性作用')
    if 'promote' in text_lower or 'activation' in text_lower or 'induced' in text_lower:
        result_parts.append('发现促进作用')
    if 'migration' in text_lower or 'invasion' in text_lower:
        result_parts.append('抑制细胞迁移和侵袭能力')
    if 'proliferation' in text_lower or 'growth' in text_lower:
        result_parts.append('抑制细胞增殖')
    if 'apoptosis' in text_lower:
        result_parts.append('诱导细胞凋亡')
    if 'survival' in text_lower:
        result_parts.append('延长生存期')
    if 'efficacy' in text_lower or 'effective' in text_lower:
        result_parts.append('显示良好有效性')
    if 'safety' in text_lower or 'tolerable' in text_lower or 'toxicity' in text_lower:
        result_parts.append('安全性可接受')

    # 具体数据（如果摘要中有数字）
    import re
    numbers = re.findall(r'\d+\.?\d*%', abstract)
    if numbers:
        result_parts.append(f'相关数据: {numbers[0]}')

    result = '；'.join(result_parts) if result_parts else '取得了重要的实验数据'

    # ===== 4. 研究意义 =====
    significance_parts = []

    if 'novel' in text_lower or 'new target' in text_lower or 'first time' in text_lower:
        significance_parts.append('为相关疾病治疗提供了新靶点')
    if 'potential therapeutic' in text_lower or 'therapeutic target' in text_lower:
        significance_parts.append('具有潜在治疗应用价值')
    if 'biomarker' in text_lower:
        significance_parts.append('可作为预后生物标志物')
    if 'drug discovery' in text_lower or 'drug development' in text_lower:
        significance_parts.append('为药物研发提供新方向')
    if 'combination' in text_lower or 'synergistic' in text_lower:
        significance_parts.append('支持联合治疗策略')

    # 期刊信息
    if article.get('journal'):
        significance_parts.append(f'发表在《{article["journal"]}》')

    significance = '；'.join(significance_parts) if significance_parts else '对领域发展具有参考价值'

    # ===== 组装完整中文详情 =====
    cn_summary = f"【研究背景】{background}。" if background else ''
    cn_summary += f"\n【实验方法】{method}。"
    cn_summary += f"\n【实验结果】{result}。"
    cn_summary += f"\n【研究意义】{significance}。"

    # 翻译的英文摘要（用于对照）
    cn_abstract = translate_paper_keywords(abstract[:1000]) if abstract else ''

    return cn_title, cn_abstract, cn_summary
    # 翻译的英文摘要（用于对照）
    cn_abstract = translate_paper_keywords(abstract[:800]) if abstract else ''

    return cn_title, cn_abstract, cn_summary

def search_pubmed(query, days_back=7, max_results=50):
    """搜索PubMed"""
    search_url = PUBMED_API + "esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': query,
        'reldate': days_back,
        'datetype': 'pdat',
        'retmax': max_results,
        'retmode': 'json',
        'sort': 'date'
    }

    try:
        response = requests.get(search_url, params=params, timeout=30)
        data = response.json()
        return data.get('esearchresult', {}).get('idlist', [])
    except Exception as e:
        print(f"Search error: {e}")
        return []

def fetch_article_details(pmids):
    """获取文章详细信息"""
    if not pmids:
        return []

    fetch_url = PUBMED_API + "efetch.fcgi"
    params = {
        'db': 'pubmed',
        'id': ','.join(pmids),
        'retmode': 'xml',
        'rettype': 'abstract'
    }

    try:
        response = requests.get(fetch_url, params=params, timeout=30)
        root = ET.fromstring(response.content)

        articles = []
        for article in root.findall('.//PubmedArticle'):
            try:
                medline_citation = article.find('.//MedlineCitation')
                if medline_citation is None:
                    continue

                pmid = medline_citation.find('PMID')
                pmid_text = pmid.text if pmid is not None else ''

                article_data = medline_citation.find('Article')
                if article_data is None:
                    continue

                # 标题
                title_elem = article_data.find('ArticleTitle')
                title = ''.join(title_elem.itertext()) if title_elem is not None else ''

                # 摘要
                abstract_elem = article_data.find('Abstract')
                abstract_parts = []
                if abstract_elem is not None:
                    for elem in abstract_elem.findall('AbstractText'):
                        label = elem.get('Label', '')
                        text = ''.join(elem.itertext())
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                abstract = ' '.join(abstract_parts)

                # 作者
                authors = []
                author_list = article_data.find('AuthorList')
                if author_list is not None:
                    for author in author_list.findall('Author')[:5]:
                        last_name = author.find('LastName')
                        fore_name = author.find('ForeName')
                        if last_name is not None:
                            name = last_name.text
                            if fore_name is not None:
                                name = f"{fore_name.text} {last_name.text}"
                            authors.append(name)

                # 期刊
                journal_elem = article_data.find('Journal')
                journal = ''
                if journal_elem is not None:
                    title_elem = journal_elem.find('Title')
                    journal = title_elem.text if title_elem is not None else ''

                # 日期
                pub_date = ''
                pub_date_elem = article_data.find('ArticleDate')
                if pub_date_elem is not None:
                    year = pub_date_elem.find('Year')
                    month = pub_date_elem.find('Month')
                    day = pub_date_elem.find('Day')
                    if year is not None:
                        pub_date = f"{year.text}-{month.text if month is not None else '01'}-{day.text if day is not None else '01'}"

                # 关键词
                keywords = []
                for kw in article.findall('.//Keyword'):
                    if kw.text:
                        keywords.append(kw.text)

                # 关联公司
                mentioned_companies = []
                text_for_search = title + ' ' + abstract
                for company in COMPANY_KEYWORDS:
                    if company.lower() in text_for_search.lower():
                        mentioned_companies.append(company)

                # 创建临时文章对象用于翻译
                temp_article = {
                    'pmid': pmid_text,
                    'title': title,
                    'abstract': abstract[:500] + '...' if len(abstract) > 500 else abstract,
                    'authors': authors,
                    'journal': journal,
                    'date': pub_date,
                    'keywords': keywords,
                    'companies': mentioned_companies
                }

                # 生成中文翻译
                cn_title, cn_abstract, cn_summary = generate_paper_summary(temp_article)
                temp_article['title_cn'] = cn_title
                temp_article['abstract_cn'] = cn_abstract
                temp_article['summary_cn'] = cn_summary

                articles.append(temp_article)
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        return articles
    except Exception as e:
        print(f"Fetch error: {e}")
        return []

def is_important_journal(journal_name):
    """判断是否重要期刊"""
    if not journal_name:
        return False
    journal_lower = journal_name.lower()
    important_patterns = [
        'nature', 'science', 'cell', 'lancet', 'nejm', 'jama',
        'molecular therapy', 'blood', 'jco', 'jci', 'pnas',
        'embo', 'genome research', 'biotechnology'
    ]
    return any(pattern in journal_lower for pattern in important_patterns)

def categorize_article(article):
    """对文章进行分类"""
    categories = []
    text = (article.get('title', '') + ' ' + article.get('abstract', '')).lower()

    # 基因编辑
    gene_editing_keywords = ['crispr', 'cas9', 'base editing', 'prime editing', 'zinc finger', 'talen', 'gene editing', 'gene therapy', 'aav', 'lentiviral']
    if any(kw in text for kw in gene_editing_keywords):
        categories.append('gene_editing')

    # 细胞治疗
    cell_keywords = ['car-t', 'cell therapy', 'ipsc', 'stem cell', 'tcr-t', 'nk cell', 'tumor infiltrating']
    if any(kw in text for kw in cell_keywords):
        categories.append('cell_therapy')

    # ADC
    adc_keywords = ['adc', 'antibody drug conjugate', 'bispecific', 'payload', 'linker']
    if any(kw in text for kw in adc_keywords):
        categories.append('adc')

    # GLP-1
    glp1_keywords = ['glp-1', 'semaglutide', 'ozempic', 'wegovy', 'obesity', 'weight loss', 'diabetes', 'incretin']
    if any(kw in text for kw in glp1_keywords):
        categories.append('glp1')

    # IO
    io_keywords = ['checkpoint', 'pd-1', 'pd-l1', 'ctla-4', 'immunotherapy', 'io combo', 'tumor microenvironment']
    if any(kw in text for kw in io_keywords):
        categories.append('io')

    return categories if categories else ['other']

def search_companies_news(company_names, days_back=7):
    """搜索公司相关新闻(通过PubMed)"""
    results = []
    for company in company_names:
        query = f'{company}[Title/Abstract]'
        pmids = search_pubmed(query, days_back=days_back, max_results=5)
        if pmids:
            articles = fetch_article_details(pmids)
            results.extend(articles)
    return results

def collect_all_data():
    """收集所有数据"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取PubMed数据...")

    all_papers = {
        'gene_editing': [],
        'cell_therapy': [],
        'adc': [],
        'glp1': [],
        'io': []
    }

    # 按类别搜索
    for category, queries in SEARCH_TERMS.items():
        print(f"\n[{category}] 搜索中...")
        for query in queries:
            pmids = search_pubmed(query, days_back=7, max_results=30)
            if pmids:
                articles = fetch_article_details(pmids)
                for article in articles:
                    cats = categorize_article(article)
                    for cat in cats:
                        if cat in all_papers and article not in all_papers[cat]:
                            all_papers[cat].append(article)
                print(f"  找到 {len(articles)} 篇")

    # 搜索重点公司相关
    print("\n[重点公司] 搜索中...")
    company_news = search_companies_news(COMPANY_KEYWORDS[:10], days_back=14)
    print(f"  找到 {len(company_news)} 篇公司相关")

    return {
        'papers': all_papers,
        'company_news': company_news,
        'timestamp': datetime.now().isoformat()
    }

def save_data(data, output_dir):
    """保存数据"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存今日数据
    today = datetime.now().strftime('%Y-%m-%d')
    today_file = os.path.join(output_dir, f'{today}.json')
    with open(today_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 读取并合并新闻数据
    news_file = os.path.join(output_dir, 'news_latest.json')
    combined_data = dict(data)
    if os.path.exists(news_file):
        try:
            with open(news_file, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            # 从新闻数据提取分类
            items = news_data.get('items', [])
            deals = [i for i in items if 'deal' in i.get('categories', [])]
            clinical = [i for i in items if 'clinical' in i.get('categories', [])]
            regulatory = [i for i in items if 'regulatory' in i.get('categories', [])]
            # 构建critical和daily结构
            combined_data['critical'] = {
                'deals': deals[:5],
                'clinical': clinical[:5],
                'approvals': regulatory[:5]
            }
            combined_data['daily'] = {
                'deals': deals,
                'clinical': clinical,
                'regulatory': regulatory
            }
        except Exception as e:
            print(f"  合并新闻数据失败: {e}")

    # 更新latest链接
    latest_file = os.path.join(output_dir, 'latest.json')
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {today_file}")

def main():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'daily')

    data = collect_all_data()
    save_data(data, output_dir)

    print("\n完成!")

if __name__ == '__main__':
    main()