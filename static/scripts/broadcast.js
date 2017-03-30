UPDATE = true

function update_log() {
    $.ajax({
        url: LOGEXISTS_URL,
        type: 'GET',
        complete: function (data) {
            get_log();
        },
        error: function (xhr, textStatus, errorThrown) {
            if (xhr.status === 404)
                UPDATE = false;
        }
    });
}

function get_log() {
    $.ajax({
        url: LOG_URL,
        type: 'GET',
        success: function (data) {
            $('#log').html(data)
        },
        complete: function (data) {
            if (UPDATE)
                setTimeout(update_log, 2000);
        }
    });
}
