from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_squared_error
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)

# ---------------- CONFIG ----------------
API_KEY = 'cc1d1d8e616533db983cd0952e8f75ad'
BASE_URL = 'https://api.openweathermap.org/data/2.5/'
DATA_FILE = os.path.join("data", "weather.csv")   # <== CSV in data folder


# ---------------- FUNCTIONS ----------------
def get_current_weather(city):
    """Fetch current weather from OpenWeather API"""
    url = f"{BASE_URL}weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200 or 'main' not in data:
        raise ValueError(data.get('message', 'Error fetching weather data'))
    return {
        'city': data['name'],
        'current_temp': round(data['main']['temp']),
        'feels_like': round(data['main']['feels_like']),
        'temp_min': round(data['main']['temp_min']),
        'temp_max': round(data['main']['temp_max']),
        'humidity': round(data['main']['humidity']),
        'description': data['weather'][0]['description'],
        'country': data['sys']['country'],
        'wind_gust_dir': data['wind']['deg'],
        'pressure': data['main']['pressure'],
        'wind_gust_speed': data['wind']['speed']
    }


def read_historical_data(filename):
    """Read historical CSV"""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} not found. Please provide weather.csv")
    df = pd.read_csv(filename)
    df = df.dropna()
    df = df.drop_duplicates()
    return df


def prepare_data(data):
    """Prepare dataset for rain prediction"""
    le = LabelEncoder()
    all_directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S",
        "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    le.fit(all_directions)
    data['WindGustDir'] = le.transform(data['WindGustDir'])
    data['RainTomorrow'] = LabelEncoder().fit_transform(data['RainTomorrow'])
    x = data[['MinTemp', 'MaxTemp', 'WindGustDir', 'WindGustSpeed', 'Humidity', 'Pressure', 'Temp']]
    y = data['RainTomorrow']
    return x, y, le


def train_rain_model(x, y):
    X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print("Rain Model Error:", mean_squared_error(y_test, y_pred))
    return model


def prepare_regression_data(data, feature):
    X, y = [], []
    for i in range(len(data) - 1):
        X.append(data[feature].iloc[i])
        y.append(data[feature].iloc[i + 1])
    return np.array(X).reshape(-1, 1), np.array(y)


def train_regression_model(X, y):
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model


def predict_future(model, current_value):
    predictions = [current_value]
    for _ in range(5):
        next_value = model.predict(np.array([[predictions[-1]]]))
        predictions.append(next_value[0])
    return predictions[1:]


# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/weather', methods=['POST'])
def api_weather():
    data = request.get_json()
    city = data.get('city')
    if not city:
        return jsonify({'error': 'City is required'}), 400

    try:
        current_weather = get_current_weather(city)
        historical_data = read_historical_data(DATA_FILE)
        X, y, le = prepare_data(historical_data)
        rain_model = train_rain_model(X, y)

        # Wind conversion
        wind_deg = current_weather['wind_gust_dir'] % 360
        compass_points = [
            ("N", 0, 11.25), ("NNE", 11.25, 33.75), ("NE", 33.75, 56.25),
            ("ENE", 56.25, 78.75), ("E", 78.75, 101.25), ("ESE", 101.25, 123.75),
            ("SE", 123.75, 146.25), ("SSE", 146.25, 168.75), ("S", 168.75, 191.25),
            ("SSW", 191.25, 213.75), ("SW", 213.75, 236.25), ("WSW", 236.25, 258.75),
            ("W", 258.75, 281.25), ("WNW", 281.25, 303.75), ("NW", 303.75, 326.25),
            ("NNW", 326.25, 348.75), ("N", 348.75, 360)
        ]
        compass_direction = next(point for point, start, end in compass_points if start <= wind_deg < end)
        compass_direction_encoded = le.transform([compass_direction])[0]

        current_df = pd.DataFrame([{
            'MinTemp': current_weather['temp_min'],
            'MaxTemp': current_weather['temp_max'],
            'WindGustDir': compass_direction_encoded,
            'WindGustSpeed': current_weather['wind_gust_speed'],
            'Humidity': current_weather['humidity'],
            'Pressure': current_weather['pressure'],
            'Temp': current_weather['current_temp']
        }])
        rain_prediction = bool(rain_model.predict(current_df)[0])

        # Regression predictions
        X_temp, y_temp = prepare_regression_data(historical_data, 'Temp')
        X_hum, y_hum = prepare_regression_data(historical_data, 'Humidity')
        temp_model = train_regression_model(X_temp, y_temp)
        hum_model = train_regression_model(X_hum, y_hum)
        future_temp = predict_future(temp_model, current_weather['temp_min'])
        future_humidity = predict_future(hum_model, current_weather['humidity'])

        # Future times
        timezone = pytz.timezone('Asia/Kolkata')
        now = datetime.now(timezone)
        next_hour = now + timedelta(hours=1)
        next_hour = next_hour.replace(minute=0, second=0, microsecond=0)
        future_times = [(next_hour + timedelta(hours=i)).strftime("%H:00") for i in range(5)]

        return jsonify({
            'city': current_weather['city'],
            'country': current_weather['country'],
            'current_temp': current_weather['current_temp'],
            'feels_like': current_weather['feels_like'],
            'humidity': current_weather['humidity'],
            'description': current_weather['description'],
            'pressure': current_weather['pressure'],
            'rain_prediction': rain_prediction,
            'future_temp': future_temp,
            'future_humidity': future_humidity,
            'future_times': future_times
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
