import { useRef, useEffect } from 'react';
import { AssistantState } from '../types';

interface VoiceVisualizerProps {
    state: AssistantState;
    analyser?: AnalyserNode | null;
}

export function VoiceVisualizer({ state, analyser }: VoiceVisualizerProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationRef = useRef<number>();

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Configuration
        const BAR_COUNT = 32;
        const BAR_GAP = 4;

        // Handle High DPI
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const draw = () => {
            ctx.clearRect(0, 0, rect.width, rect.height);

            // If we have an active analyer and are listening/speaking/processing
            if (analyser && (state === 'LISTENING' || state === 'SPEAKING')) {
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                analyser.getByteFrequencyData(dataArray);

                // We want to visualize roughly the voice range, so we pick a subset of bins
                // Creating a simplified bar visualization
                const step = Math.floor(bufferLength / BAR_COUNT);
                const barWidth = (rect.width - (BAR_COUNT - 1) * BAR_GAP) / BAR_COUNT;

                for (let i = 0; i < BAR_COUNT; i++) {
                    const dataIndex = i * step;
                    const value = dataArray[dataIndex];
                    // Normalize height (0-255) to canvas height
                    const percent = value / 255;
                    const barHeight = Math.max(4, percent * rect.height * 0.8);

                    const x = i * (barWidth + BAR_GAP);
                    const y = (rect.height - barHeight) / 2; // Center vertically

                    // Gradient color based on height/intensity
                    const gradient = ctx.createLinearGradient(x, y, x, y + barHeight);
                    gradient.addColorStop(0, '#f97316'); // orange-500
                    gradient.addColorStop(1, '#ef4444'); // red-500

                    ctx.fillStyle = gradient;

                    // Rounded caps style (simplified as rect for performance)
                    ctx.beginPath();
                    ctx.roundRect(x, y, barWidth, barHeight, 4);
                    ctx.fill();
                }
            } else {
                // IDLE Visualization (Breathing/Pulse or flat line)
                const centerY = rect.height / 2;


                // Draw a simple idle line or dots
                ctx.fillStyle = '#3f3f46'; // zinc-700
                const barWidth = (rect.width - (BAR_COUNT - 1) * BAR_GAP) / BAR_COUNT;

                for (let i = 0; i < BAR_COUNT; i++) {
                    const x = i * (barWidth + BAR_GAP);
                    const h = 4;
                    const y = centerY - h / 2;
                    ctx.beginPath();
                    ctx.roundRect(x, y, barWidth, h, 2);
                    ctx.fill();
                }
            }

            animationRef.current = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
        };
    }, [analyser, state]);

    return (
        <div className="h-24 w-full flex items-center justify-center mb-6 overflow-hidden">
            <canvas
                ref={canvasRef}
                className="w-full h-full"
                style={{ width: '100%', height: '100%' }}
            />
        </div>
    );
}
