function update_log() {
    $.ajax({
        url: '/maps/api/log/' + OBJECT_PK,
        type: 'GET',
        success: function (data) {
            $('#log').html(data)
        },
        complete: function (data) {
            setTimeout(update_log, 2000);
        },
        error: function (xhr, textStatus, errorThrown) {
            if(xhr.status==404) {
                loc = location;
                location = loc.protocol + '//' + loc.host + loc.pathname + loc.search;
            }
        }
    });
}
