$(document).ready(function (e) {
            function UpdateBezels(obj){
                var defaultTextUpdated = $(obj).find(":selected").text();
                $(obj).parent().find('.selectDefault').text(defaultTextUpdated);

                console.log($(obj).find(":selected").text())
                console.log($(obj).parent().parent().attr('id'))

                var selected_Bezel = $(obj).find(":selected").text()
                var image_ID = $(obj).parent().parent().attr('id')
                var bezelImage = $('#' + image_ID + '_bezelImage')
                bezelImage.attr('src', 'image/' + image_ID + '?bezel=' + encodeURIComponent(selected_Bezel))
                console.log("new bezel")
            }
            function RefreshFilesTable() {
                console.log("func: UpdateFilesList")
                $.ajax({
                    url: 'image_list', // point to server-side URL
                    dataType: 'json', // what to expect back from server
                    cache: false,
                    contentType: false,
                    processData: false,
                    data: false,
                    type: 'get',
                    success: function (response) { // display success response
                        console.log(response);
                        files_table = $('#files_table').html('')
                        $.each(response, function (key, data) {
                            console.log(data);
                            var row = $('<tr>');
                            row.attr('id', key)
                            row.html('<th scope="row"><input name="row-check" class="form-check-input" type="checkbox" value=""></th>')
                            var td = $('<td>').attr('type', 'filename').text(data['src_file'])
                            row.append(td)
                            files_table.append(row);

                            if(key !== 'message') {
                                $('#msg').append(key + ' -> ' + data + '<br/>');
                            } else {
                                $('#msg').append(data + '<br/>');
                            }
                        })
                    },
                    error: function (response) {
                        $('#msg').html(response.message); // display error response
                    }
                });
            }
            RefreshFilesTable();

            function LoadImages() {
                $.ajax({
                    url: 'image_list', // point to server-side URL
                    dataType: 'json', // what to expect back from server
                    cache: false,
                    contentType: false,
                    processData: false,
                    data: false,
                    type: 'get',
                    success: function (response) { // display success response
                        console.log(response);
                        var selected_Bezel = $('#select_bezel').find(":selected").text()
                        devices_table = $('#devices_table')
                        devices_table.html('')
                        $.each(response, function (key, data) {
                            var row = $('<tr>');
                            row.attr('id', key)
                            row.html('<th scope="row"><input name="row-check" class="form-check-input" type="checkbox" value=""></th>')
                            var params = '?bezel=' + encodeURIComponent(selected_Bezel)
                            params += '&stretch=' + $("#radio_stretch").prop("checked")
                            params += '&crop=' + $("#radio_crop").prop("checked")
                            params += '&preview=true'
                            console.log(params)
                            var img = $('<img>').attr('src', 'image/' + key + params)
                            //img.attr('style', "max-width: 400px");
                            img.attr('id', key + '_bezelImage')
                            var td = $('<td>').append(img);
                            row.append(td);
                            console.log('image/' + key + '?bezel=' + encodeURIComponent(selected_Bezel));
                            devices_table.append(row);

                            if(key !== 'message') {
                                $('#msg').append(key + ' -> ' + data + '<br/>');
                            } else {
                                $('#msg').append(data + '<br/>');
                            }
                        })

                    },
                    error: function (response) {
                        $('#msg').html(response.message); // display error response
                    }
                });
            }
            function DeleteFiles() {
                console.log('func: DeleteFiles')
                files = [];
                $("#files_table input[type=checkbox]:checked").each(function () {
                    files.push($(this).parent().next().text())
                });
                console.log(files)
                $.post('delete_images', JSON.stringify({'files': files}), function(response) {
                    console.log(response);
                    RefreshFilesTable();
                });

            }
            function DownloadFiles() {
                console.log('func: DownloadFiles')
                var files = [];
                $("#files_table input[type=checkbox]").each(function () {
                    files.push({
                       'src_file': $(this).parent().next().text(),
                       'bezel_id': $('#select_bezel').find(":selected").text(),
                       'stretch': $("#radio_stretch").prop("checked"),
                       'crop': $("#radio_crop").prop("checked")
                   })
                });
                console.log(files)
                //$.ajax({
                //  url: 'download_images',
                //  data: 'files=' + JSON.stringify({'files': files}),
                //  success: null,
                //  dataType: 'json'
                //});
                //creating an invisible element
                var href = 'download_images'
                href += '?files=' + JSON.stringify({'files': files})
                var element = document.createElement('a');
                element.setAttribute('href', href);
                element.setAttribute('download', 'download.zip');
                // Above code is equivalent to
                // <a href="path of file" download="file name">
                document.body.appendChild(element);
                //onClick property
                element.click();
                document.body.removeChild(element);

                /*
                $.get('download_images', 'files=' + JSON.stringify({'files': files}), function(response) {
                    console.log(response);
                    const blob = new Blob([response.data], {
                          type: 'application/octet-stream'
                        })
                    const filename = 'download.zip'
                    saveAs(blob, filename)
                });
                */
            }

            $('#refresh-files').on('click', function () {
                RefreshFilesTable();
            });
            $('#delete-files').on('click', function () {
                DeleteFiles();
            });
            $('#download-all').on('click', function () {
                DownloadFiles();
            });
            // Header Master Checkbox Event
            $("#masterCheck").on("click", function () {
                console.log('click: masterCheck')
                if ($("input:checkbox").prop("checked")) {
                    $("input:checkbox[name='row-check']").prop("checked", true);
                } else {
                    $("input:checkbox[name='row-check']").prop("checked", false);
                }
            });
            // Check event on each table row checkbox
            $("input:checkbox[name='row-check']").on("change", function () {
                console.log('click: row-check')
                var total_check_boxes = $("input:checkbox[name='row-check']").length;
                var total_checked_boxes = $("input:checkbox[name='row-check']:checked").length;

                // If all checked manually then check master checkbox
                if (total_check_boxes === total_checked_boxes) {
                    $("#masterCheck").prop("checked", true);
                }
                else {
                    $("#masterCheck").prop("checked", false);
                }
            });

            $.ajax({
                url: 'bezel_list', // point to server-side URL
                dataType: 'json', // what to expect back from server
                cache: false,
                contentType: false,
                processData: false,
                data: false,
                type: 'get',
                success: function (response) { // display success response
                    console.log(response);
                    bezels = response;
                },
                error: function (response) {
                    $('#msg').html(response.message); // display error response
                }
            }).done(function(bezels){
                console.log("bezels:")
                console.log(bezels)
                var sel = $('#select_bezel')
                sel.append($('<option>').attr('value', 'Auto').text('Auto'))
                $.each(bezels, function (k, v) {
                    var opt = $('<option>').attr('value', k).text(k)
                    sel.append(opt)
                })

                $('#select_bezel').on('change', function () {
                    LoadImages();

                });

            });
			$('#refresh').on('click', function () {
                LoadImages()
            });
			$('#upload').on('click', function () {
				var form_data = new FormData();
				var ins = document.getElementById('multiFiles').files.length;

				if(ins == 0) {
					$('#msg').html('<span style="color:red">Select at least one file</span>');
					return;
				}
				for (var x = 0; x < ins; x++) {
					form_data.append("files[]", document.getElementById('multiFiles').files[x]);
				}
				$.ajax({
					url: 'upload_file', // point to server-side URL
					dataType: 'json', // what to expect back from server
					cache: false,
					contentType: false,
					processData: false,
					data: form_data,
					type: 'post',
					success: function (response) { // display success response
						$('#msg').html('');
						$.each(response, function (key, data) {
							if(key !== 'message') {
								$('#msg').append(key + ' -> ' + data + '<br/>');
							} else {
								$('#msg').append(data + '<br/>');
							}
						})
						RefreshFilesTable();
					},
					error: function (response) {
						$('#msg').html(response.message); // display error response
					}
				});
				RefreshFilesTable();
			});
			$('#refresh-device-images').on('click', function () {
                LoadImages()
            });
		});