"""
Cairo-First Weather Dashboard — Flask front-end.
Enter a city, see current conditions + a 3-day forecast. Defaults to
Cairo (home base) but works for any city Open-Meteo's geocoder knows.
"""

from datetime import date, timedelta

from flask import Flask, render_template, request

from weather_service import get_weather, weather_label

DEFAULT_CITY = "Cairo"


def create_app():
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        city = request.form.get("city", DEFAULT_CITY).strip() or DEFAULT_CITY
        data, source, found = get_weather(city)

        forecast_days = []
        if found:
            today = date.today()
            for day in data["forecast"]:
                forecast_date = today + timedelta(days=day["day_offset"])
                forecast_days.append({
                    "label": forecast_date.strftime("%A"),
                    "temp_max_c": day["temp_max_c"],
                    "temp_min_c": day["temp_min_c"],
                    "description": weather_label(day["weather_code"]),
                })

        return render_template(
            "index.html",
            city_input=city,
            data=data,
            found=found,
            source=source,
            forecast_days=forecast_days,
            weather_label=weather_label,
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
