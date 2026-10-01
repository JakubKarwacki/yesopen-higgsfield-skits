import subprocess
from brand import BLUE, INK, caption, endcard, notification

NOTES = {
    "notif-1": "Answered your question. Anything else?",
    "notif-2": "12 new reviews answered",
    "notif-3": "Your post is live on Instagram and Facebook",
    "notif-4": "You're #1 for “gym near me”",
}
for name, body in NOTES.items():
    notification(body).save(f"assets/{name}.png")
endcard([[("It’s not you.", INK)], [("It’s your ", INK), ("invoices.", BLUE)]]).save("assets/endcard.png")
caption("It's not you.").save("assets/caption-sample.png")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
    "aevalsrc='0.32*sin(2*PI*1318.5*t)*exp(-9*t)+0.28*sin(2*PI*1975.5*(t-0.11))*exp(-7*(t-0.11))*gte(t\\,0.11)':s=48000:d=0.9",
    "-af", "lowpass=f=7000,afade=t=out:st=0.65:d=0.25", "-ac", "2", "assets/ding.wav"], check=True)
print("assets ok")
