
import { Settings } from 'lucide-react';
import { Icon } from '@iconify/react';

import { AssistantState } from '../types';

interface HeaderProps {
    state: AssistantState;
    onSettingsClick: () => void;
}

export function Header({ state, onSettingsClick }: HeaderProps) {
    return (
        <header className="flex items-center justify-between px-8 py-5 border-b border-orange-800/30 glass-panel mt-4 mx-4 rounded-xl">
            <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center border border-orange-500/30">
                    <Icon icon="mdi:phone" className="w-8 h-8 text-orange-500" />
                </div>
                <span className="text-2xl tracking-wide bg-clip-text text-transparent bg-gradient-to-r from-[#ff4d4d] to-[#f9cb28]" style={{ fontFamily: '"Pacifico", cursive' }}>
                    Echo Voice
                </span>
            </div>

            <div className="flex items-center gap-4">
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${state === 'IDLE' ? 'border-zinc-700 bg-zinc-800/50 text-zinc-400' :
                    state === 'LISTENING' ? 'border-green-500/50 bg-green-900/20 text-green-400 animate-pulse' :
                        state === 'PROCESSING' ? 'border-blue-500/50 bg-blue-900/20 text-blue-400 animate-pulse' :
                            'border-orange-500/50 bg-orange-900/20 text-orange-400'
                    }`}>
                    <div className={`w-2 h-2 rounded-full ${state === 'IDLE' ? 'bg-zinc-500' :
                        state === 'LISTENING' ? 'bg-green-500' :
                            state === 'PROCESSING' ? 'bg-blue-500' :
                                'bg-orange-500'
                        }`} />
                    <span className="text-xs font-semibold uppercase tracking-wider">{state}</span>
                </div>

                <button
                    onClick={onSettingsClick}
                    className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
                >
                    <Settings className="w-5 h-5" />
                </button>
            </div>
        </header>
    );
}
