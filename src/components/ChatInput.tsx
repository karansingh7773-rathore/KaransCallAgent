import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatInputProps {
    onSendMessage: (text: string) => void;
}

const PLACEHOLDERS = [
    "Type a message to agent...",
    "Ask for schedule...",
    "Ask for business details...",
    "Request video analysis...",
    "Check security alerts..."
];

export function ChatInput({ onSendMessage }: ChatInputProps) {
    const [input, setInput] = useState("");
    const [index, setIndex] = useState(0);

    // Cycle through placeholders
    useEffect(() => {
        const interval = setInterval(() => {
            setIndex((prev) => (prev + 1) % PLACEHOLDERS.length);
        }, 3500);
        return () => clearInterval(interval);
    }, []);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && input.trim()) {
            onSendMessage(input.trim());
            setInput("");
        }
    };

    return (
        <div className="relative w-full">
            <div className="relative overflow-hidden rounded-xl bg-zinc-950/50 border border-zinc-700 shadow-inner group focus-within:border-orange-500/50 focus-within:ring-1 focus-within:ring-orange-500/20 transition-all">

                {/* Animated Placeholder - Only visible when input is empty */}
                <AnimatePresence mode="wait">
                    {input === "" && (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, filter: "blur(10px)", y: 5 }}
                            animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
                            exit={{ opacity: 0, filter: "blur(10px)", y: -5 }}
                            transition={{ duration: 0.8, ease: "easeInOut" }}
                            className="absolute top-0 bottom-0 left-4 flex items-center pointer-events-none text-zinc-500/80 italic select-none"
                        >
                            {PLACEHOLDERS[index]}
                        </motion.div>
                    )}
                </AnimatePresence>

                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="w-full bg-transparent px-4 py-4 pr-12 text-zinc-200 focus:outline-none placeholder-transparent z-10 relative"
                    // We hide native placeholder to use our custom one
                    placeholder=""
                />

                <div className="absolute right-4 top-1/2 transform -translate-y-1/2 text-zinc-600 pointer-events-none z-20">
                    ↵
                </div>
            </div>
        </div>
    );
}
