import duckdb

con = duckdb.connect()
con.execute('''
    INSTALL httpfs; LOAD httpfs;
    CREATE SECRET rustfs_secret (
        TYPE s3, KEY_ID 'rustfsadmin', SECRET 'rustfsadmin123',
        ENDPOINT 'localhost:9002', URL_STYLE 'path', USE_SSL false
    );
''')

mr_query = """
    SELECT skill, count 
    FROM read_parquet('s3://hh-lake/result_1.parquet') 
    ORDER BY count DESC 
    LIMIT 1
"""
mr_res = con.execute(mr_query).fetchone()

ddb_query = """
    SELECT trim(UNNEST(string_split(key_skills, ';'))) as skill, COUNT(*) as cnt
    FROM read_parquet('s3://hh-lake/java_vacancies.parquet')
    WHERE name ILIKE '%java%' AND name NOT ILIKE '%javascript%'
    GROUP BY skill 
    ORDER BY cnt DESC 
    LIMIT 1
"""
ddb_res = con.execute(ddb_query).fetchone()

print(f'MapReduce: {mr_res[1]} вхождений (навык: {mr_res[0]})')
print(f'DuckDB:    {ddb_res[1]} вхождений (навык: {ddb_res[0]})')

if mr_res[1] == ddb_res[1]:
    print('Верификация пройдена, результаты совпадают')
else:
    print('Ошибка верификации, есть расхождения')