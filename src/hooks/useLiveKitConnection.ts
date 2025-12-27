/**
 * LiveKit Connection Hook
 * 
 * Manages LiveKit room connection and exposes the Room for use with
 * @livekit/components-react hooks.
 */
import { useState, useCallback, useEffect } from 'react';
import { Room, ConnectionState, RoomEvent } from 'livekit-client';

interface LiveKitConnectionState {
    isConnected: boolean;
    isConnecting: boolean;
    error: string | null;
}

interface ConnectionInfo {
    url: string;
    token: string;
    room: string;
}

export function useLiveKitConnection() {
    const [room] = useState<Room>(() => new Room({
        audioCaptureDefaults: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
        },
        dynacast: true,
        adaptiveStream: true,
    }));

    const [state, setState] = useState<LiveKitConnectionState>({
        isConnected: false,
        isConnecting: false,
        error: null,
    });

    const [connectionInfo, setConnectionInfo] = useState<ConnectionInfo | null>(null);

    // Setup room event listeners
    useEffect(() => {
        const handleConnected = () => {
            console.log('[LiveKit] Connected to room');
            setState(prev => ({ ...prev, isConnected: true, isConnecting: false }));
        };

        const handleDisconnected = () => {
            console.log('[LiveKit] Disconnected from room');
            setState({ isConnected: false, isConnecting: false, error: null });
        };

        const handleStateChange = (state: ConnectionState) => {
            console.log('[LiveKit] Connection state:', state);
        };

        room.on(RoomEvent.Connected, handleConnected);
        room.on(RoomEvent.Disconnected, handleDisconnected);
        room.on(RoomEvent.ConnectionStateChanged, handleStateChange);

        return () => {
            room.off(RoomEvent.Connected, handleConnected);
            room.off(RoomEvent.Disconnected, handleDisconnected);
            room.off(RoomEvent.ConnectionStateChanged, handleStateChange);
            room.disconnect();
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

            setConnectionInfo({ url: data.url, token: data.token, room: data.room });

            // Connect to room
            await room.connect(data.url, data.token);

            // Enable microphone
            await room.localParticipant.setMicrophoneEnabled(true);

        } catch (err: any) {
            console.error('[LiveKit] Connection error:', err);
            setState(prev => ({
                ...prev,
                isConnecting: false,
                error: err.message,
            }));
        }
    }, [room]);

    const disconnect = useCallback(() => {
        room.disconnect();
        setConnectionInfo(null);
        setState({ isConnected: false, isConnecting: false, error: null });
    }, [room]);

    // Set TTS voice via participant attributes
    const setTtsVoice = useCallback(async (voice: string) => {
        if (!room || room.state !== ConnectionState.Connected) {
            console.log('[LiveKit] Cannot set TTS voice - not connected');
            return;
        }

        try {
            await room.localParticipant.setAttributes({ tts_voice: voice });
            console.log('[LiveKit] TTS voice set to:', voice);
        } catch (err: any) {
            console.error('[LiveKit] Failed to set TTS voice:', err);
        }
    }, [room]);

    return {
        room,
        state,
        connectionInfo,
        connect,
        disconnect,
        setTtsVoice,
    };
}
