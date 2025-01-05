$(document).ready(function () {

    const hiddenState = localStorage.getItem('iconsHidden');
    if (hiddenState === 'true') {
        $('.lecture-icon').addClass('hidden');
        $('.icon-toggle img').toggleClass('active');
    }



    $('.class-name').click(function () {
        const id = $(this).data('id');
        const openId = $('.course-list.active').data('id');

        $('.course-list.active').slideToggle();
        $('.course-list').removeClass('active');
        $('.class-name[data-id!="' + id + '"]').removeClass('active');
        console.log('$(this).hasClass(\'active\')', $(this).hasClass('active'));
        if ($(this).hasClass('active')) {
            $(this).removeClass('active');
        }
        else {
            $(this).addClass('active');
        }
        const that = $(this);

        if (id != openId) {
            // $('.course-list[data-id="' + id + '"]').css('display', 'flex');
            $('.course-list[data-id="' + id + '"]').slideToggle({
                start: function () {
                    $(this).css('display', 'flex');
                    $(this).addClass('active');
                },
                done: function () {
                    // $(this).css('display', 'flex');
                    $([document.documentElement, document.body]).animate({
                        scrollTop: that.offset().top - that.outerHeight()
                    }, 200);
                }
            });
        }
    })


    $('#reportModal').on('show.bs.modal', function (event) {
        var button = $(event.relatedTarget)
        var reportable_title = button.attr('data-title')
        var reportable_type = button.attr('data-type')
        var reportable_id = button.attr('data-id')
        console.log('reportable_title', reportable_title);
        console.log('reportable_id', reportable_id);
        var modal = $(this)
        modal.find('.modal-title').text('إرسال بلاغ عن خطأ في: ' + reportable_title);
        modal.find('[name="reportable_type"]').val(reportable_type);
        modal.find('[name="reportable_id"]').val(reportable_id);
    });

    $(document).on("submit", "#reportForm", function (e) {
        e.preventDefault();
        var thisForm = $(this);
        var formData = new FormData($(this)[0]);
        formData.append('_token', $('meta[name="csrf-token"]').attr('content'));
        $.ajax({
            type: "POST",
            url: thisForm.attr("action"),
            data: formData,
            cache: false,
            enctype: 'multipart/form-data',
            processData: false,
            contentType: false,
            beforeSend: function () { },
            success: function (data) {
                $('#reportModal').modal('hide');
                $('#reportForm')[0].reset();
                $('#reportForm').find('[name="reportable_type"]').val('');
                $('#reportForm').find('[name="reportable_id"]').val('');
            },
            error: function (err) {
                console.log({
                    ...err
                });
                if (err.responseJSON.errors.description) {
                    console.log("$('#reportForm').find('[name=`description`]')", $(
                        '#reportForm').find('[name="description"]'));
                    $('#reportForm').find('[name="description"]').addClass(
                        'is-invalid');
                    $('#reportForm').find('[name="description"]').next().text(err
                        .responseJSON.errors.description[0]);
                }
            }
        });
    });

    $('.teacher-select').on('change', function () {
        const href = $(this).find('option:selected').attr('href');
        if (href) {
            window.location.href = href;
        }
    });

    $('.pdf-icon').on('click', function () {
        let element = $(this);
        const reportButton = $('#solution-modal .report-btn');

        if (reportButton) {
            console.log('element.attr("data-title")', element.attr('data-title'));
            console.log('element.attr("data-lecture")', element.attr('data-lecture'));
            reportButton.attr('data-title', element.attr('data-title'));
            reportButton.attr('data-id', element.attr('data-lecture'));
        }
        $('#solution-modal .modal-title').text(element.attr('data-title'));
        $('#solution-modal').modal('show');
        let solPage = element.attr('data-page');
      

        if (!document.getElementById("adobe-dc-view")) {
            if (solPage) {
                   setTimeout(() => {
                    var container = $('#viewerContainerImages'),
                    scrollTo = $('#solution-page-'+element.data('page'));
                    container.scrollTop(
                        scrollTo.offset().top - container.offset().top +container.scrollTop()
                    );
                   }, 300);
            }
            return 
        };

        let previewFilePromise;
        if (!window.pdfApis) {
            previewFilePromise = window.adobeDCView.previewFile(
                {
                    content: { location: { url: element.attr('data-fullpath') } },
                    metaData: { fileName: 'حل ' + element.attr('data-title') + '.pdf' }
                },
                {
                    embedMode: "FULL_WINDOW",
                }
            );
            previewFilePromise.then((adobeViewer) => {
                adobeViewer.getAPIs().then((apis) => {
                    window.pdfApis = apis;
                    apis.gotoLocation(Number.parseInt(solPage), 0, 0);
                });

            })
        }
        else {
            console.log('solPage', solPage);
            window.pdfApis.gotoLocation(Number.parseInt(solPage), 0, 0);

        }


    })

});

//.video-video position fixed after scroll down
$(window).scroll(function () {
    var scroll = $(window).scrollTop();
    if (scroll >= 500) {
        $(".video-video").css("position", "fixed");
        $(".video-video").css("top", "0rem");
    } else {
        $(".video-video").css("position", "initial");
    }
    if (scroll >= 50
        // document.body.scrollHeight-window.screen.height-40

    ) {
        $(".icon-toggle").css("left", "-5rem");
    }
    else {
        $(".icon-toggle").css("left", "0rem");
    }
});

$('.icon-toggle').on('click', function () {
    $('.icon-toggle').toggleClass('active');
    $('.icon-toggle img').toggleClass('active');
    $('.lecture-icon').toggleClass('hidden');

    const hiddenState = localStorage.getItem('iconsHidden');
    localStorage.setItem('iconsHidden', !(hiddenState === 'true'));
})