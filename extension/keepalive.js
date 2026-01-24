console.log("[Tarabean KeepAlive] Injecting Anti-Freeze...");

// 1. Web Audio API Trick (Silent Oscillator)
// Browsers rarely throttle tabs playing audio.
try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.frequency.value = 100;
        gain.gain.value = 0.001; // Effectively silent

        osc.start();
        console.log("[Tarabean KeepAlive] Silent Audio Started.");

        // Ensure context resumes if suspended
        setInterval(() => {
            if (ctx.state === 'suspended') ctx.resume();
        }, 5000);
    }
} catch (e) {
    console.error("[Tarabean KeepAlive] Audio Failed:", e);
}

// 2. Web Worker Trick (Separate Thread)
const workerBlob = new Blob([`
    setInterval(() => {
        postMessage("tick");
    }, 1000);
`], { type: "text/javascript" });

const worker = new Worker(URL.createObjectURL(workerBlob));
worker.onmessage = () => {
    // console.log("Worker tick");
};
console.log("[Tarabean KeepAlive] Worker Started.");
