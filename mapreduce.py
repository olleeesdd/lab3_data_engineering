import pyarrow.parquet as pq
import pyarrow as pa
import pyarrow.fs as fs
from collections import Counter
from itertools import combinations

s3 = fs.S3FileSystem(
    access_key='rustfsadmin',
    secret_key='rustfsadmin123',
    endpoint_override='localhost:9002',
    scheme='http'
)

path = 'hh-lake/java_vacancies.parquet'
table = pq.ParquetFile(path, filesystem=s3)

skills_counter = Counter()
pairs_counter = Counter()
triples_counter = Counter()

for batch in table.iter_batches(batch_size=50000, columns=['name', 'key_skills']):
    names = batch.column('name').to_pylist()
    skills_list = batch.column('key_skills').to_pylist()
    
    for name, skills_str in zip(names, skills_list):
        if not name or 'java' not in name.lower() or 'javascript' in name.lower():
            continue
        if not skills_str:
            continue
            
        s_list = sorted(list(set([s.strip() for s in skills_str.split(';') if s.strip()])))
        if not s_list:
            continue
            
        skills_counter.update(s_list)
        pairs_counter.update(combinations(s_list, 2))
        triples_counter.update(combinations(s_list, 3))

def save_to_s3(counter, filename, is_tuple=False):
    if is_tuple:
        data = [{'skill_1': k[0], 'skill_2': k[1], 'count': v} for k, v in counter.items()] if len(list(counter.keys())[0]) == 2 else [{'skill_1': k[0], 'skill_2': k[1], 'skill_3': k[2], 'count': v} for k, v in counter.items()]
    else:
        data = [{'skill': k, 'count': v} for k, v in counter.items()]
        
    df_res = pa.Table.from_pylist(data)
    pq.write_table(df_res, f'hh-lake/{filename}', filesystem=s3)

save_to_s3(skills_counter, 'result_1.parquet')
save_to_s3(pairs_counter, 'result_2.parquet', is_tuple=True)
save_to_s3(triples_counter, 'result_3.parquet', is_tuple=True)

print("Результаты MapReduce сохранены в S3 (result_1, result_2, result_3)")