/**
 * ConversationBox Component
 * 
 * Displays real-time conversation between user and agent using LiveKit transcriptions.
 * Must be used inside a LiveKitRoom context.
 */
import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useConversationTranscription, ChatMessage } from '../hooks/useConversationTranscription';

interface ConversationBoxProps {
    onSendMessage?: (text: string) => void;
}

const MessageBubble = ({ message }: { message: ChatMessage }) => {
    const isUser = message.role === 'user';

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
        >
            <div className={`max-w-[80%] p-4 rounded-2xl border backdrop-blur-sm ${isUser
                ? 'bg-zinc-800/80 border-zinc-700 text-zinc-100 rounded-tr-sm'
                : 'bg-gradient-to-br from-orange-900/20 to-zinc-900/40 border-orange-500/20 text-zinc-200 rounded-tl-sm shadow-[0_0_15px_rgba(154,52,18,0.1)]'
                } ${!message.isFinal ? 'opacity-70' : ''}`}>
                <p className="leading-relaxed">
                    {message.text}
                    {!message.isFinal && (
                        <span className="inline-block ml-1 animate-pulse">...</span>
                    )}
                </p>
            </div>
        </motion.div>
    );
};

export function ConversationBox({ onSendMessage: _onSendMessage }: ConversationBoxProps) {
    const { messages, agentState, isAgentConnected } = useConversationTranscription();
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="flex flex-col h-full">
            {/* Agent Status */}
            <div className="px-4 py-2 border-b border-zinc-700/50 bg-zinc-900/50">
                <div className="flex items-center gap-2 text-xs">
                    <span className={`w-2 h-2 rounded-full ${isAgentConnected
                        ? agentState === 'speaking'
                            ? 'bg-orange-500 animate-pulse'
                            : 'bg-green-500'
                        : 'bg-zinc-500'
                        }`} />
                    <span className="text-zinc-400">
                        {isAgentConnected
                            ? `Agent: ${agentState}`
                            : 'Waiting for agent...'}
                    </span>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 px-4 py-4 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent">
                <AnimatePresence mode="popLayout">
                    {messages.length === 0 ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex items-center justify-center h-full text-zinc-500 text-sm"
                        >
                            Start speaking to begin the conversation...
                        </motion.div>
                    ) : (
                        messages.map((msg) => (
                            <MessageBubble key={msg.id} message={msg} />
                        ))
                    )}
                </AnimatePresence>
                <div ref={messagesEndRef} />
            </div>
        </div>
    );
}
