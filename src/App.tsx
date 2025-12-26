import { useState, useEffect, useRef, useCallback } from 'react';
import { LiveKitRoom, RoomAudioRenderer, useRoomContext } from '@livekit/components-react';
import { ConnectionState } from 'livekit-client';
import { AssistantState } from './types';
import { Header } from './components/Header';
import { ConversationBox } from './components/ConversationBox';
import { ChatInput } from './components/ChatInput';
import { AudioSphere } from './components/AudioSphere';
import { ControlPanel } from './components/ControlPanel';
import { SettingsPanel } from './components/SettingsPanel';

// Inner content that needs room context
function VoiceContent() {
    const room = useRoomContext();

    // Enable microphone when connected
    useEffect(() => {
        if (room.state === ConnectionState.Connected) {
            room.localParticipant.setMicrophoneEnabled(true).catch(console.error);
        }
    }, [room.state]);

    return (
        <>
            <ConversationBox />
            <RoomAudioRenderer />
        </>
    );
}

function App() {
    const [state, setState] = useState<AssistantState>('IDLE');
    const [isMicActive, setIsMicActive] = useState(false);

    // LiveKit connection info
    const [liveKitToken, setLiveKitToken] = useState<string | null>(null);
    const [liveKitUrl, setLiveKitUrl] = useState<string | null>(null);
    const [isConnecting, setIsConnecting] = useState(false);

    // WebSocket Connection (for text chat and settings only)
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Connect to WebSocket for text chat only
        const connectWebSocket = () => {
            ws.current = new WebSocket('ws://localhost:8000/ws');

            ws.current.onopen = () => {
                console.log('Connected to Sentinel Server (text chat only)');
            };

            ws.current.onmessage = async (event) => {
                try {
                    const message = JSON.parse(event.data);
                    switch (message.type) {
                        case 'config':
                            console.log('[WS] Config updated');
                            break;
                        case 'error':
                            console.error('[WS] Error:', message.data);
                            break;
                    }
                } catch (err) {
                    console.error("Failed to parse WebSocket message:", err);
                }
            };

            ws.current.onclose = () => {
                console.log("WebSocket disconnected. Reconnecting in 3s...");
                setTimeout(connectWebSocket, 3000);
            };
        };

        connectWebSocket();

        return () => {
            if (ws.current) {
                ws.current.onclose = null;
                ws.current.close();
            }
        };
    }, []);

    // Text chat uses WebSocket
    const sendMessage = (text: string) => {
        ws.current?.send(JSON.stringify({ type: 'text', data: text }));
    };

    // LiveKit Voice Control - get token and let LiveKitRoom handle connection
    const toggleMic = async () => {
        if (liveKitToken) {
            // Disconnect by clearing token
            setLiveKitToken(null);
            setLiveKitUrl(null);
            setIsMicActive(false);
            setState('IDLE');
        } else {
            // Fetch token and connect
            setIsConnecting(true);
            try {
                const response = await fetch('http://localhost:8000/api/livekit-token', {
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

                console.log('[LiveKit] Got token, connecting to room:', data.room);
                setLiveKitUrl(data.url);
                setLiveKitToken(data.token);
                setIsMicActive(true);
                setState('LISTENING');
            } catch (err: any) {
                console.error('[LiveKit] Failed to get token:', err);
            } finally {
                setIsConnecting(false);
            }
        }
    };

    // Handle LiveKit connection events
    const handleConnected = useCallback(() => {
        console.log('[LiveKit] Connected');
        setIsMicActive(true);
        setState('LISTENING');
    }, []);

    const handleDisconnected = useCallback(() => {
        console.log('[LiveKit] Disconnected');
        setLiveKitToken(null);
        setLiveKitUrl(null);
        setIsMicActive(false);
        setState('IDLE');
    }, []);

    // Deepgram voice state
    const [ttsVoice, setTtsVoiceState] = useState('arcas');

    const changeTtsVoice = (voice: string) => {
        setTtsVoiceState(voice);
        // Voice change will be handled via room participant attributes
    };

    // Settings State
    const [showSettings, setShowSettings] = useState(false);

    // Configuration State
    const [agentPrompt, setAgentPrompt] = useState("");
    const [businessDetails, setBusinessDetails] = useState("");
    const [speechSpeed, setSpeechSpeed] = useState(1.0);

    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
    const isMounted = useRef(false);

    // Sync config with server
    useEffect(() => {
        if (!isMounted.current) {
            isMounted.current = true;
            return;
        }

        if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);

        debounceTimerRef.current = setTimeout(() => {
            if (ws.current?.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify({
                    type: 'config',
                    agent_prompt: agentPrompt,
                    business_details: businessDetails,
                    voice: ttsVoice,
                    speed: speechSpeed,
                }));
            }
        }, 800);

        return () => {
            if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
        };
    }, [agentPrompt, businessDetails, ttsVoice, speechSpeed]);

    // Resizing State
    const [sidebarWidth, setSidebarWidth] = useState(600);
    const [isResizing, setIsResizing] = useState(false);
    const sidebarRef = useRef<HTMLDivElement>(null);

    const startResizing = (e: React.MouseEvent) => {
        setIsResizing(true);
        e.preventDefault();
    };

    useEffect(() => {
        const stopResizing = () => setIsResizing(false);

        const resize = (e: MouseEvent) => {
            if (isResizing) {
                const newWidth = window.innerWidth - e.clientX;
                if (newWidth >= 300 && newWidth <= 900) {
                    setSidebarWidth(newWidth);
                }
            }
        };

        if (isResizing) {
            window.addEventListener('mousemove', resize);
            window.addEventListener('mouseup', stopResizing);
        }

        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        };
    }, [isResizing]);

    return (
        <div className="flex flex-col h-full font-sans text-zinc-100 bg-zinc-950 relative z-20"
            style={{ cursor: isResizing ? 'col-resize' : 'default' }}>
            <Header state={state} onSettingsClick={() => setShowSettings(true)} />

            <SettingsPanel
                isOpen={showSettings}
                onClose={() => setShowSettings(false)}
                ttsVoice={ttsVoice}
                onChangeTtsVoice={changeTtsVoice}
                agentPrompt={agentPrompt}
                onChangeAgentPrompt={setAgentPrompt}
                businessDetails={businessDetails}
                onChangeBusinessDetails={setBusinessDetails}
                speechSpeed={speechSpeed}
                onChangeSpeed={setSpeechSpeed}
            />

            <div className="flex-1 flex overflow-hidden relative bg-zinc-950">
                {/* Main Stage: Visualizer & Controls */}
                <div className="flex-1 flex flex-col items-center justify-center p-8 gap-6 pb-32 relative">
                    {/* Sphere Container */}
                    <div className="w-full max-w-2xl h-[400px] flex items-center justify-center relative">
                        <AudioSphere
                            state={state}
                            micAnalyser={null}
                            playbackAnalyser={null}
                        />
                    </div>

                    {/* Controls centered below sphere */}
                    <div className="z-20">
                        <ControlPanel
                            isMicActive={isMicActive}
                            toggleMic={toggleMic}
                            state={state}
                        />
                    </div>
                </div>

                {/* Sidebar: Conversation with LiveKit Transcription */}
                <aside
                    ref={sidebarRef}
                    style={{ width: sidebarWidth }}
                    className="relative border border-zinc-700/50 bg-zinc-900/80 backdrop-blur-xl flex flex-col shadow-2xl z-30 h-[calc(100%-3rem)] my-auto mr-4 rounded-[2rem] overflow-hidden transition-[width] duration-0 ease-linear p-2"
                >
                    {/* Resize Handle */}
                    <div
                        className="absolute left-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-orange-500/20 z-50 transition-colors"
                        onMouseDown={startResizing}
                    />

                    {/* Inner Content Container */}
                    <div className="flex-1 flex flex-col w-full h-full rounded-[1.5rem] border border-zinc-700/50 overflow-hidden bg-zinc-900/50">
                        <div className="p-5 border-b border-zinc-800 bg-zinc-900/50 flex items-center justify-between">
                            <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${isMicActive ? 'bg-green-500' : 'bg-orange-500'}`}></span>
                                Conversation
                            </h2>
                        </div>

                        <div className="flex-1 overflow-hidden relative flex flex-col">
                            {/* LiveKit Room - manages connection automatically */}
                            {liveKitToken && liveKitUrl ? (
                                <LiveKitRoom
                                    token={liveKitToken}
                                    serverUrl={liveKitUrl}
                                    connect={true}
                                    audio={true}
                                    video={false}
                                    onConnected={handleConnected}
                                    onDisconnected={handleDisconnected}
                                >
                                    <VoiceContent />
                                </LiveKitRoom>
                            ) : (
                                <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm p-4 text-center">
                                    <div>
                                        <p className="mb-2">🎙️ Click the microphone button to start</p>
                                        <p className="text-xs text-zinc-600">Your conversation will appear here</p>
                                        {isConnecting && <p className="text-xs text-orange-500 mt-2">Connecting...</p>}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Input Area */}
                        <div className="p-5 border-t border-zinc-700/50 bg-zinc-900/50">
                            <ChatInput onSendMessage={sendMessage} />
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    );
}

export default App;
