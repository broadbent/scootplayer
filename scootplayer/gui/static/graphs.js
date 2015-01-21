function request_time_series_data(buffer, metric) {
    $.ajax({
        url: buffer + '/' + metric,
    }).success(function(data) {
        data_series = [];
        for (var i = 0; i < data[metric].length; i++) {
            data_series.push([data['time_elapsed'][i], data[metric][i]]);
        }
        $.plot($("#" + buffer + '-' + metric), [ data_series ]);
    });

}

function test2() {
    request_time_series_data('playback', 'time_buffer');
    request_time_series_data('playback', 'url_bitrate');
    request_time_series_data('playback', 'time_position');
    request_time_series_data('playback', 'bandwidth');
    request_time_series_data('playback', 'moving_average_occupancy');
    request_time_series_data('playback', 'max_encoded_bitrate');
    request_time_series_data('playback', 'id');
    request_time_series_data('playback', 'moving_average_bandwidth');

    request_time_series_data('download', 'time_buffer');
    request_time_series_data('download', 'url_bitrate');
    request_time_series_data('download', 'time_position');
    request_time_series_data('download', 'bandwidth');
    request_time_series_data('download', 'moving_average_occupancy');
    request_time_series_data('download', 'max_encoded_bitrate');
    request_time_series_data('download', 'id');
    request_time_series_data('download', 'moving_average_bandwidth');
}

var interval = setInterval(test2, 1000);



// window.onresize = function(event) {
//     $.plot($("#moving_average_bandwidth"), [ [[0, 0], [1, 1]] ], { yaxis: { max: 1 } });
// }
