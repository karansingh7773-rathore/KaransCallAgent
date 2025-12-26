import { useRef, useCallback, useState, useEffect } from 'react';

interface AudioPlayerHook {
    playAudio: (base64Audio: string) => Promise<void>;
    stopAllAudio: () => void;
    playbackAnalyser: AnalyserNode | null;
    isPlaying: boolean;
}

/**
 * Loopback Bridge Audio Player
 * 
 * This hook implements the "Loopback Bridge" pattern to enable proper
 * Acoustic Echo Cancellation (AEC) in browsers.
 * 
 * The Problem:
 * Browsers only apply AEC to audio played through <audio>/<video> elements.
 * Web Audio API output to ctx.destination is "invisible" to AEC.
 * 
 * The Solution:
 * Route: AudioBuffer -> MediaStreamDestination -> <audio> element
 * This "flags" the audio as system output, enabling hardware AEC.
 */
export function useAudioPlayer(): AudioPlayerHook {
    const audioContextRef = useRef<AudioContext | null>(null);
    const mediaStreamDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);
    const audioElementRef = useRef<HTMLAudioElement | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);

    const [playbackAnalyser, setPlaybackAnalyser] = useState<AnalyserNode | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);

    // Initialize the Loopback Bridge on mount
    useEffect(() => {
        const initBridge = async () => {
            try {
                // Create AudioContext
                const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
                audioContextRef.current = ctx;

                // Create MediaStreamDestination - this is the key to the bridge
                const streamDest = ctx.createMediaStreamDestination();
                mediaStreamDestRef.current = streamDest;

                // Create Analyser for visualization
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 512;
                analyser.smoothingTimeConstant = 0.5;
                analyserRef.current = analyser;
                setPlaybackAnalyser(analyser);

                // Connect: Analyser -> MediaStreamDestination
                analyser.connect(streamDest);

                // Create hidden <audio> element for the loopback
                const audioEl = document.createElement('audio');
                audioEl.id = 'aec-loopback-audio';
                audioEl.autoplay = true;
                audioEl.setAttribute('playsinline', ''); // For iOS Safari
                // Hidden but not display:none (some browsers need the element "active")
                audioEl.style.position = 'absolute';
                audioEl.style.left = '-9999px';
                audioEl.style.top = '-9999px';
                document.body.appendChild(audioEl);
                audioElementRef.current = audioEl;

                // Connect the MediaStream to the audio element
                audioEl.srcObject = streamDest.stream;

                console.log('[AudioPlayer] Loopback Bridge initialized');
            } catch (err) {
                console.error('[AudioPlayer] Failed to init bridge:', err);
            }
        };

        initBridge();

        // Cleanup on unmount
        return () => {
            if (audioElementRef.current) {
                audioElementRef.current.pause();
                audioElementRef.current.srcObject = null;
                audioElementRef.current.remove();
            }
            if (audioContextRef.current) {
                audioContextRef.current.close().catch(() => { });
            }
        };
    }, []);

    const playAudio = useCallback(async (base64Audio: string) => {
        try {
            const ctx = audioContextRef.current;
            const analyser = analyserRef.current;
            const audioEl = audioElementRef.current;

            if (!ctx || !analyser) {
                console.error('[AudioPlayer] Bridge not initialized');
                return;
            }

            // Resume context if suspended (autoplay policy)
            if (ctx.state === 'suspended') {
                await ctx.resume();
            }

            // Ensure audio element is playing
            if (audioEl && audioEl.paused) {
                try {
                    await audioEl.play();
                } catch (e) {
                    // Autoplay might be blocked, user interaction will fix this
                    console.warn('[AudioPlayer] Autoplay blocked, will play on next interaction');
                }
            }

            // Decode base64 audio
            const audioData = atob(base64Audio);
            const arrayBuffer = new ArrayBuffer(audioData.length);
            const view = new Uint8Array(arrayBuffer);
            for (let i = 0; i < audioData.length; i++) {
                view[i] = audioData.charCodeAt(i);
            }

            const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

            // Create source and connect through the analyser (which goes to MediaStreamDest)
            const source = ctx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(analyser);
            source.start(0);

            setIsPlaying(true);

            // Track active sources for interruption support
            activeSourcesRef.current.push(source);
            source.onended = () => {
                activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source);
                if (activeSourcesRef.current.length === 0) {
                    setIsPlaying(false);
                }
            };

        } catch (err) {
            console.error('[AudioPlayer] Playback error:', err);
        }
    }, []);

    const stopAllAudio = useCallback(() => {
        activeSourcesRef.current.forEach(source => {
            try {
                source.stop();
            } catch (e) {
                // Already stopped
            }
        });
        activeSourcesRef.current = [];
        setIsPlaying(false);
        console.log('[AudioPlayer] All audio stopped (barge-in)');
    }, []);

    return {
        playAudio,
        stopAllAudio,
        playbackAnalyser,
        isPlaying
    };
}
