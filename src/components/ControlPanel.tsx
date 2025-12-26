
import { Mic, MicOff } from 'lucide-react';
import { AssistantState } from '../types';

interface ControlPanelProps {
    isMicActive: boolean;
    toggleMic: () => void;
    state: AssistantState;
}

export function ControlPanel({ isMicActive, toggleMic, state }: ControlPanelProps) {
    return (
        <div className="flex flex-col items-center gap-6">
            <div className="flex justify-center items-center gap-6">
                <button
                    onClick={toggleMic}
                    className={`relative group w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 ${isMicActive
                        ? 'bg-red-500/20 border-2 border-red-500 text-red-500 shadow-[0_0_30px_rgba(239,68,68,0.4)]'
                        : 'bg-zinc-800 border-2 border-zinc-700 text-zinc-400 hover:border-orange-500/50 hover:text-orange-500'
                        }`}
                >
                    {isMicActive ? <MicOff className="w-8 h-8" /> : <Mic className="w-8 h-8" />}

                    {/* Ripple Effect ring */}
                    {isMicActive && (
                        <div className="absolute inset-0 rounded-full border border-red-500 animate-ping opacity-75" />
                    )}
                </button>
            </div>

            <div className="text-center text-xs text-zinc-500 uppercase tracking-widest">
                {state === 'IDLE' ? 'Tap to Speak' : state}
            </div>
        </div>
    );
}
