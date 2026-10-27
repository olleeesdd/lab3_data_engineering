import duckdb
import pandas as pd
from itertools import combinations
from collections import defaultdict

con = duckdb.connect()
con.execute('''
    INSTALL httpfs; LOAD httpfs;
    CREATE SECRET rustfs_secret (
        TYPE s3, KEY_ID 'rustfsadmin', SECRET 'rustfsadmin123',
        ENDPOINT 'localhost:9002', URL_STYLE 'path', USE_SSL false
    );
''')

base_query = '''
    FROM read_parquet('s3://hh-lake/java_vacancies.parquet')
    WHERE name ILIKE '%java%' AND name NOT ILIKE '%javascript%'
      AND salary_from IS NOT NULL AND salary_from > 0
'''

med_query = f"SELECT MEDIAN(salary_from) as base_median {base_query}"
base_median = con.execute(med_query).fetchone()[0]
print(f'Базовая медианная зарплата (Java): {base_median:,.0f} руб.')

df = con.execute(f"SELECT key_skills, salary_from {base_query}").df()

pairs_salaries = defaultdict(list)
triples_salaries = defaultdict(list)

for skills_str, salary in zip(df['key_skills'], df['salary_from']):
    if not isinstance(skills_str, str) or not skills_str.strip(): 
        continue
    
    s_list = sorted(list(set([s.strip() for s in skills_str.split(';') if s.strip()])))
    if not s_list:
        continue
        
    for p in combinations(s_list, 2): 
        pairs_salaries[p].append(salary)
    for t in combinations(s_list, 3): 
        triples_salaries[t].append(salary)

def get_top_insights(salaries_dict, title, min_count=30):
    stats = []
    for k, v in salaries_dict.items():
        if len(v) >= min_count:
            stats.append((k, len(v), pd.Series(v).median()))
    
    stats.sort(key=lambda x: x[2], reverse=True)
    top_up = stats[:5]
    top_down = stats[-5:]
    
    print(f'\n {title} (Наибольшая медианная зарплата)')
    for k, cnt, med in top_up:
        print(f'{k}: {med:,.0f} руб. (встреч: {cnt})')
        
    print(f'\n {title} (Наименьшая медианная зарплата)')
    for k, cnt, med in reversed(top_down):
        print(f'{k}: {med:,.0f} руб. (встреч: {cnt})')

get_top_insights(pairs_salaries, 'Пары навыков')
get_top_insights(triples_salaries, 'Тройки навыков')

print('\n Сравнительный анализ по регионам')
reg_query = f'''
    SELECT area, COUNT(*) as vacancies, MEDIAN(salary_from) as median_salary
    {base_query}
    GROUP BY area
    ORDER BY vacancies DESC
    LIMIT 3
'''
reg_df = con.execute(reg_query).df()
print(reg_df.to_string(index=False))

print('\n Топ 3 навыка в каждом регионе ')
for area in reg_df['area']:
    area_query = f'''
        SELECT clean_skill, COUNT(*) as cnt
        FROM (
            SELECT trim(UNNEST(string_split(key_skills, ';'))) as clean_skill {base_query}
            AND area = '{area}'
        )
        WHERE clean_skill != ''
        GROUP BY clean_skill
        ORDER BY cnt DESC
        LIMIT 3
    '''
    res = con.execute(area_query).df()
    print(f'\nРегион: {area}')
    print(res.to_string(index=False))