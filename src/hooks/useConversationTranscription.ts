/**
 * Conversation Transcription Hook
 * 
 * Uses LiveKit's built-in transcription features to get real-time
 * transcriptions from both the user and the agent.
 * 
 * This replaces WebSocket-based transcript broadcasting.
 */
import { useMemo, useEffect, useRef, useState, useCallback } from 'react';
import {
    useVoiceAssistant,
    useLocalParticipant,
    useTrackTranscription,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import type { ReceivedTranscriptionSegment, TrackReferenceOrPlaceholder } from '@livekit/components-core';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    text: string;
    isFinal: boolean;
    timestamp: number;
}

interface UseConversationTranscriptionReturn {
    messages: ChatMessage[];
    agentState: string;
    isAgentConnected: boolean;
    clearMessages: () => void;
}

export function useConversationTranscription(): UseConversationTranscriptionReturn {
    // Get agent transcriptions via useVoiceAssistant
    const { agentTranscriptions, state: agentState, agent } = useVoiceAssistant();

    // Get local participant for user transcriptions
    const { localParticipant, microphoneTrack } = useLocalParticipant();

    // Create TrackReference for user microphone
    const userMicTrackRef: TrackReferenceOrPlaceholder | undefined = useMemo(() => {
        if (!microphoneTrack || !localParticipant) return undefined;
        return {
            participant: localParticipant,
            publication: microphoneTrack,
            source: Track.Source.Microphone,
        };
    }, [localParticipant, microphoneTrack]);

    // Get user transcriptions from microphone track
    const { segments: userTranscriptions } = useTrackTranscription(userMicTrackRef);

    // Store finalized messages
    const [messages, setMessages] = useState<ChatMessage[]>([]);

    // Track which segment IDs we've already processed as final
    const processedSegments = useRef<Set<string>>(new Set());

    // Clear messages function
    const clearMessages = useCallback(() => {
        setMessages([]);
        processedSegments.current.clear();
    }, []);

    // Process user transcriptions
    useEffect(() => {
        if (!userTranscriptions || userTranscriptions.length === 0) return;

        userTranscriptions.forEach((seg: ReceivedTranscriptionSegment) => {
            const segId = seg.id;

            if (seg.final && !processedSegments.current.has(`user-${segId}`)) {
                // Add finalized user message
                processedSegments.current.add(`user-${segId}`);

                if (seg.text.trim()) {
                    console.log('[Transcription] User (final):', seg.text);
                    setMessages(prev => {
                        // Remove any existing interim message with this ID
                        const filtered = prev.filter(m => m.id !== `user-${segId}`);
                        return [...filtered, {
                            id: `user-${segId}`,
                            role: 'user',
                            text: seg.text,
                            isFinal: true,
                            timestamp: Date.now(),
                        }];
                    });
                }
            }
        });
    }, [userTranscriptions]);

    // Process agent transcriptions
    useEffect(() => {
        if (!agentTranscriptions || agentTranscriptions.length === 0) return;

        agentTranscriptions.forEach((seg: ReceivedTranscriptionSegment) => {
            const segId = seg.id;

            if (seg.final && !processedSegments.current.has(`agent-${segId}`)) {
                // Add finalized agent message
                processedSegments.current.add(`agent-${segId}`);

                if (seg.text.trim()) {
                    console.log('[Transcription] Agent (final):', seg.text);
                    setMessages(prev => {
                        // Remove any existing interim message with this ID
                        const filtered = prev.filter(m => m.id !== `agent-${segId}`);
                        return [...filtered, {
                            id: `agent-${segId}`,
                            role: 'assistant',
                            text: seg.text,
                            isFinal: true,
                            timestamp: Date.now(),
                        }];
                    });
                }
            }
        });
    }, [agentTranscriptions]);

    // Get current interim transcripts (non-final)
    const currentUserInterim = useMemo(() => {
        if (!userTranscriptions || userTranscriptions.length === 0) return null;
        const latest = userTranscriptions[userTranscriptions.length - 1];
        if (!latest.final && latest.text.trim()) {
            return latest.text;
        }
        return null;
    }, [userTranscriptions]);

    const currentAgentInterim = useMemo(() => {
        if (!agentTranscriptions || agentTranscriptions.length === 0) return null;
        const latest = agentTranscriptions[agentTranscriptions.length - 1];
        if (!latest.final && latest.text.trim()) {
            return latest.text;
        }
        return null;
    }, [agentTranscriptions]);

    // Combine finalized messages with current interim transcripts
    const allMessages = useMemo(() => {
        const result = [...messages];

        // Add current user interim as a temporary message
        if (currentUserInterim) {
            result.push({
                id: 'user-interim',
                role: 'user',
                text: currentUserInterim,
                isFinal: false,
                timestamp: Date.now(),
            });
        }

        // Add current agent interim as a temporary message
        if (currentAgentInterim) {
            result.push({
                id: 'agent-interim',
                role: 'assistant',
                text: currentAgentInterim,
                isFinal: false,
                timestamp: Date.now(),
            });
        }

        // Sort by timestamp
        return result.sort((a, b) => a.timestamp - b.timestamp);
    }, [messages, currentUserInterim, currentAgentInterim]);

    return {
        messages: allMessages,
        agentState,
        isAgentConnected: !!agent,
        clearMessages,
    };
}
