
function takemetodivktbby(id){
    document.getElementById(id).scrollIntoView(true);
}
function takemetodivktbby2(id){
    $('html,body').animate({scrollTop: $("#"+id).offset().top},'slow');
    //document.getElementById(id).scrollIntoView(true);
}
function showhidektbby(divid) {
	var divid=divid;
    var x = document.getElementById(divid);
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}
	