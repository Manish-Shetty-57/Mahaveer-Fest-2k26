// Set the date we're counting down to: October 10, 2026, 10:10:00 AM
const countDownDate = new Date("Oct 10, 2026 10:10:00").getTime();

// Update the count down every 1 second
const x = setInterval(function() {

    // Get today's date and time
    const now = new Date().getTime();

    // Find the distance between now and the count down date
    const distance = countDownDate - now;

    // Time calculations for days, hours, minutes and seconds
    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);

    // Display the result in the elements
    document.getElementById("days").innerText = days < 10 ? "0" + days : days;
    document.getElementById("hours").innerText = hours < 10 ? "0" + hours : hours;
    document.getElementById("minutes").innerText = minutes < 10 ? "0" + minutes : minutes;
    document.getElementById("seconds").innerText = seconds < 10 ? "0" + seconds : seconds;

    // If the count down is finished, display a message and a button
    if (distance < 0) {
        clearInterval(x);
        const timerContainer = document.getElementById("timer-container");
        
        timerContainer.innerHTML = `
            <div class="text-center w-full animate-bounce">
                <h3 class='text-3xl font-bold text-green-500 mb-4'>Registration is now OPEN!</h3>
                <a href='#' class='inline-block bg-primary-red text-white font-bold py-3 px-8 rounded-full hover:bg-red-800 transition shadow-lg shadow-red-900/50'>
                    Register Now
                </a>
            </div>
        `;
        document.querySelector("#registration-section p").style.display = 'none';
    }
}, 1000);
