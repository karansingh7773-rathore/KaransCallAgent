import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

type Message = {
    role: 'user' | 'assistant';
    text: string;
};

interface ChatInterfaceProps {
    messages: Message[];
    transcript: string;
}

const StreamingMessage = ({ text }: { text: string }) => {
    const [displayedText, setDisplayedText] = React.useState("");

    React.useEffect(() => {
        let index = 0;
        const interval = setInterval(() => {
            if (index < text.length) {
                setDisplayedText((prev) => prev + text.charAt(index));
                index++;
            } else {
                clearInterval(interval);
            }
        }, 30); // Typing speed
        return () => clearInterval(interval);
    }, [text]);

    return <p className="leading-relaxed">{displayedText}</p>;
};

export function ChatInterface({ messages, transcript }: ChatInterfaceProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages, transcript]);

    return (
        <div className="flex-1 overflow-y-auto space-y-4 px-4 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent py-4">
            {messages.map((msg, i) => (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    key={i}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                    <div className={`max-w-[80%] p-4 rounded-2xl border backdrop-blur-sm ${msg.role === 'user'
                        ? 'bg-zinc-800/80 border-zinc-700 text-zinc-100 rounded-tr-sm'
                        : 'bg-gradient-to-br from-orange-900/20 to-zinc-900/40 border-orange-500/20 text-zinc-200 rounded-tl-sm shadow-[0_0_15px_rgba(154,52,18,0.1)]'
                        }`}>
                        {/* Only stream the last message if it's from assistant */}
                        {msg.role === 'assistant' && i === messages.length - 1 ? (
                            <StreamingMessage text={msg.text} />
                        ) : (
                            <p className="leading-relaxed">{msg.text}</p>
                        )}
                    </div>
                </motion.div>
            ))}

            {/* Live Transcript (Ghost Text) */}
            {transcript && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-end">
                    <div className="max-w-[80%] p-4 rounded-2xl border border-zinc-700 bg-zinc-800/40 text-zinc-400 italic rounded-tr-sm">
                        {transcript}...
                    </div>
                </motion.div>
            )}

            <div ref={messagesEndRef} />
        </div>
    );
}
