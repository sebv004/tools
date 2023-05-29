from flask import Flask, request, Response
import ntplib

app = Flask(__name__)

def get_ntp_time(server):
    client = ntplib.NTPClient()
    response = client.request(server)
    return response.tx_time

@app.route('/time-difference')
def calculate_time_difference():
    ntp_server1 = request.args.get('ntp_server1')
    ntp_server2 = request.args.get('ntp_server2')
    num_iterations = request.args.get('num_iterations', default=4, type=int)

    if not ntp_server1 or not ntp_server2:
        return 'Please provide NTP server addresses as query parameters.', 400

    time_diff_sum = 0
    time_diff_min = float('inf')  # Initialize with a high value
    time_diff_max = float('-inf')  # Initialize with a low value

    for _ in range(num_iterations):
        # Get the time from the first NTP server
        time1 = get_ntp_time(ntp_server1)

        # Get the time from the second NTP server
        time2 = get_ntp_time(ntp_server2)

        # Calculate the time difference in milliseconds
        time_diff_ms = abs((time1 - time2) * 1000)

        # Update statistics
        time_diff_sum += time_diff_ms
        time_diff_min = min(time_diff_min, time_diff_ms)
        time_diff_max = max(time_diff_max, time_diff_ms)

    # Calculate the average time difference
    average_time_diff = time_diff_sum / num_iterations

    # Format the response in Prometheus exposition format
    tag = f'ntp_servers="{ntp_server1},{ntp_server2}"'
    response_data = f"""
# HELP time_difference_ms Time difference in milliseconds
# TYPE time_difference_ms gauge
time_difference_ms{{{tag},type="minimum"}} {time_diff_min}
time_difference_ms{{{tag},type="maximum"}} {time_diff_max}
time_difference_ms{{{tag},type="average"}} {average_time_diff}
"""

    return Response(response_data, mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
