import { useState, useCallback, useEffect } from 'react';
import {
    Room,
    RoomEvent,
    Track,
    RemoteTrack,
    RemoteTrackPublication,
    RemoteParticipant,
    ConnectionState,
} from 'livekit-client';

interface LiveKitState {
    isConnected: boolean;
    isConnecting: boolean;
    isMicEnabled: boolean;
    error: string | null;
    roomName: string | null;
}

interface UseLiveKitRoomReturn {
    state: LiveKitState;
    connect: () => Promise<void>;
    disconnect: () => void;
    toggleMic: () => Promise<void>;
    setTtsVoice: (voice: string) => Promise<void>;
    room: Room | null;
}

/**
 * Hook for managing LiveKit room connection
 * 
 * This replaces the old WebSocket + VAD approach with WebRTC.
 * Benefits:
 * - Hardware AEC (browser knows it's a "call")
 * - Built-in interruption handling (server-side)
 * - Low latency streaming
 */
export function useLiveKitRoom(): UseLiveKitRoomReturn {
    const [room, setRoom] = useState<Room | null>(null);
    const [state, setState] = useState<LiveKitState>({
        isConnected: false,
        isConnecting: false,
        isMicEnabled: false,
        error: null,
        roomName: null,
    });

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (room) {
                room.disconnect();
            }
        };
    }, [room]);

    const connect = useCallback(async () => {
        try {
            setState(prev => ({ ...prev, isConnecting: true, error: null }));

            // Get token from our server
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${API_URL}/api/livekit-token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    identity: `user-${Date.now()}`,
                    room: 'voice-assistant'
                })
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            console.log('[LiveKit] Connecting to room:', data.room);

            // Create and connect to room
            const newRoom = new Room({
                // Audio processing options for best AEC
                audioCaptureDefaults: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
                // Optimize for voice
                dynacast: true,
                adaptiveStream: true,
            });

            // Setup event handlers
            newRoom.on(RoomEvent.Connected, () => {
                console.log('[LiveKit] Connected to room');
                setState(prev => ({
                    ...prev,
                    isConnected: true,
                    isConnecting: false,
                    roomName: data.room,
                }));
            });

            newRoom.on(RoomEvent.Disconnected, () => {
                console.log('[LiveKit] Disconnected from room');
                setState(prev => ({
                    ...prev,
                    isConnected: false,
                    isMicEnabled: false,
                    roomName: null,
                }));
            });

            newRoom.on(RoomEvent.TrackSubscribed, (
                track: RemoteTrack,
                _publication: RemoteTrackPublication,
                participant: RemoteParticipant
            ) => {
                console.log('[LiveKit] Track subscribed:', track.kind, 'from', participant.identity);

                // Auto-play audio tracks (TTS from agent)
                if (track.kind === Track.Kind.Audio) {
                    const audioElement = track.attach();
                    audioElement.id = `livekit-audio-${participant.identity}`;
                    document.body.appendChild(audioElement);
                    console.log('[LiveKit] Audio track attached (TTS playback)');
                }
            });

            newRoom.on(RoomEvent.TrackUnsubscribed, (
                track: RemoteTrack,
                _publication: RemoteTrackPublication,
                _participant: RemoteParticipant
            ) => {
                // Cleanup audio element
                track.detach().forEach(el => el.remove());
            });

            newRoom.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
                console.log('[LiveKit] Connection state:', state);
            });

            // Connect to the room
            await newRoom.connect(data.url, data.token);
            setRoom(newRoom);

            // Enable microphone immediately after connection
            await newRoom.localParticipant.setMicrophoneEnabled(true);
            setState(prev => ({ ...prev, isMicEnabled: true }));

        } catch (err: any) {
            console.error('[LiveKit] Connection error:', err);
            setState(prev => ({
                ...prev,
                isConnecting: false,
                error: err.message,
            }));
        }
    }, []);

    const disconnect = useCallback(() => {
        if (room) {
            room.disconnect();
            setRoom(null);
        }
        setState({
            isConnected: false,
            isConnecting: false,
            isMicEnabled: false,
            error: null,
            roomName: null,
        });
    }, [room]);

    const toggleMic = useCallback(async () => {
        if (!room) return;

        try {
            const newState = !state.isMicEnabled;
            await room.localParticipant.setMicrophoneEnabled(newState);
            setState(prev => ({ ...prev, isMicEnabled: newState }));
            console.log('[LiveKit] Microphone:', newState ? 'enabled' : 'disabled');
        } catch (err: any) {
            console.error('[LiveKit] Mic toggle error:', err);
        }
    }, [room, state.isMicEnabled]);

    // Send TTS voice preference to the agent via participant attributes
    const setTtsVoice = useCallback(async (voice: string) => {
        if (!room) {
            console.log('[LiveKit] Cannot set TTS voice - not connected');
            return;
        }

        try {
            // Set participant attribute - agent listens for this
            await room.localParticipant.setAttributes({
                tts_voice: voice,
            });
            console.log('[LiveKit] TTS voice set to:', voice);
        } catch (err: any) {
            console.error('[LiveKit] Failed to set TTS voice:', err);
        }
    }, [room]);

    return {
        state,
        connect,
        disconnect,
        toggleMic,
        setTtsVoice,
        room,
    };
}
