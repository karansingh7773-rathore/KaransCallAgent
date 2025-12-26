import { useState, useRef, useCallback, useEffect } from 'react';
import '../types/vad.d.ts';

interface AudioRecorderHook {
    isRecording: boolean;
    startRecording: () => void;
    stopRecording: () => void;
    error: string | null;
    analyser: AnalyserNode | null;
    isSpeechDetected: boolean;
}

/**
 * Audio Recorder with VAD (Voice Activity Detection)
 * 
 * Uses strict AEC constraints to work with the Loopback Bridge pattern.
 * The browser's AEC will now properly cancel the audio element output.
 */
export function useAudioRecorder(
    onAudioData: (base64Data: string) => void,
    onSpeechStart?: () => void,
    onLog?: (msg: string) => void
): AudioRecorderHook {

    const [isRecording, setIsRecording] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
    const [isSpeechDetected, setIsSpeechDetected] = useState(false);

    const vadRef = useRef<any>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);

    const log = (msg: string) => {
        console.log("[VAD]", msg);
        if (onLog) onLog(msg);
    };

    const floatTo16BitPCM = (input: Float32Array): Int16Array => {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output;
    };

    const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    };

    const startRecording = useCallback(async () => {
        try {
            setError(null);

            // Check if VAD is loaded from CDN
            if (!window.vad) {
                throw new Error("VAD library not loaded. Please check CDN script in index.html");
            }

            log("Requesting microphone with STRICT AEC constraints...");

            // STRICT AEC Constraints for Loopback Bridge
            // These constraints tell the browser to aggressively cancel
            // any audio being played through <audio> elements
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    // Mono channel for cleaner processing
                    channelCount: 1,

                    // CRITICAL: Enable all audio processing
                    echoCancellation: { ideal: true },
                    noiseSuppression: { ideal: true },
                    autoGainControl: { ideal: true },

                    // Prefer default device (usually has best AEC)
                    // deviceId: 'default',

                    // Sample rate for speech recognition
                    sampleRate: { ideal: 16000 },
                }
            });
            streamRef.current = stream;

            // Log the actual constraints applied
            const track = stream.getAudioTracks()[0];
            const settings = track.getSettings();
            log(`Mic settings: echoCancellation=${settings.echoCancellation}, noiseSuppression=${settings.noiseSuppression}, autoGainControl=${settings.autoGainControl}`);

            log("Initializing VAD from CDN...");

            // Create VAD instance using CDN-loaded library
            const micVAD = await window.vad.MicVAD.new({
                stream: stream,

                // Speech detection thresholds
                positiveSpeechThreshold: 0.6,    // Higher = less sensitive (ignore quiet echoes)
                negativeSpeechThreshold: 0.4,   // Lower = faster speech end detection

                // Frame-based timing controls
                minSpeechFrames: 5,              // ~150ms minimum speech to trigger
                preSpeechPadFrames: 6,           // Include 180ms before speech start
                redemptionFrames: 10,            // Wait 300ms before declaring speech end

                onSpeechStart: () => {
                    log("🎤 Speech DETECTED");
                    setIsSpeechDetected(true);
                    if (onSpeechStart) onSpeechStart();
                },

                onSpeechEnd: (audio: Float32Array) => {
                    log(`📤 Speech ended, sending ${audio.length} samples...`);
                    setIsSpeechDetected(false);
                    const pcm = floatTo16BitPCM(audio);
                    const b64 = arrayBufferToBase64(pcm.buffer as ArrayBuffer);
                    onAudioData(b64);
                },

                onVADMisfire: () => {
                    log("❌ VAD misfire (too short)");
                    setIsSpeechDetected(false);
                }
            });

            vadRef.current = micVAD;
            micVAD.start();
            setIsRecording(true);
            log("✅ VAD running with Loopback Bridge AEC");

            // Setup analyser for visualization
            const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            audioContextRef.current = audioCtx;
            const source = audioCtx.createMediaStreamSource(stream);
            const node = audioCtx.createAnalyser();
            node.fftSize = 512;
            node.smoothingTimeConstant = 0.5;
            source.connect(node);
            setAnalyser(node);

        } catch (err: any) {
            console.error("VAD Error:", err);
            setError(err.message);
            log(`❌ Error: ${err.message}`);
        }
    }, [onAudioData, onSpeechStart]);

    const stopRecording = useCallback(() => {
        log("Stopping VAD...");

        if (vadRef.current) {
            vadRef.current.pause();
            vadRef.current = null;
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(t => t.stop());
            streamRef.current = null;
        }

        if (audioContextRef.current) {
            audioContextRef.current.close().catch(e => console.error(e));
            audioContextRef.current = null;
        }

        setIsRecording(false);
        setIsSpeechDetected(false);
        setAnalyser(null);
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (vadRef.current) {
                vadRef.current.pause();
            }
        };
    }, []);

    return {
        isRecording,
        startRecording,
        stopRecording,
        error,
        analyser,
        isSpeechDetected
    };
}
