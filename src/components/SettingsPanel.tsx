
import { X, Mic2, User, Briefcase } from 'lucide-react';

// Deepgram Aura voices
export const DEEPGRAM_VOICES = [
    { id: 'arcas', name: 'Arcas (Male, Deep)' },
    { id: 'thalia', name: 'Thalia (Female, Warm)' },
    { id: 'andromeda', name: 'Andromeda (Female, Clear)' },
    { id: 'orpheus', name: 'Orpheus (Male, Rich)' },
    { id: 'luna', name: 'Luna (Female, Soft)' },
    { id: 'atlas', name: 'Atlas (Male, Strong)' },
    { id: 'orion', name: 'Orion (Male, Neutral)' },
    { id: 'stella', name: 'Stella (Female, Bright)' },
];

interface SettingsPanelProps {
    isOpen: boolean;
    onClose: () => void;

    // Deepgram Voice
    ttsVoice: string;
    onChangeTtsVoice: (voice: string) => void;

    // Agent Config
    agentPrompt: string;
    onChangeAgentPrompt: (val: string) => void;
    businessDetails: string;
    onChangeBusinessDetails: (val: string) => void;

    // Speech Settings
    speechSpeed: number;
    onChangeSpeed: (val: number) => void;
}

export function SettingsPanel({
    isOpen,
    onClose,
    ttsVoice,
    onChangeTtsVoice,
    agentPrompt,
    onChangeAgentPrompt,
    businessDetails,
    onChangeBusinessDetails,
    speechSpeed,
    onChangeSpeed,
}: SettingsPanelProps) {
    if (!isOpen) return null;

    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm transition-all duration-300">
            <div className="w-full max-w-sm bg-zinc-900/90 border border-zinc-700 rounded-2xl shadow-2xl overflow-hidden glass-panel relative animate-in fade-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-orange-500/10 rounded-lg">
                            <SettingsIcon className="w-5 h-5 text-orange-500" />
                        </div>
                        <h2 className="text-lg font-semibold text-zinc-100">Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-zinc-800 rounded-full text-zinc-400 hover:text-white transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto custom-scrollbar">

                    {/* Voice Selection Section */}
                    <div className="space-y-3">
                        <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                            <Mic2 className="w-3 h-3" /> Voice (Deepgram Aura)
                        </label>

                        <select
                            value={ttsVoice}
                            onChange={(e) => onChangeTtsVoice(e.target.value)}
                            className="w-full bg-zinc-950/50 border border-zinc-800 rounded-xl p-3 text-sm text-zinc-300 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50"
                        >
                            {DEEPGRAM_VOICES.map(voice => (
                                <option key={voice.id} value={voice.id}>{voice.name}</option>
                            ))}
                        </select>

                        <p className="text-xs text-zinc-500 px-1">
                            Ultra-low latency text-to-speech powered by Deepgram Aura.
                        </p>
                    </div>

                    {/* Speech Speed */}
                    <div className="space-y-2">
                        <div className="flex justify-between items-center">
                            <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block">
                                Speech Speed
                            </label>
                            <span className="text-xs text-orange-500 font-mono">{speechSpeed}x</span>
                        </div>
                        <input
                            type="range"
                            min="0.5"
                            max="2.0"
                            step="0.1"
                            value={speechSpeed}
                            onChange={(e) => onChangeSpeed(parseFloat(e.target.value))}
                            className="w-full accent-orange-500 h-1.5 bg-zinc-800 rounded-full appearance-none cursor-pointer"
                        />
                    </div>

                    {/* Agent Persona Section */}
                    <div className="space-y-3 pt-2 border-t border-zinc-800">
                        <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                            <User className="w-3 h-3" /> Agent Persona
                        </label>
                        <textarea
                            value={agentPrompt}
                            onChange={(e) => onChangeAgentPrompt(e.target.value)}
                            placeholder="e.g. You are a helpful assistant for Apex Industries..."
                            className="w-full h-24 bg-zinc-950/50 border border-zinc-800 rounded-xl p-3 text-sm text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 resize-none transition-all"
                        />
                        <p className="text-xs text-zinc-500 px-1">
                            Define the assistant's role and personality.
                        </p>
                    </div>

                    {/* Business Details Section */}
                    <div className="space-y-3">
                        <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                            <Briefcase className="w-3 h-3" /> Business Details
                        </label>
                        <textarea
                            value={businessDetails}
                            onChange={(e) => onChangeBusinessDetails(e.target.value)}
                            placeholder="e.g. Apex Industries sells premium widgets. Opening hours: 9am-5pm..."
                            className="w-full h-24 bg-zinc-950/50 border border-zinc-800 rounded-xl p-3 text-sm text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 resize-none transition-all"
                        />
                        <p className="text-xs text-zinc-500 px-1">
                            Provide context about services, hours, or solutions for the assistant to reference.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Simple Settings Icon component
function SettingsIcon({ className }: { className?: string }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1-1-1.72v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
            <circle cx="12" cy="12" r="3" />
        </svg>
    )
}
