function request_graphing_data(buffer) {
    if($('#' + buffer + '_graphs').is(':hidden')) {
        return;
    }
    $.ajax({
        url: buffer
    }).success(function(data) {
        for (metric in data) {
            $.plot($("#" + buffer + '-' + metric), [ data[metric] ]);
        }
    });

}

function plot_graphs() {
    request_graphing_data('playback');
    request_graphing_data('download');
}

var interval = setInterval(plot_graphs, 1000);
