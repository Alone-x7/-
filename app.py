from flask import Flask, jsonify
import json

app = Flask(__name__)

# 读取本地 JSON 文件
def load_data():
    with open("weather.json", "r", encoding="utf-8") as f:
        return json.load(f)

@app.route('/weather')
def weather():
    data = load_data()
    return jsonify(data)

@app.route('/')
def home():
    return "Weather API Running"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)