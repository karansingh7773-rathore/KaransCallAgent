import { useState, useEffect } from 'react';
import { X, Info } from 'lucide-react';

export function StartupDialog() {
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        // Show dialog on mount
        setIsOpen(true);
    }, []);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-2xl shadow-2xl p-6 relative animate-in zoom-in-95 duration-200">

                <button
                    onClick={() => setIsOpen(false)}
                    className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>

                <div className="flex flex-col items-center text-center space-y-4">
                    <div className="p-3 bg-blue-500/10 rounded-full">
                        <Info className="w-8 h-8 text-blue-500" />
                    </div>

                    <h2 className="text-xl font-semibold text-white">Quick Start Guide</h2>

                    <div className="text-zinc-400 text-sm space-y-3 leading-relaxed">
                        <p>
                            To ensure custom instructions are applied correctly:
                        </p>
                        <ol className="list-decimal list-inside text-left space-y-2 bg-zinc-950/50 p-4 rounded-xl border border-zinc-800">
                            <li><span className="text-zinc-200 font-medium">Run the Agent</span> first.</li>
                            <li>Connect to the room.</li>
                            <li>Then open <span className="text-orange-500 font-medium">Settings</span> and fill in the Persona/Business details.</li>
                        </ol>
                        <p>
                            The agent will dynamically update its instructions when you modify them while connected.
                        </p>
                    </div>

                    <button
                        onClick={() => setIsOpen(false)}
                        className="w-full py-2.5 px-4 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 transition-colors mt-2"
                    >
                        Got it
                    </button>
                </div>
            </div>
        </div>
    );
}
