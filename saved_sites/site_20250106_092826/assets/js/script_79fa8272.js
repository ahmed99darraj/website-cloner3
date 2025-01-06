
$( window ).ready(function() {

    var hash = window.location.hash;

    if (hash == "#ktbbydate") {
      //var top = document.getElementById("ktbbydate").offsetTop; //Getting Y of target element
      //window.scrollTo(0, top);
		$('html,body').animate({scrollTop: $("#ktbbydate").offset().top},'slow');
		//document.getElementById("ktbbydate").scrollIntoView(true);
    }
});
	