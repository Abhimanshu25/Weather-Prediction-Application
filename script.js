let tempChart, humChart;

function getWeather() {
    const city = document.getElementById("city").value.trim();
    if (!city) {
        alert("Please enter a city name.");
        return;
    }

    fetch("/api/weather", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({city})
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert("Error: " + data.error);
            return;
        }

        document.getElementById("city-name").textContent = `${data.city}, ${data.country}`;
        document.getElementById("description").textContent = data.description;
        document.getElementById("temp").textContent = data.current_temp;
        document.getElementById("feels-like").textContent = data.feels_like;
        document.getElementById("humidity").textContent = data.humidity;
        document.getElementById("pressure").textContent = data.pressure;
        document.getElementById("rain").textContent = data.rain_prediction ? "Yes 🌧" : "No ☀️";

        document.getElementById("result").classList.remove("hidden");

        // Destroy old charts before drawing new ones
        if (tempChart) tempChart.destroy();
        if (humChart) humChart.destroy();

        // Temperature Chart
        const ctxTemp = document.getElementById('tempChart').getContext('2d');
        tempChart = new Chart(ctxTemp, {
            type: 'line',
            data: {
                labels: data.future_times,
                datasets: [{
                    label: 'Temperature (°C)',
                    data: data.future_temp,
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255,107,107,0.2)',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointBackgroundColor: '#ff4757'
                }]
            },
            options: { responsive: true }
        });

        // Humidity Chart
        const ctxHum = document.getElementById('humChart').getContext('2d');
        humChart = new Chart(ctxHum, {
            type: 'line',
            data: {
                labels: data.future_times,
                datasets: [{
                    label: 'Humidity (%)',
                    data: data.future_humidity,
                    borderColor: '#1e90ff',
                    backgroundColor: 'rgba(30,144,255,0.2)',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointBackgroundColor: '#1e90ff'
                }]
            },
            options: { responsive: true }
        });
    })
    .catch(err => {
        alert("An error occurred: " + err);
    });
}
