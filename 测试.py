import pymysql
import json

# 1. 连接本地 MySQL
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="mydatas",
    database="深圳天气情况",
    charset="utf8"
)

cursor = conn.cursor()

# 2. 查询数据
sql = "SELECT * FROM 深圳天气_清洗 LIMIT 100"
cursor.execute(sql)

rows = cursor.fetchall()

# 3. 获取字段名
columns = [desc[0] for desc in cursor.description]

# 4. 转 JSON
result = []
for row in rows:
    result.append(dict(zip(columns, row)))

# 5. 写入 JSON 文件
with open("weather.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=4)

cursor.close()
conn.close()

print("导出完成：weather.json")