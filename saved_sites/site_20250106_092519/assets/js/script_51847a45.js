

    $(document).on("click", ".cart-class", function () {

        var myurl = $(this).data('url');
        $(".modal-body #ifrm").attr("src", myurl);
    });


    




    function blockui(element) {
            $(element).block({

                message: '<div class="sk-spinner sk-spinner-cube-grid"> <div class="sk-cube"></div>  <div class="sk-cube"></div><div class="sk-cube"></div>' +
                    '<div class="sk-cube"></div>'+
                    ' <div class="sk-cube"></div>' +
                    '  <div class="sk-cube"></div>' +
                    '<div class="sk-cube"></div>'+
                    ' <div class="sk-cube"></div>'+
                    '  <div class="sk-cube"></div>                        </div>',
                css: { border: '0px solid #a00', 'background-color': 'whitesmoke', width: 'auto !important' }
            });
     }

        function unblockui(element) {
                 $(element).unblock();

        }

        function recaptchaExpiredCallback() {
            grecaptcha.reset();
        }

        function recaptchaCallback(recap) {
            $("#Captcha").val(recap);
        }
    