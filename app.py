from flask import Flask, jsonify
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app)  # 解决跨域问题


# 数据库连接
def get_conn():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='mydatas',
        database='深圳天气情况',
        charset='utf8'
    )


# 获取全部数据
@app.route('/weather', methods=['GET'])
def get_weather():
    conn = get_conn()
    cursor = conn.cursor()

    sql = "SELECT * FROM 深圳天气_清洗 LIMIT 100"
    cursor.execute(sql)
    rows = cursor.fetchall()

    # 获取列名
    columns = [col[0] for col in cursor.description]

    result = []
    for row in rows:
        result.append(dict(zip(columns, row)))

    cursor.close()
    conn.close()

    return jsonify(result)


# 按年份查询（重点）
@app.route('/weather/<year>', methods=['GET'])
def get_weather_by_year(year):
    conn = get_conn()
    cursor = conn.cursor()

    sql = f"SELECT * FROM 深圳天气_清洗 WHERE 日期 LIKE '{year}%'"
    cursor.execute(sql)
    rows = cursor.fetchall()

    columns = [col[0] for col in cursor.description]

    result = []
    for row in rows:
        result.append(dict(zip(columns, row)))

    cursor.close()
    conn.close()

    return jsonify(result)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)