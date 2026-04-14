// =========================
// OTP INPUT (simple)
// =========================
const inputs = document.querySelectorAll('.otp-input');

inputs.forEach((input, index) => {
  input.addEventListener('input', (e) => {
    e.target.value = e.target.value.replace(/[^0-9]/g, '');

    if (e.target.value && index < inputs.length - 1) {
      inputs[index + 1].focus();
    }
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === "Backspace" && !input.value && index > 0) {
      inputs[index - 1].focus();
    }
  });
});


// =========================
// ⏱ OTP VALID TIMER (5 MIN)
// =========================
let otpTime = 300; // 5 minutes
const otpTimer = document.getElementById("otpTimer");

setInterval(() => {
  if (otpTime > 0) {
    otpTime--;

    let m = Math.floor(otpTime / 60);
    let s = otpTime % 60;

    otpTimer.innerText = `${m}:${s < 10 ? '0' : ''}${s}`;
  } else {
    otpTimer.innerText = "Expired";
  }
}, 1000);


// =========================
// 🔁 RESEND TIMER (30 SEC)
// =========================
let resendTime = 30;
const resendBtn = document.getElementById("resendBtn");

// disable initially
resendBtn.disabled = true;

setInterval(() => {
  if (resendTime > 0) {
    resendTime--;
    resendBtn.innerText = `Resend Code (${resendTime}s)`;
  } else {
    resendBtn.disabled = false;
    resendBtn.innerText = "Resend Code";
  }
}, 1000);
