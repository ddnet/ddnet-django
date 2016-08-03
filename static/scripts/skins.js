function renderSkin(skin) {
    //create canvas
    var canvas = document.createElement("canvas");
    canvas.width = "96";
    canvas.height = "64";

    var ctx = canvas.getContext("2d");
    ctx.drawImage(skin, 192, 64, 64, 32, 10, 33, 60, 30); //back feet shadow
    ctx.drawImage(skin, 192, 32, 64, 32, 8, 32, 64, 32); //back feet
    ctx.drawImage(skin, 96, 0, 96, 96, 16, 0, 64, 64); //body shadow
    ctx.drawImage(skin, 0, 0, 96, 96, 16, 0, 64, 64); //body
    ctx.drawImage(skin, 192, 64, 64, 32, 26, 33, 60, 30); //front feet shadow
    ctx.drawImage(skin, 192, 32, 64, 32, 24, 32, 64, 32); //front feet
    ctx.drawImage(skin, 64, 96, 32, 32, 36, 14, 24, 24); //left eye
    //right eye (flip and draw)
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(skin, 64, 96, 32, 32, -69, 14, 24, 24);
    ctx.restore();

    //replace with image
    skin.parentNode.replaceChild(canvas, skin);
}

function postAddSkinToDownload(skinIndex, skinName) {
    $.ajax({
        url: 'add-to-download',
        type: 'post',
        data: {
            skinName: skinName,
            csrfmiddlewaretoken: CURRENT_CSRF_TOKEN
        },
        success: function (data) {
            //hide 'add to download' button
            $('#skin-add-to-download-button-' + skinIndex).hide();
            //show 'remove from download' button
            $('#skin-remove-from-download-button-' + skinIndex).show();
            console.log(data);
            $('#selected-skins-num-span').text(data);
        }
    });
}

function postRemoveSkinFromDownload(skinIndex, skinName) {
    $.ajax({
        url: 'remove-from-download',
        type: 'post',
        data: {
            skinName: skinName,
            csrfmiddlewaretoken: CURRENT_CSRF_TOKEN
        },
        success: function (data) {
            //show 'add to download' button
            $('#skin-add-to-download-button-' + skinIndex).show();
            //hide 'remove from download' button
            $('#skin-remove-from-download-button-' + skinIndex).hide();
            console.log(data);
            $('#selected-skins-num-span').text(data);
        }
    });
}

function postClearDownloadList() {
    $.ajax({
        url: 'clear-download-list',
        type: 'post',
        data: {
            csrfmiddlewaretoken: CURRENT_CSRF_TOKEN
        },
        success: function (data) {
            $('.skin-add-to-download-button').show();
            $('.skin-remove-from-download-button').hide();
            $('#selected-skins-num-span').text(0);
        }
    });
}