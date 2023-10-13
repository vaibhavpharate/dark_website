$(document).ready(function(){
	$('.sidebar').hover(function(){
		$(this).removeClass('transparent_nav')
	},function(){
		$(this).addClass('transparent_nav')
          console.log("Hello")
	})


     $(window).scroll(function(){
var scroll = $(window).scrollTop();
if (scroll >= 57) {
$('#scroll_hide').hide('slow')
}
else{
$('#scroll_hide').show('slow');
}
});


     $('.btn_custom').hover(function(){
          $(this).addClass('light_se');
          $(this).addClass('text-dark');
          $(this).removeClass('bg-transparent');
          $(this).removeClass('main_text');
          console.log("Hello")
     },function () {
          $(this).removeClass('light_se');
          $(this).removeClass('text-dark');
          $(this).addClass('bg-transparent');
          $(this).addClass('main_text');
     })



     // Add Latest Date
     let updated = new Date();
            updated = moment(updated).format("MMMM Do YYYY, h:mm a")
            $('#updated_date').html(updated);
})
// script.js

